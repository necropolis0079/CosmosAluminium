"""
Dynamic Taxonomy Alias Loader.

Loads aliases dynamically from PostgreSQL taxonomy tables instead of
using static hardcoded dictionaries. This ensures queries always
reflect the latest taxonomy data.

See docs/HR-INTELLIGENCE-UNIFIED.md Phase 4 for specification.

Usage:
    loader = DynamicAliasLoader(db_secret_arn="...")
    aliases = await loader.load_all()

    # Or synchronous:
    aliases = load_aliases_sync(db_secret_arn="...")
"""

import asyncio
import json
import logging
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import boto3

logger = logging.getLogger(__name__)


@dataclass
class AliasEntry:
    """
    Single alias mapping entry.

    Represents a mapping from a normalized term to its canonical taxonomy ID.
    """

    canonical_id: str
    """Canonical taxonomy ID (e.g., 'ACCOUNTANT', 'SAP_ERP')."""

    source_table: str
    """Source taxonomy table (skill_taxonomy, role_taxonomy, etc.)."""

    source_language: str
    """Language of the matched term ('en', 'el', or 'both')."""

    match_type: str
    """How this alias was matched ('name_en', 'name_el', 'alias_en', 'alias_el', 'abbreviation')."""

    primary_name: str
    """Display name for this entry."""

    confidence: float = 1.0
    """Match confidence (1.0 for exact, lower for fuzzy)."""

    category: str | None = None
    """Category within the taxonomy (if available)."""


@dataclass
class AliasCache:
    """Cache container for loaded aliases."""

    aliases: dict[str, AliasEntry] = field(default_factory=dict)
    loaded_at: datetime | None = None
    entry_count: int = 0

    def is_stale(self, ttl_minutes: int) -> bool:
        """Check if cache is stale and needs refresh."""
        if self.loaded_at is None:
            return True
        age = (datetime.now(timezone.utc) - self.loaded_at).total_seconds() / 60
        return age > ttl_minutes


