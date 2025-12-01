"""
Groq Model Tests

Comprehensive tests for Groq LLM integration.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from app.integrations.ai.groq_model import GroqModel
from app.integrations.ai.base import (
    ModelProvider,
    ModelAuthenticationError,
    ModelConnectionError,
    ModelRateLimitError
)


# ==================== FIXTURES ====================

@pytest.fixture
def valid_api_key():
    """Valid API key"""
    return "test_groq_api_key_456"


@pytest.fixture
def groq_model(valid_api_key):
    """Create GroqModel instance"""
    with patch('groq.AsyncGroq') as mock_groq:
        mock_client = AsyncMock()
        mock_groq.return_value = mock_client
        model = GroqModel(
            model_name="llama-3.3-70b-versatile",
            api_key=valid_api_key
        )
        model.client = mock_client
        return model


# ==================== INITIALIZATION TESTS ====================

def test_groq_init_success(valid_api_key):
    """Test successful Groq initialization"""
    with patch('groq.AsyncGroq') as mock_groq:
        mock_client = AsyncMock()
        mock_groq.return_value = mock_client
        
        model = GroqModel(
            model_name="llama-3.3-70b-versatile",
            api_key=valid_api_key
        )
        
        assert model.provider == ModelProvider.GROQ
        assert model.model_name == "llama-3.3-70b-versatile"
        assert model.api_key == valid_api_key


def test_groq_init_missing_api_key():
    """Test initialization fails without API key"""
    with pytest.raises(ModelAuthenticationError, match="API key is required"):
        GroqModel(model_name="llama-3.3-70b-versatile", api_key="")


# ==================== GENERATE RESPONSE TESTS ====================

@pytest.mark.asyncio
async def test_generate_response_success(groq_model):
    """Test successful text generation"""
    mock_choice = Mock()
    mock_choice.message.content = "This is a test response from Groq"
    
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    
    groq_model.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    result = await groq_model.generate_response(
        prompt="Test prompt",
        temperature=0.7
    )
    
    assert result == "This is a test response from Groq"
    assert groq_model.total_input_tokens == 100
    assert groq_model.total_output_tokens == 50


@pytest.mark.asyncio
async def test_generate_response_with_system_prompt(groq_model):
    """Test generation with system prompt"""
    mock_choice = Mock()
    mock_choice.message.content = "Response"
    
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 150
    mock_response.usage.completion_tokens = 30
    
    groq_model.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    result = await groq_model.generate_response(
        prompt="User prompt",
        system_prompt="System instructions",
        temperature=0.5
    )
    
    assert result == "Response"
    # Verify system prompt was included in messages
    call_args = groq_model.client.chat.completions.create.call_args
    messages = call_args[1]["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


@pytest.mark.asyncio
async def test_generate_response_with_max_tokens(groq_model):
    """Test generation with max tokens limit"""
    mock_choice = Mock()
    mock_choice.message.content = "Short response"
    
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 20
    
    groq_model.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    result = await groq_model.generate_response(
        prompt="Test",
        max_tokens=100
    )
    
    assert result == "Short response"
    
    # Verify max_tokens was passed
    call_args = groq_model.client.chat.completions.create.call_args
    assert call_args[1]["max_tokens"] == 100


@pytest.mark.asyncio
async def test_generate_response_authentication_error(groq_model):
    """Test authentication error handling"""
    groq_model.client.chat.completions.create = AsyncMock(
        side_effect=Exception("Invalid API key")
    )
    
    with pytest.raises(ModelAuthenticationError):
        await groq_model.generate_response(prompt="Test")


@pytest.mark.asyncio
async def test_generate_response_rate_limit_error(groq_model):
    """Test rate limit error handling"""
    groq_model.client.chat.completions.create = AsyncMock(
        side_effect=Exception("Rate limit exceeded")
    )
    
    with pytest.raises(ModelRateLimitError):
        await groq_model.generate_response(prompt="Test")


# ==================== STRUCTURED OUTPUT TESTS ====================

@pytest.mark.asyncio
async def test_generate_structured_output_success(groq_model):
    """Test successful structured output generation"""
    import json
    
    mock_choice = Mock()
    mock_choice.message.content = json.dumps({
        "action": "buy",
        "confidence": 0.85
    })
    
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 200
    mock_response.usage.completion_tokens = 100
    
    groq_model.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "confidence": {"type": "number"}
        }
    }
    
    result = await groq_model.generate_structured_output(
        prompt="Analyze market",
        schema=schema,
        temperature=0.3
    )
    
    assert result["action"] == "buy"
    assert result["confidence"] == 0.85
    
    # Verify JSON mode was used
    call_args = groq_model.client.chat.completions.create.call_args
    assert call_args[1]["response_format"]["type"] == "json_object"


# ==================== COST CALCULATION TESTS ====================

def test_calculate_cost_llama_70b(groq_model):
    """Test cost calculation for LLaMA 70B"""
    cost = groq_model.calculate_cost(input_tokens=1000000, output_tokens=500000)
    
    # LLaMA 70B: $0.59 per 1M input, $0.79 per 1M output
    # Expected: (1 * 0.59) + (0.5 * 0.79) = 0.59 + 0.395 = 0.985
    expected_cost = Decimal("0.59") + Decimal("0.395")
    assert cost == expected_cost


def test_calculate_cost_llama_8b():
    """Test cost calculation for LLaMA 8B"""
    with patch('groq.AsyncGroq') as mock_groq:
        mock_client = AsyncMock()
        mock_groq.return_value = mock_client
        
        model = GroqModel(
            model_name="llama-3.1-8b-instant",
            api_key="key"
        )
        
        cost = model.calculate_cost(input_tokens=1000000, output_tokens=500000)
        
        # LLaMA 8B: $0.05 per 1M input, $0.08 per 1M output
        # Expected: (1 * 0.05) + (0.5 * 0.08) = 0.05 + 0.04 = 0.09
        expected_cost = Decimal("0.05") + Decimal("0.04")
        assert cost == expected_cost


# ==================== CONNECTION TEST TESTS ====================

@pytest.mark.asyncio
async def test_connection_success(groq_model):
    """Test successful connection test"""
    mock_choice = Mock()
    mock_choice.message.content = "OK"
    
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    
    groq_model.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    result = await groq_model.test_connection()
    
    assert result["success"] is True
    assert result["provider"] == "groq"
    assert result["model_name"] == "llama-3.3-70b-versatile"
    assert "latency_ms" in result
    assert result["response"] == "OK"


@pytest.mark.asyncio
async def test_connection_failure(groq_model):
    """Test connection test failure"""
    groq_model.client.chat.completions.create = AsyncMock(
        side_effect=Exception("Connection failed")
    )
    
    with pytest.raises(ModelConnectionError):
        await groq_model.test_connection()


# ==================== SUMMARY ====================

"""
Test Coverage Summary:
✅ Initialization (2 tests)
✅ Generate response (4 tests)
✅ Structured output (1 test)
✅ Cost calculation (2 tests)
✅ Connection test (2 tests)

TOTAL: 11 comprehensive tests
All using mocked Groq API responses
"""


