"""
Search Indexer for indexing parsed CV data to OpenSearch.

Generates embeddings using Cohere Embed v4 and indexes documents
to OpenSearch for hybrid search (k-NN + BM25).
"""

import logging
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from ..llm.provider import BedrockProvider
from ..search.client import OpenSearchClient
from ..search.mappings import CANDIDATES_INDEX
from .schema import ParsedCV
from .taxonomy_mapper import normalize_text

logger = logging.getLogger(__name__)


class SearchIndexer:
    """
    Indexes parsed CV data to OpenSearch with embeddings.

    Generates 1024-dimensional Cohere embeddings for semantic search
    and indexes documents to the cosmos-hr-candidates index.

    Example:
        indexer = SearchIndexer(
            opensearch_endpoint="vpc-xxx.eu-north-1.es.amazonaws.com"
        )
        await indexer.index_candidate(candidate_id, parsed_cv)
    """

    def __init__(
        self,
        opensearch_endpoint: str | None = None,
        region: str = "eu-north-1",
    ):
        """
        Initialize search indexer.

        Args:
            opensearch_endpoint: OpenSearch domain endpoint
            region: AWS region
        """
        self.region = region
        self._opensearch_endpoint = opensearch_endpoint
        self._client: OpenSearchClient | None = None
        self._provider: BedrockProvider | None = None

    @property
    def client(self) -> OpenSearchClient:
        """Lazy-load OpenSearch client."""
        if self._client is None:
            import os

            endpoint = self._opensearch_endpoint or os.environ.get("OPENSEARCH_ENDPOINT")
            if not endpoint:
                raise ValueError("OpenSearch endpoint not configured")

            self._client = OpenSearchClient(host=endpoint, region=self.region)

        return self._client

    @property
    def provider(self) -> BedrockProvider:
        """Lazy-load Bedrock provider."""
        if self._provider is None:
            self._provider = BedrockProvider(region=self.region)
        return self._provider

    async def index_candidate(
        self,
        candidate_id: UUID,
        parsed_cv: ParsedCV,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """
        Index a candidate to OpenSearch.

        Args:
            candidate_id: PostgreSQL candidate ID
            parsed_cv: Parsed CV data
            refresh: Whether to refresh index after indexing

        Returns:
            OpenSearch indexing response
        """
        logger.info(f"Indexing candidate {candidate_id} to OpenSearch")

        # Build embedding text
        embedding_text = self._build_embedding_text(parsed_cv)

        # Generate embedding
        embedding = await self._generate_embedding(embedding_text)

        # Build document
        document = self._build_document(candidate_id, parsed_cv, embedding)

        # Index to OpenSearch
        response = self.client.index_document(
            index=CANDIDATES_INDEX,
            doc_id=str(candidate_id),
            document=document,
            refresh=refresh,
        )

        logger.info(f"Indexed candidate {candidate_id}: result={response.get('result')}")
        return response

    async def bulk_index_candidates(
        self,
        candidates: list[tuple[UUID, ParsedCV]],
    ) -> dict[str, Any]:
        """
        Bulk index multiple candidates.

        Args:
            candidates: List of (candidate_id, parsed_cv) tuples

        Returns:
            Bulk indexing summary
        """
        if not candidates:
            return {"success": 0, "errors": 0}

        # Build documents with embeddings
        documents = []

        for candidate_id, parsed_cv in candidates:
            embedding_text = self._build_embedding_text(parsed_cv)
            embedding = await self._generate_embedding(embedding_text)
            document = self._build_document(candidate_id, parsed_cv, embedding)
            documents.append(document)

        # Bulk index
        return self.client.bulk_index(
            index=CANDIDATES_INDEX,
            documents=documents,
            id_field="candidate_id",
        )

    async def delete_candidate(self, candidate_id: UUID) -> dict[str, Any]:
        """
        Delete a candidate from OpenSearch.

        Args:
            candidate_id: Candidate ID to delete

        Returns:
            OpenSearch response
        """
        return self.client.delete_document(
            index=CANDIDATES_INDEX,
            doc_id=str(candidate_id),
        )

    def _build_embedding_text(self, parsed_cv: ParsedCV) -> str:
        """
        Build text for embedding generation.

        Combines key fields for semantic search:
        - Full name
        - Skills
        - Experience summary
        - Education summary

        Args:
            parsed_cv: Parsed CV data

        Returns:
            Text for embedding
        """
        parts = []

        # Name
        if parsed_cv.personal.first_name and parsed_cv.personal.last_name:
            parts.append(f"{parsed_cv.personal.first_name} {parsed_cv.personal.last_name}")

        # Skills
        if parsed_cv.skills:
            skills_text = ", ".join(s.name for s in parsed_cv.skills[:20])
            parts.append(f"Skills: {skills_text}")

        # Experience summary
        if parsed_cv.experience:
            for exp in parsed_cv.experience[:5]:
                exp_text = f"{exp.job_title} at {exp.company_name}"
                if exp.description:
                    exp_text += f": {exp.description[:200]}"
                parts.append(exp_text)

        # Education summary
        if parsed_cv.education:
            for edu in parsed_cv.education[:3]:
                edu_text = edu.institution_name
                if edu.degree_title:
                    edu_text += f" - {edu.degree_title}"
                parts.append(edu_text)

        # Languages
        if parsed_cv.languages:
            lang_text = ", ".join(
                f"{l.language_name} ({l.proficiency_level.value})"
                for l in parsed_cv.languages[:5]
            )
            parts.append(f"Languages: {lang_text}")

        # Certifications
        if parsed_cv.certifications:
            cert_text = ", ".join(c.certification_name for c in parsed_cv.certifications[:5])
            parts.append(f"Certifications: {cert_text}")

        # Training/Seminars
        if parsed_cv.training:
            training_text = ", ".join(t.training_name for t in parsed_cv.training[:5])
            parts.append(f"Training: {training_text}")

        return " | ".join(parts)

    async def _generate_embedding(self, text: str) -> list[float]:
        """
        Generate 1024-dimensional embedding.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        response = await self.provider.embed([text])
        return response.embeddings[0]

    def _build_document(
        self,
        candidate_id: UUID,
        parsed_cv: ParsedCV,
        embedding: list[float],
    ) -> dict[str, Any]:
        """
        Build OpenSearch document from parsed CV.

        Matches the cosmos-hr-candidates index mapping.

        Args:
            candidate_id: PostgreSQL candidate ID
            parsed_cv: Parsed CV data
            embedding: CV embedding vector

        Returns:
            Document dict for indexing
        """
        personal = parsed_cv.personal

        # Build full name
        full_name = f"{personal.first_name} {personal.last_name}".strip()
        full_name_normalized = normalize_text(full_name) if full_name else None

        # Calculate total experience
        total_experience_months = 0
        for exp in parsed_cv.experience:
            if exp.duration_months:
                total_experience_months += exp.duration_months

        # Get current position
        current_position = None
        current_company = None
        for exp in parsed_cv.experience:
            if exp.is_current:
                current_position = exp.job_title
                current_company = exp.company_name
                break

        # Get highest education
        highest_education = None
        if parsed_cv.education:
            # Simple heuristic: use first (often most recent)
            edu = parsed_cv.education[0]
            highest_education = {
                "level": edu.degree_level.value if edu.degree_level else None,
                "institution": edu.institution_name,
                "field": edu.field_of_study.value if edu.field_of_study else None,
                "year": edu.graduation_year,
            }

        # Build skills list
        skills = []
        for skill in parsed_cv.skills:
            skills.append({
                "name": skill.name,
                "name_normalized": normalize_text(skill.name),
                "canonical_id": skill.canonical_id,
                "level": skill.level.value if skill.level else None,
                "years": skill.years_of_experience,
            })

        # Build languages list
        languages = []
        for lang in parsed_cv.languages:
            languages.append({
                "code": lang.language_code,
                "name": lang.language_name,
                "level": lang.proficiency_level.value if lang.proficiency_level else "unknown",
                "is_native": lang.is_native,
            })

        # Build certifications list
        certifications = []
        for cert in parsed_cv.certifications:
            certifications.append({
                "name": cert.certification_name,
                "issuer": cert.issuing_organization,
                "valid": cert.is_current,
            })

        # Build training list
        training = []
        for t in parsed_cv.training:
            training.append({
                "name": t.training_name,
                "provider": t.provider_name,
                "type": t.training_type,
                "category": t.category,
                "duration_hours": t.duration_hours,
            })

        # Build driving licenses list
        driving_licenses = [
            dl.license_category.value for dl in parsed_cv.driving_licenses
        ]

        # Build document
        document = {
            "candidate_id": str(candidate_id),
            "full_name": full_name,
            "full_name_normalized": full_name_normalized,
            "email": personal.email,
            "phone": personal.phone,
            "location": {
                "city": personal.address_city,
                "region": personal.address_region,
                "country": personal.address_country,
            },
            "availability": personal.availability_status.value
            if personal.availability_status
            else "unknown",
            "military_status": personal.military_status.value
            if personal.military_status
            else "unknown",
            "total_experience_months": total_experience_months,
            "total_experience_years": total_experience_months / 12 if total_experience_months else 0,
            "current_position": current_position,
            "current_company": current_company,
            "highest_education": highest_education,
            "skills": skills,
            "skills_list": [s.name for s in parsed_cv.skills],
            "languages": languages,
            "language_codes": [l.language_code for l in parsed_cv.languages],
            "certifications": certifications,
            "certification_names": [c.certification_name for c in parsed_cv.certifications],
            "training": training,
            "training_names": [t.training_name for t in parsed_cv.training],
            "driving_licenses": driving_licenses,
            "cv_text": parsed_cv.raw_cv_text[:10000] if parsed_cv.raw_cv_text else None,
            "cv_embedding": embedding,
            "quality_score": parsed_cv.completeness_score,
            "parsing_confidence": parsed_cv.overall_confidence,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "correlation_id": parsed_cv.correlation_id,
        }

        return document

    async def search_similar(
        self,
        query: str,
        k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for candidates similar to a query.

        Args:
            query: Search query text
            k: Number of results
            filters: Optional filters

        Returns:
            List of matching candidates
        """
        # Generate query embedding
        query_embedding = await self.provider.embed_query(query)

        # Hybrid search
        return self.client.hybrid_search(
            index=CANDIDATES_INDEX,
            query_text=query,
            query_vector=query_embedding,
            k=k,
            filters=filters,
        )
