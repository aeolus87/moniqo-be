"""
Executor Agent Tests

Comprehensive tests for ExecutorAgent.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from app.modules.ai_agents.executor_agent import ExecutorAgent
from app.modules.ai_agents.base_agent import AgentRole, AgentStatus


# ==================== FIXTURES ====================

@pytest.fixture
def mock_model():
    """Mock LLM model"""
    model = Mock()
    model.generate_response = AsyncMock(return_value="Execution plan created")
    model.generate_structured_output = AsyncMock(return_value={
        "execution_plan": "validated",
        "estimated_slippage": 0.001
    })
    model.get_model_info.return_value = {
        "total_input_tokens": 200,
        "total_output_tokens": 100,
        "total_cost_usd": Decimal("0.01")
    }
    model.reset_usage = Mock()
    return model


@pytest.fixture
def executor_agent(mock_model):
    """Create ExecutorAgent instance"""
    with patch('app.integrations.ai.factory.get_model_factory') as mock_factory:
        mock_factory_instance = Mock()
        mock_factory_instance.create_model.return_value = mock_model
        mock_factory.return_value = mock_factory_instance
        
        agent = ExecutorAgent(model_provider="gemini")
        agent.model = mock_model
        return agent


# ==================== INITIALIZATION TESTS ====================

def test_executor_agent_init(executor_agent):
    """Test ExecutorAgent initialization"""
    assert executor_agent.role == AgentRole.EXECUTOR
    assert executor_agent.model_provider == "gemini"
    assert executor_agent.status == AgentStatus.IDLE


# ==================== PROCESS TESTS ====================

@pytest.mark.asyncio
async def test_process_order_execution_success(executor_agent, mock_model):
    """Test successful order execution planning"""
    context = {
        "approved_order": {
            "order_id": "order123",
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.1,
            "price": 50000.0,
            "type": "LIMIT"
        },
        "wallet_id": "wallet123"
    }
    
    result = await executor_agent.process(context)
    
    assert result["success"] is True
    assert result["agent"] == "executor"
    assert result["order_id"] == "order123"
    assert result["status"] == "pending_execution"
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_process_with_market_order(executor_agent, mock_model):
    """Test execution planning for market order"""
    context = {
        "approved_order": {
            "order_id": "order456",
            "symbol": "ETH/USDT",
            "side": "SELL",
            "quantity": 1.0,
            "type": "MARKET"
        },
        "wallet_id": "wallet123"
    }
    
    result = await executor_agent.process(context)
    
    assert result["success"] is True
    assert result["order_id"] == "order456"
    assert result["status"] == "pending_execution"


@pytest.mark.asyncio
async def test_process_with_limit_order(executor_agent, mock_model):
    """Test execution planning for limit order"""
    context = {
        "approved_order": {
            "order_id": "order789",
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.5,
            "price": 49000.0,
            "type": "LIMIT"
        },
        "wallet_id": "wallet123"
    }
    
    result = await executor_agent.process(context)
    
    assert result["success"] is True
    assert result["order_id"] == "order789"


@pytest.mark.asyncio
async def test_process_with_stop_loss_order(executor_agent, mock_model):
    """Test execution planning for stop loss order"""
    context = {
        "approved_order": {
            "order_id": "order_stop",
            "symbol": "BTC/USDT",
            "side": "SELL",
            "quantity": 0.1,
            "stop_price": 48000.0,
            "type": "STOP_LOSS"
        },
        "wallet_id": "wallet123"
    }
    
    result = await executor_agent.process(context)
    
    assert result["success"] is True
    assert result["order_id"] == "order_stop"


@pytest.mark.asyncio
async def test_process_missing_approved_order(executor_agent):
    """Test process with missing approved order"""
    context = {
        "wallet_id": "wallet123"
        # Missing approved_order
    }
    
    result = await executor_agent.process(context)
    
    # Should still succeed but with empty order_id
    assert result["success"] is True
    assert result["order_id"] == ""


@pytest.mark.asyncio
async def test_process_missing_wallet_id(executor_agent, mock_model):
    """Test process with missing wallet_id"""
    context = {
        "approved_order": {
            "order_id": "order123",
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.1
        }
        # Missing wallet_id
    }
    
    result = await executor_agent.process(context)
    
    assert result["success"] is True
    assert result["order_id"] == "order123"


@pytest.mark.asyncio
async def test_process_error_handling(executor_agent):
    """Test error handling during process"""
    # Simulate an error by making context invalid
    context = None
    
    result = await executor_agent.process(context)
    
    assert result["success"] is False
    assert "error" in result
    assert executor_agent.status == AgentStatus.ERROR


@pytest.mark.asyncio
async def test_process_status_changes(executor_agent, mock_model):
    """Test status changes during execution"""
    assert executor_agent.status == AgentStatus.IDLE
    
    context = {
        "approved_order": {
            "order_id": "order123",
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.1
        },
        "wallet_id": "wallet123"
    }
    
    result = await executor_agent.process(context)
    
    # Status should be COMPLETED after successful execution
    assert executor_agent.status == AgentStatus.COMPLETED
    assert result["success"] is True


# ==================== EXECUTION VALIDATION TESTS ====================

@pytest.mark.asyncio
async def test_execution_includes_timestamp(executor_agent, mock_model):
    """Test that execution result includes timestamp"""
    context = {
        "approved_order": {
            "order_id": "order123",
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.1
        },
        "wallet_id": "wallet123"
    }
    
    result = await executor_agent.process(context)
    
    assert "timestamp" in result
    assert result["timestamp"] is not None


@pytest.mark.asyncio
async def test_execution_includes_message(executor_agent, mock_model):
    """Test that execution result includes message"""
    context = {
        "approved_order": {
            "order_id": "order123",
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.1
        },
        "wallet_id": "wallet123"
    }
    
    result = await executor_agent.process(context)
    
    assert "message" in result
    assert "queued" in result["message"].lower() or "execution" in result["message"].lower()


# ==================== SUMMARY ====================

"""
Test Coverage Summary:
✅ Initialization (1 test)
✅ Process method (7 tests)
✅ Execution validation (2 tests)

TOTAL: 10 comprehensive tests
All testing ExecutorAgent behavior
"""


