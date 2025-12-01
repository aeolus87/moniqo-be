"""
Risk Manager Agent Tests

Comprehensive tests for RiskManager agent.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from app.modules.ai_agents.risk_manager_agent import RiskManagerAgent
from app.modules.ai_agents.base_agent import AgentRole, AgentStatus


# ==================== FIXTURES ====================

@pytest.fixture
def mock_model():
    """Mock LLM model"""
    model = Mock()
    model.generate_response = AsyncMock(return_value="Risk assessment complete")
    model.generate_structured_output = AsyncMock(return_value={
        "approved": True,
        "risk_score": 0.3,
        "recommended_position_size": 1000.0,
        "stop_loss_price": 49500.0,
        "take_profit_price": 51500.0,
        "warnings": [],
        "reasons": ["Within risk limits", "Good entry point"]
    })
    model.get_model_info.return_value = {
        "total_input_tokens": 300,
        "total_output_tokens": 150,
        "total_cost_usd": Decimal("0.015")
    }
    model.reset_usage = Mock()
    return model


@pytest.fixture
def risk_manager(mock_model):
    """Create RiskManagerAgent instance"""
    with patch('app.integrations.ai.factory.get_model_factory') as mock_factory:
        mock_factory_instance = Mock()
        mock_factory_instance.create_model.return_value = mock_model
        mock_factory.return_value = mock_factory_instance
        
        agent = RiskManagerAgent(model_provider="gemini")
        agent.model = mock_model
        return agent


# ==================== INITIALIZATION TESTS ====================

def test_risk_manager_init(risk_manager):
    """Test RiskManagerAgent initialization"""
    assert risk_manager.role == AgentRole.RISK_MANAGER
    assert risk_manager.model_provider == "gemini"
    assert risk_manager.status == AgentStatus.IDLE


# ==================== PROCESS TESTS ====================

@pytest.mark.asyncio
async def test_process_pre_trade_validation_success(risk_manager, mock_model):
    """Test successful pre-trade validation"""
    context = {
        "user_wallet_id": "wallet123",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.1,
        "entry_price": 50000.0,
        "current_balance": {"USDT": 10000.0},
        "existing_positions": [],
        "risk_limits": {
            "max_position_size_usd": 5000.0,
            "daily_loss_limit": 500.0,
            "stop_loss_default_percent": 0.02
        }
    }
    
    result = await risk_manager.process(context)
    
    assert result["success"] is True
    assert result["approved"] is True
    assert "risk_score" in result
    assert "recommended_position_size" in result
    assert result["role"] == "risk_manager"
    
    # Verify model was called
    mock_model.generate_structured_output.assert_called_once()


@pytest.mark.asyncio
async def test_process_trade_rejected_high_risk(risk_manager, mock_model):
    """Test trade rejection due to high risk"""
    mock_model.generate_structured_output.return_value = {
        "approved": False,
        "risk_score": 0.9,
        "recommended_position_size": 0.0,
        "warnings": ["Position size too large", "Exceeds daily loss limit"],
        "reasons": ["Risk score too high"]
    }
    
    context = {
        "user_wallet_id": "wallet123",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 10.0,  # Too large
        "entry_price": 50000.0,
        "current_balance": {"USDT": 10000.0},
        "risk_limits": {
            "max_position_size_usd": 5000.0
        }
    }
    
    result = await risk_manager.process(context)
    
    assert result["success"] is True
    assert result["approved"] is False
    assert len(result["warnings"]) > 0


@pytest.mark.asyncio
async def test_process_position_size_override(risk_manager, mock_model):
    """Test recommended position size override"""
    mock_model.generate_structured_output.return_value = {
        "approved": True,
        "risk_score": 0.5,
        "recommended_position_size": 500.0,  # Smaller than requested
        "reasons": ["Reduce size for better risk/reward"]
    }
    
    context = {
        "user_wallet_id": "wallet123",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 1.0,  # Requested
        "entry_price": 50000.0,
        "current_balance": {"USDT": 10000.0},
        "risk_limits": {}
    }
    
    result = await risk_manager.process(context)
    
    assert result["approved"] is True
    assert result["recommended_position_size"] < 50000.0  # Less than requested


@pytest.mark.asyncio
async def test_process_stop_loss_take_profit_suggestion(risk_manager, mock_model):
    """Test stop loss and take profit suggestions"""
    context = {
        "user_wallet_id": "wallet123",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.1,
        "entry_price": 50000.0,
        "risk_limits": {
            "stop_loss_default_percent": 0.02
        }
    }
    
    result = await risk_manager.process(context)
    
    assert "stop_loss_price" in result or "stop_loss_percent" in result
    assert "take_profit_price" in result or "take_profit_percent" in result


@pytest.mark.asyncio
async def test_process_correlation_check(risk_manager, mock_model):
    """Test correlation limit checking"""
    context = {
        "user_wallet_id": "wallet123",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.1,
        "entry_price": 50000.0,
        "existing_positions": [
            {"symbol": "BTC/USDT", "side": "LONG", "size_usd": 2000.0},
            {"symbol": "ETH/USDT", "side": "LONG", "size_usd": 1000.0}
        ],
        "risk_limits": {
            "max_correlation_exposure": 0.8
        }
    }
    
    result = await risk_manager.process(context)
    
    # Should consider existing positions
    call_args = mock_model.generate_structured_output.call_args
    prompt = call_args[1]["prompt"]
    assert "existing_positions" in prompt.lower() or "correlation" in prompt.lower()


@pytest.mark.asyncio
async def test_process_daily_loss_limit_check(risk_manager, mock_model):
    """Test daily loss limit checking"""
    context = {
        "user_wallet_id": "wallet123",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.1,
        "entry_price": 50000.0,
        "daily_pnl": -400.0,  # Already lost $400 today
        "risk_limits": {
            "daily_loss_limit": 500.0
        }
    }
    
    result = await risk_manager.process(context)
    
    # Should consider daily P&L
    call_args = mock_model.generate_structured_output.call_args
    prompt = call_args[1]["prompt"]
    assert "daily" in prompt.lower() or "loss" in prompt.lower()


@pytest.mark.asyncio
async def test_process_missing_required_fields(risk_manager):
    """Test process with missing required fields"""
    context = {
        # Missing user_wallet_id, symbol, side
        "quantity": 0.1
    }
    
    result = await risk_manager.process(context)
    
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_process_model_error(risk_manager, mock_model):
    """Test handling model errors"""
    mock_model.generate_structured_output.side_effect = Exception("API error")
    
    context = {
        "user_wallet_id": "wallet123",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.1
    }
    
    result = await risk_manager.process(context)
    
    assert result["success"] is False
    assert "error" in result
    assert risk_manager.status == AgentStatus.ERROR


# ==================== RISK CALCULATION TESTS ====================

@pytest.mark.asyncio
async def test_risk_score_calculation(risk_manager, mock_model):
    """Test risk score calculation"""
    context = {
        "user_wallet_id": "wallet123",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.1,
        "entry_price": 50000.0
    }
    
    result = await risk_manager.process(context)
    
    assert "risk_score" in result
    assert isinstance(result["risk_score"], (int, float))
    assert 0 <= result["risk_score"] <= 1


@pytest.mark.asyncio
async def test_warnings_generated(risk_manager, mock_model):
    """Test that warnings are generated when needed"""
    mock_model.generate_structured_output.return_value = {
        "approved": True,
        "risk_score": 0.6,
        "recommended_position_size": 800.0,
        "warnings": ["High volatility detected", "Consider reducing size"],
        "reasons": ["Risk score elevated"]
    }
    
    context = {
        "user_wallet_id": "wallet123",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.1,
        "entry_price": 50000.0
    }
    
    result = await risk_manager.process(context)
    
    assert "warnings" in result
    assert len(result["warnings"]) > 0
    assert isinstance(result["warnings"], list)


# ==================== SUMMARY ====================

"""
Test Coverage Summary:
✅ Initialization (1 test)
✅ Process method (7 tests)
✅ Risk calculation (2 tests)

TOTAL: 10 comprehensive tests
All testing RiskManager behavior
"""

