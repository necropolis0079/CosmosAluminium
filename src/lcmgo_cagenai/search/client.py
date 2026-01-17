"""
OpenSearch client for vector similarity search and hybrid text search.

Provides authenticated access to Amazon OpenSearch Service using AWS SigV4.
Supports k-NN vector search, BM25 text search, and hybrid search with RRF.

See docs/04-VECTORDB-OPENSEARCH.md for full specification.
"""

import logging
from typing import Any

import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection

from .mappings import (
    CANDIDATES_INDEX,
    CANDIDATES_INDEX_VERSIONED,
    CANDIDATES_MAPPING,
    INDEX_SETTINGS,
    JOBS_INDEX,
    JOBS_INDEX_VERSIONED,
    JOBS_MAPPING,
    get_full_mapping,
)

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """
    OpenSearch client with AWS SigV4 authentication.

    Provides methods for:
    - Index management (create, delete, refresh)
    - Document operations (index, bulk index, delete)
    - Vector search (k-NN)
    - Text search (BM25)
    - Hybrid search (k-NN + BM25 with RRF)

    Example:
        client = OpenSearchClient(
            host="vpc-xxx.eu-north-1.es.amazonaws.com",
            region="eu-north-1"
        )

        # Create indices
        client.create_candidates_index()
        client.create_jobs_index()

        # Index a candidate
        client.index_document(
            index=CANDIDATES_INDEX,
            doc_id="cand-123",
            document={...}
        )

        # Vector search
        results = client.vector_search(
            index=CANDIDATES_INDEX,
            field="cv_embedding",
            vector=[0.1, 0.2, ...],
            k=20
        )
    """

    def __init__(
        self,
        host: str,
        region: str = "eu-north-1",
        use_ssl: bool = True,
        verify_certs: bool = True,
    ):
        """
        Initialize OpenSearch client with AWS authentication.

        Args:
            host: OpenSearch domain endpoint (without https://)
            region: AWS region
            use_ssl: Whether to use SSL (should be True for AWS)
            verify_certs: Whether to verify SSL certificates
        """
        self.host = host.replace("https://", "").replace("http://", "")
        self.region = region

        # Get AWS credentials
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, region, "es")

        # Initialize client
        self._client = OpenSearch(
            hosts=[{"host": self.host, "port": 443}],
            http_auth=auth,
            use_ssl=use_ssl,
            verify_certs=verify_certs,
            connection_class=RequestsHttpConnection,
            timeout=30,
        )

        logger.info(f"OpenSearch client initialized for {self.host}")

    @property
    def client(self) -> OpenSearch:
        """Get the underlying OpenSearch client."""
        return self._client

    # -------------------------------------------------------------------------
    # Index Management
    # -------------------------------------------------------------------------

    def create_index(
        self,
        index: str,
        body: dict,
        alias: str | None = None,
    ) -> dict:
        """
        Create an index with settings and mappings.

        Args:
            index: Index name (e.g., cosmos-hr-candidates-v1)
            body: Index settings and mappings
            alias: Optional alias to create pointing to this index

        Returns:
            OpenSearch response
        """
        if self._client.indices.exists(index=index):
            logger.warning(f"Index {index} already exists, skipping creation")
            return {"acknowledged": True, "index": index, "existed": True}

        logger.info(f"Creating index {index}")
        response = self._client.indices.create(index=index, body=body)

        # Create alias if specified
        if alias:
            self._client.indices.put_alias(index=index, name=alias)
            logger.info(f"Created alias {alias} -> {index}")

        return response

    def create_candidates_index(self) -> dict:
        """
        Create the candidates index with k-NN mappings.

        Creates versioned index (cosmos-hr-candidates-v1) with alias
        pointing to it (cosmos-hr-candidates).

        Returns:
            OpenSearch response
        """
        body = get_full_mapping(CANDIDATES_MAPPING)
        return self.create_index(
            index=CANDIDATES_INDEX_VERSIONED,
            body=body,
            alias=CANDIDATES_INDEX,
        )

    def create_jobs_index(self) -> dict:
        """
        Create the jobs index with k-NN mappings.

        Returns:
            OpenSearch response
        """
        body = get_full_mapping(JOBS_MAPPING)
        return self.create_index(
            index=JOBS_INDEX_VERSIONED,
            body=body,
            alias=JOBS_INDEX,
        )

    def create_all_indices(self) -> dict[str, dict]:
        """
        Create all required indices.

        Returns:
            Dict with index names and their creation responses
        """
        return {
            CANDIDATES_INDEX: self.create_candidates_index(),
            JOBS_INDEX: self.create_jobs_index(),
        }

    def delete_index(self, index: str) -> dict:
        """
        Delete an index.

        Args:
            index: Index name to delete

        Returns:
            OpenSearch response
        """
        if not self._client.indices.exists(index=index):
            logger.warning(f"Index {index} does not exist")
            return {"acknowledged": True, "existed": False}

        logger.info(f"Deleting index {index}")
        return self._client.indices.delete(index=index)

    def refresh_index(self, index: str) -> dict:
        """
        Refresh index to make recent changes searchable.

        Args:
            index: Index name

        Returns:
            OpenSearch response
        """
        return self._client.indices.refresh(index=index)

    def get_index_stats(self, index: str) -> dict:
        """
        Get index statistics.

        Args:
            index: Index name

        Returns:
            Index stats including doc count, size, etc.
        """
        return self._client.indices.stats(index=index)

    # -------------------------------------------------------------------------
    # Document Operations
    # -------------------------------------------------------------------------

    def index_document(
        self,
        index: str,
        doc_id: str,
        document: dict,
        refresh: bool = False,
    ) -> dict:
        """
        Index a single document.

        Args:
            index: Index name
            doc_id: Document ID
            document: Document body
            refresh: Whether to refresh index after indexing

        Returns:
            OpenSearch response
        """
        return self._client.index(
            index=index,
            id=doc_id,
            body=document,
            refresh=refresh,
        )

    def bulk_index(
        self,
        index: str,
        documents: list[dict],
        id_field: str = "candidate_id",
        batch_size: int = 500,
    ) -> dict:
        """
        Bulk index multiple documents.

        Args:
            index: Index name
            documents: List of documents to index
            id_field: Field to use as document ID
            batch_size: Number of documents per batch

        Returns:
            Summary of bulk operation
        """
        from opensearchpy.helpers import bulk

        actions = [
            {
                "_index": index,
                "_id": doc.get(id_field, doc.get("id")),
                "_source": doc,
            }
            for doc in documents
        ]

        success, errors = bulk(
            self._client,
            actions,
            chunk_size=batch_size,
            request_timeout=120,
            refresh=False,
        )

        # Refresh once at end
        self._client.indices.refresh(index=index)

        return {"success": success, "errors": errors}

    def get_document(self, index: str, doc_id: str) -> dict | None:
        """
        Get a document by ID.

        Args:
            index: Index name
            doc_id: Document ID

        Returns:
            Document source or None if not found
        """
        try:
            response = self._client.get(index=index, id=doc_id)
            return response["_source"]
        except Exception:
            return None

    def delete_document(self, index: str, doc_id: str) -> dict:
        """
        Delete a document by ID.

        Args:
            index: Index name
            doc_id: Document ID

        Returns:
            OpenSearch response
        """
        return self._client.delete(index=index, id=doc_id)

    # -------------------------------------------------------------------------
    # Search Operations
    # -------------------------------------------------------------------------

    def vector_search(
        self,
        index: str,
        field: str,
        vector: list[float],
        k: int = 20,
        filters: dict | None = None,
        source_fields: list[str] | None = None,
    ) -> list[dict]:
        """
        Perform k-NN vector similarity search.

        Args:
            index: Index name
            field: Vector field name (e.g., cv_embedding)
            vector: Query vector (1024-dimensional)
            k: Number of results to return
            filters: Optional filter clause
            source_fields: Fields to include in response

        Returns:
            List of matching documents with scores
        """
        query = {
            "knn": {
                field: {
                    "vector": vector,
                    "k": k,
                }
            }
        }

        # Add filters if provided
        if filters:
            query = {
                "bool": {
                    "must": [query],
                    "filter": filters,
                }
            }

        body = {"size": k, "query": query}

        if source_fields:
            body["_source"] = source_fields

        response = self._client.search(index=index, body=body)

        return [
            {
                "id": hit["_id"],
                "score": hit["_score"],
                **hit["_source"],
            }
            for hit in response["hits"]["hits"]
        ]

    def text_search(
        self,
        index: str,
        query: str,
        fields: list[str] | None = None,
        size: int = 20,
        filters: dict | None = None,
    ) -> list[dict]:
        """
        Perform BM25 text search.

        Args:
            index: Index name
            query: Search query text
            fields: Fields to search (default: cv_text)
            size: Number of results
            filters: Optional filter clause

        Returns:
            List of matching documents with scores
        """
        if fields is None:
            fields = ["cv_text"]

        match_query = {
            "multi_match": {
                "query": query,
                "fields": fields,
                "type": "best_fields",
                "analyzer": "greek_search_analyzer",
            }
        }

        if filters:
            search_query = {
                "bool": {
                    "must": [match_query],
                    "filter": filters,
                }
            }
        else:
            search_query = match_query

        body = {"size": size, "query": search_query}

        response = self._client.search(index=index, body=body)

        return [
            {
                "id": hit["_id"],
                "score": hit["_score"],
                **hit["_source"],
            }
            for hit in response["hits"]["hits"]
        ]

    def hybrid_search(
        self,
        index: str,
        query_text: str,
        query_vector: list[float],
        k: int = 20,
        vector_weight: float = 0.6,
        text_weight: float = 0.4,
        filters: dict | None = None,
    ) -> list[dict]:
        """
        Perform hybrid search combining vector and text search with RRF.

        Args:
            index: Index name
            query_text: Text query for BM25
            query_vector: Query vector for k-NN
            k: Number of results
            vector_weight: Weight for vector search (default 0.6)
            text_weight: Weight for text search (default 0.4)
            filters: Optional filter clause

        Returns:
            List of matching documents with combined scores
        """
        # Perform both searches
        vector_results = self.vector_search(
            index=index,
            field="cv_embedding",
            vector=query_vector,
            k=k * 2,  # Get more for RRF
            filters=filters,
        )

        text_results = self.text_search(
            index=index,
            query=query_text,
            size=k * 2,
            filters=filters,
        )

        # Calculate RRF scores
        rrf_constant = 60
        combined_scores: dict[str, dict[str, Any]] = {}

        for rank, doc in enumerate(vector_results, 1):
            doc_id = doc["id"]
            combined_scores[doc_id] = {
                "vector_rank": rank,
                "text_rank": None,
                "vector_score": vector_weight / (rrf_constant + rank),
                "text_score": 0,
                "doc": doc,
            }

        for rank, doc in enumerate(text_results, 1):
            doc_id = doc["id"]
            text_score = text_weight / (rrf_constant + rank)

            if doc_id in combined_scores:
                combined_scores[doc_id]["text_rank"] = rank
                combined_scores[doc_id]["text_score"] = text_score
            else:
                combined_scores[doc_id] = {
                    "vector_rank": None,
                    "text_rank": rank,
                    "vector_score": 0,
                    "text_score": text_score,
                    "doc": doc,
                }

        # Calculate final scores and sort
        results = []
        for doc_id, data in combined_scores.items():
            final_score = data["vector_score"] + data["text_score"]
            doc = data["doc"]
            doc["rrf_score"] = final_score
            doc["vector_rank"] = data["vector_rank"]
            doc["text_rank"] = data["text_rank"]
            results.append(doc)

        results.sort(key=lambda x: x["rrf_score"], reverse=True)
        return results[:k]

    # -------------------------------------------------------------------------
    # Health & Info
    # -------------------------------------------------------------------------

    def cluster_health(self) -> dict:
        """Get cluster health status."""
        return self._client.cluster.health()

    def list_indices(self) -> list[str]:
        """List all indices."""
        return list(self._client.indices.get_alias().keys())


def get_client(
    host: str | None = None,
    region: str = "eu-north-1",
) -> OpenSearchClient:
    """
    Get configured OpenSearch client.

    Args:
        host: OpenSearch endpoint (or use OPENSEARCH_ENDPOINT env var)
        region: AWS region

    Returns:
        OpenSearchClient instance
    """
    import os

    if host is None:
        host = os.environ.get("OPENSEARCH_ENDPOINT", "")
        if not host:
            raise ValueError(
                "OpenSearch host not provided. "
                "Set OPENSEARCH_ENDPOINT environment variable."
            )

    return OpenSearchClient(host=host, region=region)
