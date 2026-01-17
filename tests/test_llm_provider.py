"""Tests for LLM provider abstraction."""

import pytest

from lcmgo_cagenai.llm.provider import (
    BedrockProvider,
    LLMProvider,
    LLMRequest,
    ModelType,
)


class TestLLMRequest:
    """Tests for LLMRequest dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        request = LLMRequest(prompt="test")

        assert request.prompt == "test"
        assert request.model == ModelType.CLAUDE_SONNET
        assert request.max_tokens == 4096
        assert request.temperature == 0.0
        assert request.system is None


class TestBedrockProvider:
    """Tests for BedrockProvider."""

    def test_initialization(self):
        """Test provider initializes with correct region."""
        provider = BedrockProvider(region="eu-north-1")

        assert provider.region == "eu-north-1"

    def test_is_llm_provider(self):
        """Test BedrockProvider inherits from LLMProvider."""
        provider = BedrockProvider()

        assert isinstance(provider, LLMProvider)
