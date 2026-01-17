"""
Taxonomy Mapper for mapping parsed CV data to canonical taxonomy IDs.

Maps skills, certifications, roles, and software to their canonical
IDs in the PostgreSQL taxonomy tables using:
1. Exact match on normalized names
2. Alias matching from taxonomy tables
3. Semantic matching using Cohere embeddings (optional)
"""

import logging
from typing import Any
from uuid import UUID

import boto3
import pg8000

from ..llm.provider import BedrockProvider, ModelType
from .schema import ParsedCertification, ParsedCV, ParsedExperience, ParsedSkill, ParsedSoftware

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """
    Normalize text for matching.

    Removes accents, lowercases, and strips whitespace.

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    import unicodedata

    # Normalize to decomposed form, remove combining marks
    normalized = unicodedata.normalize("NFD", text)
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    # Lowercase and strip
    return normalized.lower().strip()


class TaxonomyMapper:
    """
    Maps parsed CV data to canonical taxonomy IDs.

    Performs matching against PostgreSQL taxonomy tables:
    - skill_taxonomy
    - certification_taxonomy
    - role_taxonomy
    - software_taxonomy

    Example:
        mapper = TaxonomyMapper(db_secret_arn="arn:aws:secretsmanager:...")
        mapped_cv = await mapper.map_all(parsed_cv)
    """

    SEMANTIC_THRESHOLD = 0.85  # Minimum similarity for semantic matching

    def __init__(
        self,
        db_secret_arn: str | None = None,
        db_connection: Any | None = None,
        region: str = "eu-north-1",
        use_semantic_matching: bool = True,
    ):
        """
        Initialize taxonomy mapper.

        Args:
            db_secret_arn: ARN of Secrets Manager secret with DB credentials
            db_connection: Existing database connection (for reuse)
            region: AWS region
            use_semantic_matching: Whether to use embedding-based matching
        """
        self.db_secret_arn = db_secret_arn
        self._connection = db_connection
        self.region = region
        self.use_semantic_matching = use_semantic_matching
        self._provider: BedrockProvider | None = None

        # Cache for taxonomy data
        self._skill_cache: dict[str, dict[str, Any]] | None = None
        self._cert_cache: dict[str, dict[str, Any]] | None = None
        self._role_cache: dict[str, dict[str, Any]] | None = None
        self._software_cache: dict[str, dict[str, Any]] | None = None

    @property
    def provider(self) -> BedrockProvider:
        """Lazy-load Bedrock provider."""
        if self._provider is None:
            self._provider = BedrockProvider(region=self.region)
        return self._provider

    def _get_connection(self) -> pg8000.Connection:
        """
        Get database connection.

        Returns:
            pg8000 connection
        """
        if self._connection is not None:
            return self._connection

        if not self.db_secret_arn:
            raise ValueError("db_secret_arn required when no connection provided")

        # Get credentials from Secrets Manager
        import json

        secrets_client = boto3.client("secretsmanager", region_name=self.region)
        secret_response = secrets_client.get_secret_value(SecretId=self.db_secret_arn)
        credentials = json.loads(secret_response["SecretString"])

        self._connection = pg8000.connect(
            host=credentials["host"],
            port=int(credentials.get("port", 5432)),
            database=credentials.get("dbname", "cagenai"),
            user=credentials["username"],
            password=credentials["password"],
            ssl_context=True,
        )

        return self._connection

    async def map_all(self, parsed_cv: ParsedCV) -> ParsedCV:
        """
        Map all taxonomy fields in parsed CV.

        Args:
            parsed_cv: Parsed CV with raw data

        Returns:
            ParsedCV with taxonomy IDs populated
        """
        # Map skills
        await self.map_skills(parsed_cv)

        # Map certifications
        await self.map_certifications(parsed_cv)

        # Map job titles to roles
        await self.map_roles(parsed_cv)

        # Map software
        await self.map_software(parsed_cv)

        return parsed_cv

    async def map_skills(self, parsed_cv: ParsedCV) -> None:
        """
        Map skills to canonical taxonomy IDs.

        Args:
            parsed_cv: ParsedCV to update in place
        """
        if not parsed_cv.skills:
            return

        # Load skill taxonomy cache
        await self._load_skill_cache()

        for skill in parsed_cv.skills:
            match = await self._match_skill(skill.name)
            if match:
                skill.skill_id = match["id"]
                skill.canonical_id = match["canonical_id"]
                skill.name_normalized = match["name_normalized"]

    async def map_certifications(self, parsed_cv: ParsedCV) -> None:
        """
        Map certifications to canonical taxonomy IDs.

        Args:
            parsed_cv: ParsedCV to update in place
        """
        if not parsed_cv.certifications:
            return

        # Load certification taxonomy cache
        await self._load_certification_cache()

        for cert in parsed_cv.certifications:
            match = await self._match_certification(cert.certification_name)
            if match:
                cert.certification_id = match["id"]
                cert.canonical_id = match["canonical_id"]
                cert.certification_name_normalized = match["name_normalized"]
                if match.get("issuing_organization") and not cert.issuing_organization:
                    cert.issuing_organization = match["issuing_organization"]

    async def map_roles(self, parsed_cv: ParsedCV) -> None:
        """
        Map job titles to canonical role taxonomy IDs.

        Args:
            parsed_cv: ParsedCV to update in place
        """
        if not parsed_cv.experience:
            return

        # Load role taxonomy cache
        await self._load_role_cache()

        for exp in parsed_cv.experience:
            match = await self._match_role(exp.job_title)
            if match:
                exp.role_id = match["id"]
                exp.job_title_normalized = match["name_normalized"]

    async def map_software(self, parsed_cv: ParsedCV) -> None:
        """
        Map software to canonical taxonomy IDs.

        Args:
            parsed_cv: ParsedCV to update in place
        """
        if not parsed_cv.software:
            return

        # Load software taxonomy cache
        await self._load_software_cache()

        for sw in parsed_cv.software:
            match = await self._match_software(sw.name)
            if match:
                sw.software_id = match["id"]
                sw.canonical_id = match["canonical_id"]
                if match.get("vendor") and not sw.vendor:
                    sw.vendor = match["vendor"]

    async def _load_skill_cache(self) -> None:
        """Load skill taxonomy into memory cache."""
        if self._skill_cache is not None:
            return

        self._skill_cache = {}
        conn = self._get_connection()

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, canonical_id, name_en, name_el, aliases_en, aliases_el, category
                FROM skill_taxonomy
                WHERE is_active = true
            """)

            for row in cursor.fetchall():
                skill_id, canonical_id, name_en, name_el, aliases_en, aliases_el, category = row

                # Index by normalized names
                entry = {
                    "id": UUID(str(skill_id)),
                    "canonical_id": canonical_id,
                    "name_normalized": normalize_text(name_en),
                    "category": category,
                }

                # Add by normalized name_en
                self._skill_cache[normalize_text(name_en)] = entry

                # Add by normalized name_el if present
                if name_el:
                    self._skill_cache[normalize_text(name_el)] = entry

                # Add by aliases
                for alias in (aliases_en or []):
                    self._skill_cache[normalize_text(alias)] = entry
                for alias in (aliases_el or []):
                    self._skill_cache[normalize_text(alias)] = entry

            cursor.close()
            logger.info(f"Loaded {len(self._skill_cache)} skill taxonomy entries")

        except Exception as e:
            logger.warning(f"Failed to load skill taxonomy: {e}")
            self._skill_cache = {}

    async def _load_certification_cache(self) -> None:
        """Load certification taxonomy into memory cache."""
        if self._cert_cache is not None:
            return

        self._cert_cache = {}
        conn = self._get_connection()

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, canonical_id, name_en, name_el, issuing_organization, aliases, abbreviations
                FROM certification_taxonomy
                WHERE is_active = true
            """)

            for row in cursor.fetchall():
                cert_id, canonical_id, name_en, name_el, issuer, aliases, abbrevs = row

                entry = {
                    "id": UUID(str(cert_id)),
                    "canonical_id": canonical_id,
                    "name_normalized": normalize_text(name_en),
                    "issuing_organization": issuer,
                }

                # Index by normalized names
                self._cert_cache[normalize_text(name_en)] = entry

                if name_el:
                    self._cert_cache[normalize_text(name_el)] = entry

                for alias in (aliases or []):
                    self._cert_cache[normalize_text(alias)] = entry
                for abbrev in (abbrevs or []):
                    self._cert_cache[normalize_text(abbrev)] = entry

            cursor.close()
            logger.info(f"Loaded {len(self._cert_cache)} certification taxonomy entries")

        except Exception as e:
            logger.warning(f"Failed to load certification taxonomy: {e}")
            self._cert_cache = {}

    async def _load_role_cache(self) -> None:
        """Load role taxonomy into memory cache."""
        if self._role_cache is not None:
            return

        self._role_cache = {}
        conn = self._get_connection()

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, canonical_id, name_en, name_el, aliases_en, aliases_el, category
                FROM role_taxonomy
                WHERE is_active = true
            """)

            for row in cursor.fetchall():
                role_id, canonical_id, name_en, name_el, aliases_en, aliases_el, category = row

                entry = {
                    "id": UUID(str(role_id)),
                    "canonical_id": canonical_id,
                    "name_normalized": normalize_text(name_en),
                    "category": category,
                }

                self._role_cache[normalize_text(name_en)] = entry

                if name_el:
                    self._role_cache[normalize_text(name_el)] = entry

                for alias in (aliases_en or []):
                    self._role_cache[normalize_text(alias)] = entry
                for alias in (aliases_el or []):
                    self._role_cache[normalize_text(alias)] = entry

            cursor.close()
            logger.info(f"Loaded {len(self._role_cache)} role taxonomy entries")

        except Exception as e:
            logger.warning(f"Failed to load role taxonomy: {e}")
            self._role_cache = {}

    async def _load_software_cache(self) -> None:
        """Load software taxonomy into memory cache."""
        if self._software_cache is not None:
            return

        self._software_cache = {}
        conn = self._get_connection()

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, canonical_id, name, vendor, aliases, category
                FROM software_taxonomy
                WHERE is_active = true
            """)

            for row in cursor.fetchall():
                sw_id, canonical_id, name, vendor, aliases, category = row

                entry = {
                    "id": UUID(str(sw_id)),
                    "canonical_id": canonical_id,
                    "name_normalized": normalize_text(name),
                    "vendor": vendor,
                    "category": category,
                }

                self._software_cache[normalize_text(name)] = entry

                for alias in (aliases or []):
                    self._software_cache[normalize_text(alias)] = entry

            cursor.close()
            logger.info(f"Loaded {len(self._software_cache)} software taxonomy entries")

        except Exception as e:
            logger.warning(f"Failed to load software taxonomy: {e}")
            self._software_cache = {}

    async def _match_skill(self, skill_name: str) -> dict[str, Any] | None:
        """
        Match skill name to taxonomy entry.

        Args:
            skill_name: Skill name from CV

        Returns:
            Taxonomy entry dict or None
        """
        normalized = normalize_text(skill_name)

        # 1. Exact match
        if normalized in self._skill_cache:
            return self._skill_cache[normalized]

        # 2. Substring match (for compound skills)
        for cached_name, entry in self._skill_cache.items():
            if cached_name in normalized or normalized in cached_name:
                return entry

        # 3. Semantic matching (optional)
        if self.use_semantic_matching:
            match = await self._semantic_match(skill_name, list(self._skill_cache.keys()))
            if match:
                return self._skill_cache[match]

        return None

    async def _match_certification(self, cert_name: str) -> dict[str, Any] | None:
        """Match certification name to taxonomy entry."""
        normalized = normalize_text(cert_name)

        if normalized in self._cert_cache:
            return self._cert_cache[normalized]

        # Substring match
        for cached_name, entry in self._cert_cache.items():
            if cached_name in normalized or normalized in cached_name:
                return entry

        if self.use_semantic_matching:
            match = await self._semantic_match(cert_name, list(self._cert_cache.keys()))
            if match:
                return self._cert_cache[match]

        return None

    async def _match_role(self, job_title: str) -> dict[str, Any] | None:
        """Match job title to role taxonomy entry."""
        normalized = normalize_text(job_title)

        if normalized in self._role_cache:
            return self._role_cache[normalized]

        # Substring match
        for cached_name, entry in self._role_cache.items():
            if cached_name in normalized or normalized in cached_name:
                return entry

        if self.use_semantic_matching:
            match = await self._semantic_match(job_title, list(self._role_cache.keys()))
            if match:
                return self._role_cache[match]

        return None

    async def _match_software(self, sw_name: str) -> dict[str, Any] | None:
        """Match software name to taxonomy entry."""
        normalized = normalize_text(sw_name)

        if normalized in self._software_cache:
            return self._software_cache[normalized]

        # Substring match
        for cached_name, entry in self._software_cache.items():
            if cached_name in normalized or normalized in cached_name:
                return entry

        if self.use_semantic_matching:
            match = await self._semantic_match(sw_name, list(self._software_cache.keys()))
            if match:
                return self._software_cache[match]

        return None

    async def _semantic_match(
        self,
        query: str,
        candidates: list[str],
        threshold: float | None = None,
    ) -> str | None:
        """
        Find best semantic match using embeddings.

        Args:
            query: Query string to match
            candidates: List of candidate strings
            threshold: Minimum similarity threshold

        Returns:
            Best matching candidate or None
        """
        if not candidates:
            return None

        if threshold is None:
            threshold = self.SEMANTIC_THRESHOLD

        try:
            # Generate query embedding
            query_embedding = await self.provider.embed_query(query)

            # Generate candidate embeddings (batch)
            candidate_response = await self.provider.embed(candidates[:100])  # Limit batch size

            # Calculate cosine similarities
            best_match = None
            best_score = 0.0

            for i, candidate_embedding in enumerate(candidate_response.embeddings):
                score = self._cosine_similarity(query_embedding, candidate_embedding)
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = candidates[i]

            if best_match:
                logger.debug(f"Semantic match: '{query}' -> '{best_match}' (score={best_score:.3f})")

            return best_match

        except Exception as e:
            logger.warning(f"Semantic matching failed: {e}")
            return None

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def close(self) -> None:
        """Close database connection if owned."""
        if self._connection and not self.db_secret_arn:
            # Only close if we created the connection
            pass
        elif self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None
