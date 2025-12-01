"""
Monitor Agent Tests

Comprehensive tests for MonitorAgent.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from app.modules.ai_agents.monitor_agent import MonitorAgent
from app.modules.ai_agents.base_agent import AgentRole, AgentStatus


# ==================== FIXTURES ====================

@pytest.fixture
def mock_model():
    """Mock LLM model"""
    model = Mock()
    model.generate_response = AsyncMock(return_value="Monitoring complete")
    model.generate_structured_output = AsyncMock(return_value={
        "positions_checked": 2,
        "alerts": [
            {
                "position_id": "pos123",
                "alert_type": "stop_loss_approaching",
                "message": "Stop loss level approaching",
                "urgency": "medium"
            }
        ],
        "recommendations": [
            {
                "position_id": "pos123",
                "action": "reduce_size",
                "reason": "High volatility detected"
            }
        ],
        "risk_breaches": []
    })
    model.get_model_info.return_value = {
        "total_input_tokens": 400,
        "total_output_tokens": 200,
        "total_cost_usd": Decimal("0.02")
    }
    model.reset_usage = Mock()
    return model


@pytest.fixture
def monitor_agent(mock_model):
    """Create MonitorAgent instance"""
    with patch('app.integrations.ai.factory.get_model_factory') as mock_factory:
        mock_factory_instance = Mock()
        mock_factory_instance.create_model.return_value = mock_model
        mock_factory.return_value = mock_factory_instance
        
        agent = MonitorAgent(model_provider="gemini")
        agent.model = mock_model
        return agent


# ==================== INITIALIZATION TESTS ====================

def test_monitor_agent_init(monitor_agent):
    """Test MonitorAgent initialization"""
    assert monitor_agent.role == AgentRole.MONITOR
    assert monitor_agent.model_provider == "gemini"
    assert monitor_agent.status == AgentStatus.IDLE


# ==================== PROCESS TESTS ====================

@pytest.mark.asyncio
async def test_process_position_monitoring_success(monitor_agent, mock_model):
    """Test successful position monitoring"""
    context = {
        "positions": [
            {
                "position_id": "pos123",
                "symbol": "BTC/USDT",
                "side": "LONG",
                "entry_price": 50000.0,
                "current_price": 51000.0,
                "quantity": 0.1,
                "unrealized_pnl": 100.0
            },
            {
                "position_id": "pos456",
                "symbol": "ETH/USDT",
                "side": "SHORT",
                "entry_price": 3000.0,
                "current_price": 2900.0,
                "quantity": 1.0,
                "unrealized_pnl": 100.0
            }
        ],
        "market_data": {
            "BTC/USDT": {"price": 51000.0, "volatility": 0.02},
            "ETH/USDT": {"price": 2900.0, "volatility": 0.015}
        }
    }
    
    result = await monitor_agent.process(context)
    
    assert result["success"] is True
    assert result["agent"] == "monitor"
    assert result["positions_checked"] == 2
    assert "alerts" in result
    assert "recommendations" in result
    assert "risk_breaches" in result
    
    # Verify model was called with structured output
    mock_model.generate_structured_output.assert_called_once()


@pytest.mark.asyncio
async def test_process_with_empty_positions(monitor_agent, mock_model):
    """Test monitoring with no positions"""
    mock_model.generate_structured_output.return_value = {
        "positions_checked": 0,
        "alerts": [],
        "recommendations": [],
        "risk_breaches": []
    }
    
    context = {
        "positions": [],
        "market_data": {}
    }
    
    result = await monitor_agent.process(context)
    
    assert result["success"] is True
    assert result["positions_checked"] == 0
    assert len(result["alerts"]) == 0


@pytest.mark.asyncio
async def test_process_with_risk_breaches(monitor_agent, mock_model):
    """Test monitoring with risk breaches detected"""
    mock_model.generate_structured_output.return_value = {
        "positions_checked": 1,
        "alerts": [
            {
                "position_id": "pos123",
                "alert_type": "risk_limit_breached",
                "message": "Daily loss limit exceeded",
                "urgency": "high"
            }
        ],
        "recommendations": [
            {
                "position_id": "pos123",
                "action": "close_immediately",
                "reason": "Risk limit breached"
            }
        ],
        "risk_breaches": [
            {
                "position_id": "pos123",
                "breach_type": "daily_loss_limit",
                "current_value": -600.0,
                "limit": -500.0
            }
        ]
    }
    
    context = {
        "positions": [
            {
                "position_id": "pos123",
                "symbol": "BTC/USDT",
                "unrealized_pnl": -600.0
            }
        ],
        "market_data": {}
    }
    
    result = await monitor_agent.process(context)
    
    assert result["success"] is True
    assert len(result["risk_breaches"]) > 0
    assert result["risk_breaches"][0]["breach_type"] == "daily_loss_limit"


@pytest.mark.asyncio
async def test_process_with_stop_loss_alerts(monitor_agent, mock_model):
    """Test monitoring with stop loss alerts"""
    mock_model.generate_structured_output.return_value = {
        "positions_checked": 1,
        "alerts": [
            {
                "position_id": "pos123",
                "alert_type": "stop_loss_triggered",
                "message": "Stop loss price reached",
                "urgency": "high"
            }
        ],
        "recommendations": [
            {
                "position_id": "pos123",
                "action": "close_position",
                "reason": "Stop loss triggered"
            }
        ],
        "risk_breaches": []
    }
    
    context = {
        "positions": [
            {
                "position_id": "pos123",
                "symbol": "BTC/USDT",
                "entry_price": 50000.0,
                "current_price": 49000.0,
                "stop_loss_price": 49500.0
            }
        ],
        "market_data": {
            "BTC/USDT": {"price": 49000.0}
        }
    }
    
    result = await monitor_agent.process(context)
    
    assert result["success"] is True
    assert len(result["alerts"]) > 0
    assert any("stop_loss" in alert["alert_type"] for alert in result["alerts"])


@pytest.mark.asyncio
async def test_process_with_take_profit_alerts(monitor_agent, mock_model):
    """Test monitoring with take profit alerts"""
    mock_model.generate_structured_output.return_value = {
        "positions_checked": 1,
        "alerts": [
            {
                "position_id": "pos123",
                "alert_type": "take_profit_approaching",
                "message": "Take profit target near",
                "urgency": "low"
            }
        ],
        "recommendations": [
            {
                "position_id": "pos123",
                "action": "partial_close",
                "reason": "Take profit target approaching"
            }
        ],
        "risk_breaches": []
    }
    
    context = {
        "positions": [
            {
                "position_id": "pos123",
                "symbol": "BTC/USDT",
                "entry_price": 50000.0,
                "current_price": 51900.0,
                "take_profit_price": 52000.0
            }
        ],
        "market_data": {
            "BTC/USDT": {"price": 51900.0}
        }
    }
    
    result = await monitor_agent.process(context)
    
    assert result["success"] is True
    assert len(result["alerts"]) > 0


@pytest.mark.asyncio
async def test_process_minimal_context(monitor_agent, mock_model):
    """Test monitoring with minimal context"""
    context = {
        "positions": [
            {
                "position_id": "pos123",
                "symbol": "BTC/USDT"
            }
        ]
    }
    
    result = await monitor_agent.process(context)
    
    assert result["success"] is True
    assert "positions_checked" in result


@pytest.mark.asyncio
async def test_process_missing_positions(monitor_agent, mock_model):
    """Test monitoring with missing positions"""
    context = {
        "market_data": {
            "BTC/USDT": {"price": 50000.0}
        }
    }
    
    result = await monitor_agent.process(context)
    
    assert result["success"] is True
    assert result["positions_checked"] == 0


@pytest.mark.asyncio
async def test_process_model_error(monitor_agent, mock_model):
    """Test handling model errors"""
    mock_model.generate_structured_output.side_effect = Exception("API error")
    
    context = {
        "positions": [
            {
                "position_id": "pos123",
                "symbol": "BTC/USDT"
            }
        ],
        "market_data": {}
    }
    
    result = await monitor_agent.process(context)
    
    assert result["success"] is False
    assert "error" in result
    assert monitor_agent.status == AgentStatus.ERROR


# ==================== MONITORING QUALITY TESTS ====================

@pytest.mark.asyncio
async def test_monitoring_includes_alerts(monitor_agent, mock_model):
    """Test that monitoring includes alerts array"""
    context = {
        "positions": [
            {
                "position_id": "pos123",
                "symbol": "BTC/USDT"
            }
        ],
        "market_data": {}
    }
    
    result = await monitor_agent.process(context)
    
    assert "alerts" in result
    assert isinstance(result["alerts"], list)


@pytest.mark.asyncio
async def test_monitoring_includes_recommendations(monitor_agent, mock_model):
    """Test that monitoring includes recommendations"""
    context = {
        "positions": [
            {
                "position_id": "pos123",
                "symbol": "BTC/USDT"
            }
        ],
        "market_data": {}
    }
    
    result = await monitor_agent.process(context)
    
    assert "recommendations" in result
    assert isinstance(result["recommendations"], list)


@pytest.mark.asyncio
async def test_monitoring_includes_risk_breaches(monitor_agent, mock_model):
    """Test that monitoring includes risk breaches"""
    context = {
        "positions": [
            {
                "position_id": "pos123",
                "symbol": "BTC/USDT"
            }
        ],
        "market_data": {}
    }
    
    result = await monitor_agent.process(context)
    
    assert "risk_breaches" in result
    assert isinstance(result["risk_breaches"], list)


@pytest.mark.asyncio
async def test_monitoring_status_changes(monitor_agent, mock_model):
    """Test status changes during monitoring"""
    assert monitor_agent.status == AgentStatus.IDLE
    
    context = {
        "positions": [
            {
                "position_id": "pos123",
                "symbol": "BTC/USDT"
            }
        ],
        "market_data": {}
    }
    
    result = await monitor_agent.process(context)
    
    # Status should be COMPLETED after successful monitoring
    assert monitor_agent.status == AgentStatus.COMPLETED
    assert result["success"] is True


# ==================== SUMMARY ====================

"""
Test Coverage Summary:
✅ Initialization (1 test)
✅ Process method (8 tests)
✅ Monitoring quality (4 tests)

TOTAL: 13 comprehensive tests
All testing MonitorAgent behavior
"""


