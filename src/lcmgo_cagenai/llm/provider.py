"""Abstract LLM Provider with Bedrock implementation.

See docs/14-LLM-ABSTRACTION.md for full specification.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ModelType(Enum):
    """Available model types."""

    CLAUDE_SONNET = "claude-4-5-sonnet"
    CLAUDE_OPUS = "claude-4-5-opus"
    COHERE_EMBED = "cohere-embed-v3"


@dataclass
class LLMRequest:
    """Request to LLM provider."""

    prompt: str
    model: ModelType = ModelType.CLAUDE_SONNET
    max_tokens: int = 4096
    temperature: float = 0.0
    system: str | None = None


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cached: bool = False


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send completion request to LLM."""
        pass

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        pass


class BedrockProvider(LLMProvider):
    """AWS Bedrock implementation of LLMProvider.

    TODO: Implement with boto3 bedrock-runtime client.
    See docs/14-LLM-ABSTRACTION.md for implementation details.
    """

    def __init__(self, region: str = "eu-north-1"):
        self.region = region
        # TODO: Initialize boto3 client

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send completion request to Bedrock."""
        raise NotImplementedError("TODO: Implement Bedrock completion")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Cohere Embed v3."""
        raise NotImplementedError("TODO: Implement Cohere embedding")
