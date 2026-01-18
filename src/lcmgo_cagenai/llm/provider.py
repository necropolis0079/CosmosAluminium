"""
LLM Provider abstraction with AWS Bedrock implementation.

Supports Claude 4.5 (Sonnet, Opus, Haiku) and Cohere Embed v4.
Uses EU inference profiles for eu-north-1 region.

See docs/14-LLM-ABSTRACTION.md for full specification.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import boto3

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Available model types."""

    CLAUDE_OPUS = "claude-4-5-opus"
    CLAUDE_SONNET = "claude-4-5-sonnet"
    CLAUDE_HAIKU = "claude-4-5-haiku"
    COHERE_EMBED = "cohere-embed-v4"


# EU inference profile IDs for eu-north-1
EU_MODEL_IDS = {
    ModelType.CLAUDE_OPUS: "eu.anthropic.claude-opus-4-5-20251101-v1:0",
    ModelType.CLAUDE_SONNET: "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
    ModelType.CLAUDE_HAIKU: "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
    ModelType.COHERE_EMBED: "eu.cohere.embed-v4:0",
}


@dataclass
class LLMRequest:
    """Request to LLM provider."""

    prompt: str
    model: ModelType = ModelType.CLAUDE_SONNET
    max_tokens: int = 4096
    temperature: float = 0.0
    system: str | None = None
    images: list[dict] = field(default_factory=list)  # For vision requests


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cached: bool = False
    stop_reason: str | None = None