class DynamicAliasLoader:
    """
    Load and cache taxonomy aliases from PostgreSQL.

    Loads aliases from:
    - skill_taxonomy (hard skills)
    - role_taxonomy (job roles)
    - software_taxonomy (software tools)
    - certification_taxonomy (certifications)

    Provides a unified lookup dictionary mapping normalized terms
    to their canonical taxonomy IDs.

    Example:
        loader = DynamicAliasLoader(db_secret_arn="arn:aws:...")
        aliases = await loader.load_all()

        entry = aliases.get(normalize_text("λογιστής"))
        if entry:
            print(f"Canonical ID: {entry.canonical_id}")
    """

    DEFAULT_TTL_MINUTES = 60

    def __init__(
        self,
        db_secret_arn: str,
        cache_ttl_minutes: int = DEFAULT_TTL_MINUTES,
        region: str = "eu-north-1",
    ):
        """
        Initialize the alias loader.

        Args:
            db_secret_arn: AWS Secrets Manager ARN for database credentials
            cache_ttl_minutes: Cache TTL in minutes (default 60)
            region: AWS region
        """
        self.db_secret_arn = db_secret_arn
        self.cache_ttl_minutes = cache_ttl_minutes
        self.region = region

        self._cache = AliasCache()
        self._connection = None
        self._credentials = None

    async def load_all(self) -> dict[str, AliasEntry]:
        """
        Load all aliases from all taxonomy tables.

        Returns:
            Dictionary mapping normalized terms to AliasEntry objects.

        Note:
            Uses cached data if not stale. Call reload() to force refresh.
        """
        if not self._cache.is_stale(self.cache_ttl_minutes):
            logger.debug(f"Using cached aliases ({self._cache.entry_count} entries)")
            return self._cache.aliases

        logger.info("Loading dynamic aliases from taxonomy tables...")

        aliases: dict[str, AliasEntry] = {}

        # Load from all taxonomy tables
        try:
            skills = await self._load_skills()
            aliases.update(skills)
            logger.info(f"Loaded {len(skills)} skill aliases")
        except Exception as e:
            logger.warning(f"Failed to load skill aliases: {e}")

        try:
            roles = await self._load_roles()
            aliases.update(roles)
            logger.info(f"Loaded {len(roles)} role aliases")
        except Exception as e:
            logger.warning(f"Failed to load role aliases: {e}")

        try:
            software = await self._load_software()
            aliases.update(software)
            logger.info(f"Loaded {len(software)} software aliases")
        except Exception as e:
            logger.warning(f"Failed to load software aliases: {e}")

        try:
            certs = await self._load_certifications()
            aliases.update(certs)
            logger.info(f"Loaded {len(certs)} certification aliases")
        except Exception as e:
            logger.warning(f"Failed to load certification aliases: {e}")

        # Update cache
        self._cache = AliasCache(
            aliases=aliases,
            loaded_at=datetime.now(timezone.utc),
            entry_count=len(aliases),
        )

        logger.info(f"Dynamic aliases loaded: {len(aliases)} total entries")
        return aliases

    async def reload(self) -> dict[str, AliasEntry]:
        """Force reload of all aliases, ignoring cache."""
        self._cache = AliasCache()  # Clear cache
        return await self.load_all()

    async def reload_if_stale(self) -> bool:
        """
        Reload aliases if cache is stale.

        Returns:
            True if reloaded, False if cache was still valid.
        """
        if self._cache.is_stale(self.cache_ttl_minutes):
            await self.load_all()
            return True
        return False

    def get_cached(self) -> dict[str, AliasEntry]:
        """
        Get currently cached aliases without loading.

        Returns empty dict if cache not yet loaded.
        """
        return self._cache.aliases

    async def _load_skills(self) -> dict[str, AliasEntry]:
        """Load aliases from skill_taxonomy."""
        aliases: dict[str, AliasEntry] = {}

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                canonical_id,
                name_en,
                name_el,
                aliases_en,
                aliases_el,
                category
            FROM skill_taxonomy
            WHERE is_active = true
        """)

        for row in cursor.fetchall():
            canonical_id, name_en, name_el, aliases_en, aliases_el, category = row

            # Add primary name (English)
            if name_en:
                normalized = normalize_text(name_en)
                aliases[normalized] = AliasEntry(
                    canonical_id=canonical_id,
                    source_table="skill_taxonomy",
                    source_language="en",
                    match_type="name_en",
                    primary_name=name_en,
                    category=category,
                )

            # Add Greek name
            if name_el:
                normalized = normalize_text(name_el)
                aliases[normalized] = AliasEntry(
                    canonical_id=canonical_id,
                    source_table="skill_taxonomy",
                    source_language="el",
                    match_type="name_el",
                    primary_name=name_en or name_el,
                    category=category,
                )

            # Add English aliases
            for alias in (aliases_en or []):
                if alias:
                    normalized = normalize_text(alias)
                    aliases[normalized] = AliasEntry(
                        canonical_id=canonical_id,
                        source_table="skill_taxonomy",
                        source_language="en",
                        match_type="alias_en",
                        primary_name=name_en or name_el,
                        confidence=0.95,
                        category=category,
                    )

            # Add Greek aliases
            for alias in (aliases_el or []):
                if alias:
                    normalized = normalize_text(alias)
                    aliases[normalized] = AliasEntry(
                        canonical_id=canonical_id,
                        source_table="skill_taxonomy",
                        source_language="el",
                        match_type="alias_el",
                        primary_name=name_en or name_el,
                        confidence=0.95,
                        category=category,
                    )

        cursor.close()
        return aliases

    async def _load_roles(self) -> dict[str, AliasEntry]:
        """Load aliases from role_taxonomy."""
        aliases: dict[str, AliasEntry] = {}

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                canonical_id,
                name_en,
                name_el,
                aliases_en,
                aliases_el,
                department
            FROM role_taxonomy
            WHERE is_active = true
        """)

        for row in cursor.fetchall():
            canonical_id, name_en, name_el, aliases_en, aliases_el, department = row

            # Add primary name (English)
            if name_en:
                normalized = normalize_text(name_en)
                aliases[normalized] = AliasEntry(
                    canonical_id=canonical_id,
                    source_table="role_taxonomy",
                    source_language="en",
                    match_type="name_en",
                    primary_name=name_en,
                    category=department,
                )

            # Add Greek name
            if name_el:
                normalized = normalize_text(name_el)
                aliases[normalized] = AliasEntry(
                    canonical_id=canonical_id,
                    source_table="role_taxonomy",
                    source_language="el",
                    match_type="name_el",
                    primary_name=name_en or name_el,
                    category=department,
                )

            # Add English aliases
            for alias in (aliases_en or []):
                if alias:
                    normalized = normalize_text(alias)
                    aliases[normalized] = AliasEntry(
                        canonical_id=canonical_id,
                        source_table="role_taxonomy",
                        source_language="en",
                        match_type="alias_en",
                        primary_name=name_en or name_el,
                        confidence=0.95,
                        category=department,
                    )

            # Add Greek aliases
            for alias in (aliases_el or []):
                if alias:
                    normalized = normalize_text(alias)
                    aliases[normalized] = AliasEntry(
                        canonical_id=canonical_id,
                        source_table="role_taxonomy",
                        source_language="el",
                        match_type="alias_el",
                        primary_name=name_en or name_el,
                        confidence=0.95,
                        category=department,
                    )

        cursor.close()
        return aliases

    async def _load_software(self) -> dict[str, AliasEntry]:
        """Load aliases from software_taxonomy."""
        aliases: dict[str, AliasEntry] = {}

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                canonical_id,
                name,
                aliases,
                vendor,
                category
            FROM software_taxonomy
            WHERE is_active = true
        """)

        for row in cursor.fetchall():
            canonical_id, name, alias_list, vendor, category = row

            # Add primary name
            if name:
                normalized = normalize_text(name)
                aliases[normalized] = AliasEntry(
                    canonical_id=canonical_id,
                    source_table="software_taxonomy",
                    source_language="both",
                    match_type="name",
                    primary_name=name,
                    category=category,
                )

            # Add aliases
            for alias in (alias_list or []):
                if alias:
                    normalized = normalize_text(alias)
                    aliases[normalized] = AliasEntry(
                        canonical_id=canonical_id,
                        source_table="software_taxonomy",
                        source_language="both",
                        match_type="alias",
                        primary_name=name,
                        confidence=0.95,
                        category=category,
                    )

        cursor.close()
        return aliases

    async def _load_certifications(self) -> dict[str, AliasEntry]:
        """Load aliases from certification_taxonomy."""
        aliases: dict[str, AliasEntry] = {}

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                canonical_id,
                name_en,
                name_el,
                aliases,
                abbreviations,
                issuing_organization
            FROM certification_taxonomy
            WHERE is_active = true
        """)

        for row in cursor.fetchall():
            canonical_id, name_en, name_el, alias_list, abbreviations, issuer = row

            # Add primary name (English)
            if name_en:
                normalized = normalize_text(name_en)
                aliases[normalized] = AliasEntry(
                    canonical_id=canonical_id,
                    source_table="certification_taxonomy",
                    source_language="en",
                    match_type="name_en",
                    primary_name=name_en,
                    category=issuer,
                )

            # Add Greek name
            if name_el:
                normalized = normalize_text(name_el)
                aliases[normalized] = AliasEntry(
                    canonical_id=canonical_id,
                    source_table="certification_taxonomy",
                    source_language="el",
                    match_type="name_el",
                    primary_name=name_en or name_el,
                    category=issuer,
                )

            # Add aliases
            for alias in (alias_list or []):
                if alias:
                    normalized = normalize_text(alias)
                    aliases[normalized] = AliasEntry(
                        canonical_id=canonical_id,
                        source_table="certification_taxonomy",
                        source_language="both",
                        match_type="alias",
                        primary_name=name_en or name_el,
                        confidence=0.95,
                        category=issuer,
                    )

            # Add abbreviations (higher confidence than aliases)
            for abbr in (abbreviations or []):
                if abbr:
                    normalized = normalize_text(abbr)
                    aliases[normalized] = AliasEntry(
                        canonical_id=canonical_id,
                        source_table="certification_taxonomy",
                        source_language="both",
                        match_type="abbreviation",
                        primary_name=name_en or name_el,
                        confidence=0.98,  # High confidence for abbreviations
                        category=issuer,
                    )

        cursor.close()
        return aliases

    def _get_connection(self):
        """Get or create database connection."""
        if self._connection is not None:
            try:
                # Test if connection is still alive
                cursor = self._connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                return self._connection
            except Exception:
                self._connection = None

        import pg8000

        # Get credentials from Secrets Manager
        if self._credentials is None:
            secrets_client = boto3.client("secretsmanager", region_name=self.region)
            secret_response = secrets_client.get_secret_value(SecretId=self.db_secret_arn)
            self._credentials = json.loads(secret_response["SecretString"])

        self._connection = pg8000.connect(
            host=self._credentials["host"],
            port=int(self._credentials.get("port", 5432)),
            database=self._credentials.get("dbname", "cagenai"),
            user=self._credentials["username"],
            password=self._credentials["password"],
            ssl_context=True,
        )

        return self._connection

    def close(self):
        """Close database connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None


def normalize_text(text: str) -> str:
    """
    Normalize text for matching.

    Removes accents, lowercases, and strips whitespace.
    Uses the same normalization as taxonomy_mapper for consistency.

    Args:
        text: Text to normalize

    Returns:
        Normalized text suitable for dictionary lookup
    """
    if not text:
        return ""

    # NFD decomposition to separate base characters from combining marks
    normalized = unicodedata.normalize("NFD", text)

    # Remove combining marks (accents)
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    # Lowercase and strip
    return normalized.lower().strip()


def load_aliases_sync(
    db_secret_arn: str,
    cache_ttl_minutes: int = DynamicAliasLoader.DEFAULT_TTL_MINUTES,
    region: str = "eu-north-1",
) -> dict[str, AliasEntry]:
    """
    Synchronous wrapper for loading aliases.

    For use in non-async contexts like Lambda handlers.

    Args:
        db_secret_arn: AWS Secrets Manager ARN
        cache_ttl_minutes: Cache TTL
        region: AWS region

    Returns:
        Dictionary mapping normalized terms to AliasEntry objects
    """
    loader = DynamicAliasLoader(
        db_secret_arn=db_secret_arn,
        cache_ttl_minutes=cache_ttl_minutes,
        region=region,
    )

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(loader.load_all())
    finally:
        loop.close()
        loader.close()


# Module-level cache for Lambda warm starts
_global_loader: DynamicAliasLoader | None = None


def get_global_loader(
    db_secret_arn: str,
    cache_ttl_minutes: int = DynamicAliasLoader.DEFAULT_TTL_MINUTES,
    region: str = "eu-north-1",
) -> DynamicAliasLoader:
    """
    Get or create a global alias loader instance.

    Uses a module-level singleton to preserve cache across Lambda invocations
    (warm starts). The loader will still refresh when cache TTL expires.

    Args:
        db_secret_arn: AWS Secrets Manager ARN
        cache_ttl_minutes: Cache TTL
        region: AWS region

    Returns:
        DynamicAliasLoader instance (cached globally)
    """
    global _global_loader

    if _global_loader is None:
        _global_loader = DynamicAliasLoader(
            db_secret_arn=db_secret_arn,
            cache_ttl_minutes=cache_ttl_minutes,
            region=region,
        )

    return _global_loader
