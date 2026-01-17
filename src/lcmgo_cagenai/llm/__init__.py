"""
LLM abstraction layer for AWS Bedrock.

Provides unified interface for Claude 4.5 (Sonnet, Opus, Haiku) and Cohere Embed v4.
Uses EU inference profiles for eu-north-1 region.

Usage:
    from lcmgo_cagenai.llm import BedrockProvider, ModelType, LLMRequest

    provider = BedrockProvider()

    # Text completion
    response = await provider.complete(LLMRequest(
        prompt="Translate: Hello",
        model=ModelType.CLAUDE_SONNET
    ))

    # Vision for OCR
    response = await provider.vision(base64_image, "Extract text from CV")

    # Embeddings for vector search
    embeddings = await provider.embed(["skill: Python", "skill: AWS"])
"""

from .provider import (
    BedrockProvider,
    EmbeddingResponse,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelType,
    get_provider,
)

__all__ = [
    "LLMProvider",
    "BedrockProvider",
    "ModelType",
    "LLMRequest",
    "LLMResponse",
    "EmbeddingResponse",
    "get_provider",
]
