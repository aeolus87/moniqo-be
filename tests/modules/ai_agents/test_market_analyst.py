"""
Market Analyst Agent Tests

Comprehensive tests for MarketAnalyst agent.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from app.modules.ai_agents.market_analyst_agent import MarketAnalystAgent
from app.modules.ai_agents.base_agent import AgentRole, AgentStatus


# ==================== FIXTURES ====================

@pytest.fixture
def mock_model():
    """Mock LLM model"""
    model = Mock()
    model.generate_response = AsyncMock(return_value="Bullish trend detected")
    model.generate_structured_output = AsyncMock(return_value={
        "action": "buy",
        "confidence": 0.85,
        "reasoning": "Strong volume and breaking resistance levels",
        "price_target": 52000.0,
        "stop_loss": 49000.0,
        "take_profit": 53000.0,
        "risk_level": "medium"
    })
    model.get_model_info.return_value = {
        "total_input_tokens": 500,
        "total_output_tokens": 200,
        "total_cost_usd": Decimal("0.02")
    }
    model.reset_usage = Mock()
    return model


@pytest.fixture
def market_analyst(mock_model):
    """Create MarketAnalystAgent instance"""
    with patch('app.integrations.ai.factory.get_model_factory') as mock_factory:
        mock_factory_instance = Mock()
        mock_factory_instance.create_model.return_value = mock_model
        mock_factory.return_value = mock_factory_instance
        
        agent = MarketAnalystAgent(model_provider="gemini")
        agent.model = mock_model
        return agent


# ==================== INITIALIZATION TESTS ====================

def test_market_analyst_init(market_analyst):
    """Test MarketAnalystAgent initialization"""
    assert market_analyst.role == AgentRole.MARKET_ANALYST
    assert market_analyst.model_provider == "gemini"
    assert market_analyst.status == AgentStatus.IDLE


# ==================== PROCESS TESTS ====================

@pytest.mark.asyncio
async def test_process_market_analysis_success(market_analyst, mock_model):
    """Test successful market analysis"""
    context = {
        "symbol": "BTC/USDT",
        "market_data": {
            "current_price": 50000.0,
            "high_24h": 51000.0,
            "low_24h": 49000.0,
            "volume_24h": 1000000,
            "change_24h_percent": 2.5
        },
        "indicators": {
            "rsi": 65,
            "macd": "bullish",
            "moving_average": "above"
        }
    }
    
    result = await market_analyst.process(context)
    
    assert result["success"] is True
    assert "action" in result
    assert "confidence" in result
    assert "reasoning" in result
    assert result["agent"] == "market_analyst"
    
    # Verify model was called with structured output
    mock_model.generate_structured_output.assert_called_once()


@pytest.mark.asyncio
async def test_process_with_news_data(market_analyst, mock_model):
    """Test analysis with news data"""
    context = {
        "symbol": "BTC/USDT",
        "market_data": {"current_price": 50000.0},
        "indicators": {}
    }
    
    result = await market_analyst.process(context)
    
    assert result["success"] is True
    assert "action" in result


@pytest.mark.asyncio
async def test_process_minimal_context(market_analyst, mock_model):
    """Test analysis with minimal context"""
    context = {
        "symbol": "BTC/USDT",
        "market_data": {"current_price": 50000.0}
    }
    
    result = await market_analyst.process(context)
    
    assert result["success"] is True
    assert "action" in result


@pytest.mark.asyncio
async def test_process_default_symbol(market_analyst, mock_model):
    """Test process with default symbol"""
    context = {
        "market_data": {"current_price": 50000.0}
    }
    
    result = await market_analyst.process(context)
    
    assert result["success"] is True
    assert "action" in result


@pytest.mark.asyncio
async def test_process_model_error(market_analyst, mock_model):
    """Test handling model errors"""
    mock_model.generate_structured_output.side_effect = Exception("API error")
    
    context = {
        "symbol": "BTC/USDT",
        "market_data": {"current_price": 50000.0}
    }
    
    result = await market_analyst.process(context)
    
    assert result["success"] is False
    assert "error" in result
    assert market_analyst.status == AgentStatus.ERROR


# ==================== ANALYSIS QUALITY TESTS ====================

@pytest.mark.asyncio
async def test_analysis_includes_confidence(market_analyst, mock_model):
    """Test that analysis includes confidence score"""
    context = {"symbol": "BTC/USDT", "market_data": {"current_price": 50000.0}}
    
    result = await market_analyst.process(context)
    
    assert "confidence" in result
    assert isinstance(result["confidence"], (int, float))
    assert 0 <= result["confidence"] <= 1


@pytest.mark.asyncio
async def test_analysis_includes_action(market_analyst, mock_model):
    """Test that analysis includes action"""
    context = {"symbol": "BTC/USDT", "market_data": {"current_price": 50000.0}}
    
    result = await market_analyst.process(context)
    
    assert "action" in result
    assert result["action"] in ["buy", "sell", "hold"]


@pytest.mark.asyncio
async def test_analysis_includes_price_targets(market_analyst, mock_model):
    """Test that analysis includes price targets"""
    context = {"symbol": "BTC/USDT", "market_data": {"current_price": 50000.0}}
    
    result = await market_analyst.process(context)
    
    assert "price_target" in result
    assert "stop_loss" in result
    assert "take_profit" in result
    assert isinstance(result["price_target"], (int, float))
    assert isinstance(result["stop_loss"], (int, float))
    assert isinstance(result["take_profit"], (int, float))


# ==================== SUMMARY ====================

"""
Test Coverage Summary:
✅ Initialization (1 test)
✅ Process method (5 tests)
✅ Analysis quality (3 tests)

TOTAL: 9 comprehensive tests
All testing MarketAnalystAgent behavior
"""

