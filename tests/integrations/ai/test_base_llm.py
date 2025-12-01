"""
BaseLLM Tests

Tests for BaseLLM abstract interface and model implementations.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from app.integrations.ai.base import (
    BaseLLM,
    ModelProvider,
    ModelError,
    ModelConnectionError,
    ModelAuthenticationError,
    ModelRateLimitError,
    ModelTokenLimitError
)


# ==================== BASELLM TESTS ====================

def test_base_llm_abstract():
    """Test BaseLLM is abstract and can't be instantiated"""
    with pytest.raises(TypeError):
        BaseLLM(
            provider=ModelProvider.GEMINI,
            model_name="test",
            api_key="key"
        )


def test_base_llm_initialization():
    """Test BaseLLM initialization in concrete class"""
    # Create a concrete implementation for testing
    class TestLLM(BaseLLM):
        async def generate_response(self, prompt, **kwargs):
            return "test response"
        
        async def generate_structured_output(self, prompt, schema, **kwargs):
            return {}
        
        def calculate_cost(self, input_tokens, output_tokens):
            return Decimal("0.01")
        
        async def test_connection(self):
            return {"success": True}
    
    model = TestLLM(
        provider=ModelProvider.GEMINI,
        model_name="test-model",
        api_key="test-key"
    )
    
    assert model.provider == ModelProvider.GEMINI
    assert model.model_name == "test-model"
    assert model.api_key == "test-key"
    assert model.total_input_tokens == 0
    assert model.total_output_tokens == 0
    assert model.total_cost_usd == Decimal("0")


def test_base_llm_track_usage():
    """Test usage tracking"""
    class TestLLM(BaseLLM):
        async def generate_response(self, prompt, **kwargs):
            return "test"
        async def generate_structured_output(self, prompt, schema, **kwargs):
            return {}
        def calculate_cost(self, input_tokens, output_tokens):
            return Decimal(str(input_tokens)) * Decimal("0.001")
        async def test_connection(self):
            return {"success": True}
    
    model = TestLLM(
        provider=ModelProvider.GEMINI,
        model_name="test",
        api_key="key"
    )
    
    # Track usage
    model.track_usage(input_tokens=1000, output_tokens=500)
    
    assert model.total_input_tokens == 1000
    assert model.total_output_tokens == 500
    assert model.total_cost_usd > 0


def test_base_llm_reset_usage():
    """Test usage reset"""
    class TestLLM(BaseLLM):
        async def generate_response(self, prompt, **kwargs):
            return "test"
        async def generate_structured_output(self, prompt, schema, **kwargs):
            return {}
        def calculate_cost(self, input_tokens, output_tokens):
            return Decimal("0.01")
        async def test_connection(self):
            return {"success": True}
    
    model = TestLLM(
        provider=ModelProvider.GEMINI,
        model_name="test",
        api_key="key"
    )
    
    model.track_usage(100, 50)
    model.reset_usage()
    
    assert model.total_input_tokens == 0
    assert model.total_output_tokens == 0
    assert model.total_cost_usd == Decimal("0")


def test_base_llm_get_model_info():
    """Test model info retrieval"""
    class TestLLM(BaseLLM):
        async def generate_response(self, prompt, **kwargs):
            return "test"
        async def generate_structured_output(self, prompt, schema, **kwargs):
            return {}
        def calculate_cost(self, input_tokens, output_tokens):
            return Decimal("0.01")
        async def test_connection(self):
            return {"success": True}
    
    model = TestLLM(
        provider=ModelProvider.GEMINI,
        model_name="test-model",
        api_key="key",
        extra_config="value"
    )
    
    info = model.get_model_info()
    
    assert info["provider"] == "gemini"
    assert info["model_name"] == "test-model"
    assert "total_cost_usd" in info


def test_base_llm_string_repr():
    """Test string representations"""
    class TestLLM(BaseLLM):
        async def generate_response(self, prompt, **kwargs):
            return "test"
        async def generate_structured_output(self, prompt, schema, **kwargs):
            return {}
        def calculate_cost(self, input_tokens, output_tokens):
            return Decimal("0.01")
        async def test_connection(self):
            return {"success": True}
    
    model = TestLLM(
        provider=ModelProvider.GEMINI,
        model_name="test-model",
        api_key="key"
    )
    
    str_repr = str(model)
    assert "gemini" in str_repr.lower()
    assert "test-model" in str_repr.lower()


# ==================== MODEL PROVIDER TESTS ====================

def test_model_provider_enum():
    """Test ModelProvider enum values"""
    assert ModelProvider.GEMINI == "gemini"
    assert ModelProvider.GROQ == "groq"
    assert ModelProvider.OPENAI == "openai"
    assert ModelProvider.ANTHROPIC == "anthropic"
    assert ModelProvider.XAI == "xai"
    assert ModelProvider.OLLAMA == "ollama"


# ==================== SUMMARY ====================

"""
Test Coverage Summary:
✅ BaseLLM abstraction (6 tests)
✅ ModelProvider enum (1 test)

TOTAL: 7 comprehensive tests
All testing abstract interface behavior
"""