@dataclass
class EmbeddingResponse:
    """Response from embedding request."""

    embeddings: list[list[float]]
    model: str
    input_tokens: int
    latency_ms: float


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send completion request to LLM."""
        pass

    @abstractmethod
    async def embed(self, texts: list[str]) -> EmbeddingResponse:
        """Generate embeddings for texts."""
        pass

    @abstractmethod
    async def vision(
        self, image_data: str, prompt: str, media_type: str = "image/png"
    ) -> LLMResponse:
        """Process image with vision model."""
        pass


class BedrockProvider(LLMProvider):
    """
    AWS Bedrock implementation of LLMProvider.

    Uses EU inference profiles for eu-north-1 region to ensure
    data residency compliance.

    Example:
        provider = BedrockProvider(region="eu-north-1")

        # Text completion
        response = await provider.complete(LLMRequest(
            prompt="Translate to Greek: Hello",
            model=ModelType.CLAUDE_SONNET
        ))

        # Vision (for CV OCR)
        response = await provider.vision(
            image_data=base64_image,
            prompt="Extract all text from this CV"
        )

        # Embeddings (for vector search)
        embeddings = await provider.embed(["skill: welding", "skill: TIG welding"])
    """

    def __init__(self, region: str = "eu-north-1"):
        """
        Initialize Bedrock provider.

        Args:
            region: AWS region (should be eu-north-1 for EU data residency)
        """
        self.region = region
        self._client = None

    @property
    def client(self):
        """Lazy-load Bedrock runtime client."""
        if self._client is None:
            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Send completion request to Bedrock.

        Args:
            request: LLMRequest with prompt and parameters

        Returns:
            LLMResponse with generated content
        """
        model_id = EU_MODEL_IDS[request.model]
        start = time.time()

        logger.debug(f"Bedrock completion request: model={request.model.value}")

        # Build messages
        messages = [{"role": "user", "content": request.prompt}]

        # Build request body
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": request.max_tokens,
            "messages": messages,
        }

        if request.temperature > 0:
            body["temperature"] = request.temperature

        if request.system:
            body["system"] = request.system

        # Invoke model
        response = self.client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        latency_ms = (time.time() - start) * 1000

        return LLMResponse(
            content=response_body["content"][0]["text"],
            model=model_id,
            input_tokens=response_body.get("usage", {}).get("input_tokens", 0),
            output_tokens=response_body.get("usage", {}).get("output_tokens", 0),
            latency_ms=latency_ms,
            stop_reason=response_body.get("stop_reason"),
        )

    async def vision(
        self,
        image_data: str,
        prompt: str,
        media_type: str = "image/png",
        model: ModelType = ModelType.CLAUDE_SONNET,
    ) -> LLMResponse:
        """
        Process image with Claude Vision.

        Args:
            image_data: Base64-encoded image data
            prompt: Text prompt to accompany the image
            media_type: MIME type of image (image/png, image/jpeg, etc.)
            model: Model to use (Sonnet or Opus recommended for vision)

        Returns:
            LLMResponse with extracted/analyzed content
        """
        model_id = EU_MODEL_IDS[model]
        start = time.time()

        logger.debug(f"Bedrock vision request: model={model.value}")

        # Build request body with image
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 8000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }

        # Invoke model
        response = self.client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        latency_ms = (time.time() - start) * 1000

        return LLMResponse(
            content=response_body["content"][0]["text"],
            model=model_id,
            input_tokens=response_body.get("usage", {}).get("input_tokens", 0),
            output_tokens=response_body.get("usage", {}).get("output_tokens", 0),
            latency_ms=latency_ms,
            stop_reason=response_body.get("stop_reason"),
        )

    async def embed(self, texts: list[str]) -> EmbeddingResponse:
        """
        Generate embeddings using Cohere Embed v4.

        Args:
            texts: List of texts to embed

        Returns:
            EmbeddingResponse with 1024-dimensional embeddings
        """
        model_id = EU_MODEL_IDS[ModelType.COHERE_EMBED]
        start = time.time()

        logger.debug(f"Bedrock embedding request: {len(texts)} texts")

        # Build request body for Cohere Embed v4
        body = {
            "texts": texts,
            "input_type": "search_document",
            "embedding_types": ["float"],
            "output_dimension": 1024,  # Match OpenSearch k-NN config
        }

        logger.info(f"Cohere embed request: model={model_id}, texts_count={len(texts)}, first_text_len={len(texts[0]) if texts else 0}")

        # Invoke model
        response = self.client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        latency_ms = (time.time() - start) * 1000

        # Cohere Embed v4 returns embeddings as {"float": [[...]]} or {"int8": [[...]]}
        # Handle both new nested format and legacy flat format
        embeddings_data = response_body["embeddings"]
        if isinstance(embeddings_data, dict):
            # New format: {"float": [[...]], ...} or {"int8": [[...]], ...}
            # Prefer float format
            embeddings = embeddings_data.get("float") or embeddings_data.get("int8") or []
        else:
            # Legacy format: [[...]]
            embeddings = embeddings_data

        return EmbeddingResponse(
            embeddings=embeddings,
            model=model_id,
            input_tokens=response_body.get("meta", {}).get("billed_units", {}).get("input_tokens", 0),
            latency_ms=latency_ms,
        )

    async def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.

        Uses input_type="search_query" for optimal retrieval performance.

        Args:
            query: Search query text

        Returns:
            1024-dimensional embedding vector
        """
        model_id = EU_MODEL_IDS[ModelType.COHERE_EMBED]

        # Cohere Embed v4 request body
        body = {
            "texts": [query],
            "input_type": "search_query",
            "embedding_types": ["float"],
            "output_dimension": 1024,  # Match OpenSearch k-NN config
        }

        logger.info(f"Cohere embed_query request: model={model_id}, query_len={len(query)}")

        try:
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())

            # Cohere Embed v4 returns embeddings as {"float": [[...]]} or {"int8": [[...]]}
            embeddings_data = response_body["embeddings"]
            if isinstance(embeddings_data, dict):
                embeddings = embeddings_data.get("float") or embeddings_data.get("int8") or []
            else:
                embeddings = embeddings_data

            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.error(f"Cohere embed_query failed: {type(e).__name__}: {e}")
            raise


# Convenience function for simple usage
def get_provider(region: str = "eu-north-1") -> BedrockProvider:
    """
    Get a configured Bedrock provider instance.

    Args:
        region: AWS region (default: eu-north-1)

    Returns:
        BedrockProvider instance
    """
    return BedrockProvider(region=region)
