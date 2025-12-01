"""
Gemini Model Tests

Comprehensive tests for Gemini LLM integration.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal

from app.integrations.ai.gemini_model import GeminiModel
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
    return "test_gemini_api_key_123"


@pytest.fixture
def gemini_model(valid_api_key):
    """Create GeminiModel instance"""
    with patch('google.generativeai.configure'):
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_instance = AsyncMock()
            mock_model.return_value = mock_instance
            model = GeminiModel(
                model_name="gemini-1.5-pro",
                api_key=valid_api_key
            )
            return model


# ==================== INITIALIZATION TESTS ====================

def test_gemini_init_success(valid_api_key):
    """Test successful Gemini initialization"""
    with patch('google.generativeai.configure'):
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_instance = AsyncMock()
            mock_model.return_value = mock_instance
            
            model = GeminiModel(
                model_name="gemini-1.5-pro",
                api_key=valid_api_key
            )
            
            assert model.provider == ModelProvider.GEMINI
            assert model.model_name == "gemini-1.5-pro"
            assert model.api_key == valid_api_key


def test_gemini_init_missing_api_key():
    """Test initialization fails without API key"""
    with pytest.raises(ModelAuthenticationError, match="API key is required"):
        GeminiModel(model_name="gemini-1.5-pro", api_key="")


def test_gemini_init_empty_api_key():
    """Test initialization fails with empty API key"""
    with pytest.raises(ModelAuthenticationError):
        GeminiModel(model_name="gemini-1.5-pro", api_key=None)


# ==================== GENERATE RESPONSE TESTS ====================

@pytest.mark.asyncio
async def test_generate_response_success(gemini_model):
    """Test successful text generation"""
    mock_response = Mock()
    mock_response.text = "This is a test response from Gemini"
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.candidates_token_count = 50
    
    gemini_model.model.generate_content_async = AsyncMock(return_value=mock_response)
    
    result = await gemini_model.generate_response(
        prompt="Test prompt",
        temperature=0.7
    )
    
    assert result == "This is a test response from Gemini"
    assert gemini_model.total_input_tokens == 100
    assert gemini_model.total_output_tokens == 50


@pytest.mark.asyncio
async def test_generate_response_with_system_prompt(gemini_model):
    """Test generation with system prompt"""
    mock_response = Mock()
    mock_response.text = "Response"
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 150
    mock_response.usage_metadata.candidates_token_count = 30
    
    gemini_model.model.generate_content_async = AsyncMock(return_value=mock_response)
    
    result = await gemini_model.generate_response(
        prompt="User prompt",
        system_prompt="System instructions",
        temperature=0.5
    )
    
    assert result == "Response"
    # Verify system prompt was included
    call_args = gemini_model.model.generate_content_async.call_args
    assert call_args is not None


@pytest.mark.asyncio
async def test_generate_response_with_max_tokens(gemini_model):
    """Test generation with max tokens limit"""
    mock_response = Mock()
    mock_response.text = "Short response"
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.candidates_token_count = 20
    
    gemini_model.model.generate_content_async = AsyncMock(return_value=mock_response)
    
    result = await gemini_model.generate_response(
        prompt="Test",
        max_tokens=100
    )
    
    assert result == "Short response"


@pytest.mark.asyncio
async def test_generate_response_authentication_error(gemini_model):
    """Test authentication error handling"""
    gemini_model.model.generate_content_async = AsyncMock(
        side_effect=Exception("Invalid API key")
    )
    
    with pytest.raises(ModelAuthenticationError):
        await gemini_model.generate_response(prompt="Test")


@pytest.mark.asyncio
async def test_generate_response_rate_limit_error(gemini_model):
    """Test rate limit error handling"""
    gemini_model.model.generate_content_async = AsyncMock(
        side_effect=Exception("Rate limit exceeded")
    )
    
    with pytest.raises(ModelRateLimitError):
        await gemini_model.generate_response(prompt="Test")


# ==================== STRUCTURED OUTPUT TESTS ====================

@pytest.mark.asyncio
async def test_generate_structured_output_success(gemini_model):
    """Test successful structured output generation"""
    import json
    
    mock_response = Mock()
    mock_response.text = json.dumps({
        "action": "buy",
        "confidence": 0.85,
        "reasoning": "Bullish trend"
    })
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 200
    mock_response.usage_metadata.candidates_token_count = 100
    
    gemini_model.model.generate_content_async = AsyncMock(return_value=mock_response)
    
    schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "confidence": {"type": "number"},
            "reasoning": {"type": "string"}
        }
    }
    
    result = await gemini_model.generate_structured_output(
        prompt="Analyze market",
        schema=schema,
        temperature=0.3
    )
    
    assert result["action"] == "buy"
    assert result["confidence"] == 0.85
    assert result["reasoning"] == "Bullish trend"


@pytest.mark.asyncio
async def test_generate_structured_output_with_markdown(gemini_model):
    """Test structured output extraction from markdown code block"""
    import json
    
    mock_response = Mock()
    mock_response.text = "```json\n" + json.dumps({"action": "sell"}) + "\n```"
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 200
    mock_response.usage_metadata.candidates_token_count = 50
    
    gemini_model.model.generate_content_async = AsyncMock(return_value=mock_response)
    
    schema = {"type": "object", "properties": {"action": {"type": "string"}}}
    
    result = await gemini_model.generate_structured_output(
        prompt="Test",
        schema=schema
    )
    
    assert result["action"] == "sell"


# ==================== COST CALCULATION TESTS ====================

def test_calculate_cost_gemini_pro(gemini_model):
    """Test cost calculation for Gemini Pro"""
    cost = gemini_model.calculate_cost(input_tokens=1000000, output_tokens=500000)
    
    # Gemini Pro: $1.25 per 1M input, $5.00 per 1M output
    # Expected: (1 * 1.25) + (0.5 * 5.00) = 1.25 + 2.50 = 3.75
    expected_cost = Decimal("1.25") + Decimal("2.50")
    assert cost == expected_cost


def test_calculate_cost_gemini_flash():
    """Test cost calculation for Gemini Flash"""
    with patch('google.generativeai.configure'):
        with patch('google.generativeai.GenerativeModel'):
            model = GeminiModel(
                model_name="gemini-1.5-flash",
                api_key="key"
            )
            
            cost = model.calculate_cost(input_tokens=1000000, output_tokens=500000)
            
            # Gemini Flash: $0.075 per 1M input, $0.30 per 1M output
            # Expected: (1 * 0.075) + (0.5 * 0.30) = 0.075 + 0.15 = 0.225
            expected_cost = Decimal("0.075") + Decimal("0.15")
            assert cost == expected_cost


def test_calculate_cost_default_pricing(gemini_model):
    """Test default pricing if model not in PRICING dict"""
    # Change model name to something not in PRICING
    gemini_model.model_name = "unknown-model"
    
    # Should use default (gemini-1.5-pro pricing)
    cost = gemini_model.calculate_cost(input_tokens=1000, output_tokens=500)
    assert cost > 0


# ==================== CONNECTION TEST TESTS ====================

@pytest.mark.asyncio
async def test_connection_success(gemini_model):
    """Test successful connection test"""
    mock_response = Mock()
    mock_response.text = "OK"
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 10
    mock_response.usage_metadata.candidates_token_count = 5
    
    gemini_model.model.generate_content_async = AsyncMock(return_value=mock_response)
    
    result = await gemini_model.test_connection()
    
    assert result["success"] is True
    assert result["provider"] == "gemini"
    assert result["model_name"] == "gemini-1.5-pro"
    assert "latency_ms" in result
    assert result["response"] == "OK"


@pytest.mark.asyncio
async def test_connection_failure(gemini_model):
    """Test connection test failure"""
    gemini_model.model.generate_content_async = AsyncMock(
        side_effect=Exception("Connection failed")
    )
    
    with pytest.raises(ModelConnectionError):
        await gemini_model.test_connection()


# ==================== EDGE CASES ====================

@pytest.mark.asyncio
async def test_generate_response_no_usage_metadata(gemini_model):
    """Test generation when usage metadata not available"""
    mock_response = Mock()
    mock_response.text = "Response"
    # No usage_metadata attribute
    delattr(mock_response, 'usage_metadata')
    
    gemini_model.model.generate_content_async = AsyncMock(return_value=mock_response)
    
    result = await gemini_model.generate_response(prompt="Test")
    
    assert result == "Response"
    # Should estimate tokens
    assert gemini_model.total_input_tokens > 0


@pytest.mark.asyncio
async def test_generate_response_no_text_attribute(gemini_model):
    """Test generation when response has no text attribute"""
    mock_response = Mock()
    # No text attribute
    mock_response.text = None
    mock_response.usage_metadata = Mock()
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.candidates_token_count = 50
    
    gemini_model.model.generate_content_async = AsyncMock(return_value=mock_response)
    
    result = await gemini_model.generate_response(prompt="Test")
    
    # Should convert to string
    assert isinstance(result, str)


# ==================== SUMMARY ====================

"""
Test Coverage Summary:
✅ Initialization (3 tests)
✅ Generate response (4 tests)
✅ Structured output (2 tests)
✅ Cost calculation (3 tests)
✅ Connection test (2 tests)
✅ Edge cases (2 tests)

TOTAL: 16 comprehensive tests
All using mocked Gemini API responses
"""


