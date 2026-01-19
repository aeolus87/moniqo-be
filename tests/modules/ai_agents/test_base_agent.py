"""
Base Agent Tests

Comprehensive tests for BaseAgent abstract class.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from app.modules.ai_agents.base_agent import (
    BaseAgent,
    AgentRole,
    AgentStatus
)
from app.integrations.ai.base import BaseLLM, ModelProvider


# ==================== FIXTURES ====================

@pytest.fixture
def mock_model():
    """Mock LLM model"""
    model = Mock(spec=BaseLLM)
    model.generate_response = AsyncMock(return_value="test response")
    model.generate_structured_output = AsyncMock(return_value={"key": "value"})
    model.get_model_info.return_value = {
        "total_input_tokens": 100,
        "total_output_tokens": 50,
        "total_cost_usd": Decimal("0.01")
    }
    model.reset_usage = Mock()
    return model


@pytest.fixture
def concrete_agent(mock_model):
    """Create concrete agent for testing"""
    class TestAgent(BaseAgent):
        async def process(self, context):
            return {"success": True, "result": "test"}
    
    with patch('app.integrations.ai.factory.get_model_factory') as mock_factory:
        mock_factory_instance = Mock()
        mock_factory_instance.create_model.return_value = mock_model
        mock_factory.return_value = mock_factory_instance
        
        agent = TestAgent(
            role=AgentRole.MARKET_ANALYST,
            model_provider="gemini"
        )
        
        # Replace with mock
        agent.model = mock_model
        return agent


# ==================== INITIALIZATION TESTS ====================

def test_base_agent_init(concrete_agent):
    """Test agent initialization"""
    assert concrete_agent.role == AgentRole.MARKET_ANALYST
    assert concrete_agent.model_provider == "gemini"
    assert concrete_agent.status == AgentStatus.IDLE


def test_base_agent_abstract_process():
    """Test that BaseAgent process is abstract"""
    # BaseAgent can't be instantiated directly
    with pytest.raises(TypeError):
        BaseAgent(
            role=AgentRole.MARKET_ANALYST,
            model_provider="gemini"
        )


# ==================== ANALYZE TESTS ====================

@pytest.mark.asyncio
async def test_analyze_text_response(concrete_agent, mock_model):
    """Test text analysis"""
    result = await concrete_agent.analyze(
        prompt="Test prompt",
        system_prompt="System instructions",
        temperature=0.7
    )
    
    assert result == "test response"
    assert concrete_agent.cost_tracking["total_requests"] == 1
    mock_model.generate_response.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_structured_output(concrete_agent, mock_model):
    """Test structured output analysis"""
    schema = {"type": "object"}
    
    result = await concrete_agent.analyze(
        prompt="Test prompt",
        system_prompt="System instructions",
        temperature=0.3,
        structured=True,
        schema=schema
    )
    
    assert result == {"key": "value"}
    mock_model.generate_structured_output.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_cost_tracking(concrete_agent, mock_model):
    """Test cost tracking during analysis"""
    initial_cost = concrete_agent.cost_tracking["total_cost_usd"]
    
    await concrete_agent.analyze(prompt="Test")
    
    # Cost should be tracked
    assert concrete_agent.cost_tracking["total_requests"] == 1
    # Cost will be updated based on model info


@pytest.mark.asyncio
async def test_analyze_status_change(concrete_agent, mock_model):
    """Test status changes during analysis"""
    assert concrete_agent.status == AgentStatus.IDLE
    
    await concrete_agent.analyze(prompt="Test")
    
    # Status should be back to IDLE after completion
    assert concrete_agent.status == AgentStatus.IDLE


@pytest.mark.asyncio
async def test_analyze_error_handling(concrete_agent, mock_model):
    """Test error handling during analysis"""
    mock_model.generate_response.side_effect = Exception("API error")
    
    with pytest.raises(Exception):
        await concrete_agent.analyze(prompt="Test")
    
    assert concrete_agent.status == AgentStatus.ERROR


# ==================== COST TRACKING TESTS ====================

def test_get_cost_summary(concrete_agent):
    """Test cost summary retrieval"""
    # Set some usage
    concrete_agent.cost_tracking["total_requests"] = 10
    concrete_agent.cost_tracking["total_input_tokens"] = 1000
    concrete_agent.cost_tracking["total_output_tokens"] = 500
    concrete_agent.cost_tracking["total_cost_usd"] = Decimal("0.10")
    
    summary = concrete_agent.get_cost_summary()
    
    assert summary["role"] == "market_analyst"
    assert summary["total_requests"] == 10
    assert summary["total_input_tokens"] == 1000
    assert summary["total_output_tokens"] == 500
    assert summary["total_cost_usd"] == 0.10
    assert summary["average_cost_per_request"] == 0.01


def test_get_cost_summary_zero_requests(concrete_agent):
    """Test cost summary with zero requests"""
    summary = concrete_agent.get_cost_summary()
    
    assert summary["total_requests"] == 0
    assert summary["average_cost_per_request"] == 0


def test_reset_cost_tracking(concrete_agent):
    """Test cost tracking reset"""
    # Set some usage
    concrete_agent.cost_tracking["total_requests"] = 10
    concrete_agent.cost_tracking["total_cost_usd"] = Decimal("0.10")
    
    concrete_agent.reset_cost_tracking()
    
    assert concrete_agent.cost_tracking["total_requests"] == 0
    assert concrete_agent.cost_tracking["total_cost_usd"] == Decimal("0")
    # Should also reset model usage
    concrete_agent.model.reset_usage.assert_called_once()


# ==================== STRING REPRESENTATION TESTS ====================

def test_agent_string_repr(concrete_agent):
    """Test string representation"""
    str_repr = str(concrete_agent)
    
    assert "market_analyst" in str_repr.lower()
    assert "gemini" in str_repr.lower()


def test_agent_repr(concrete_agent):
    """Test detailed representation"""
    concrete_agent.cost_tracking["total_cost_usd"] = Decimal("0.05")
    concrete_agent.status = AgentStatus.ANALYZING
    
    repr_str = repr(concrete_agent)
    
    assert "market_analyst" in repr_str.lower()
    assert "analyzing" in repr_str.lower()
    assert "0.05" in repr_str


# ==================== AGENT ROLE TESTS ====================

def test_agent_role_enum():
    """Test AgentRole enum values"""
    assert AgentRole.MARKET_ANALYST == "market_analyst"
    assert AgentRole.SENTIMENT_ANALYST == "sentiment_analyst"
    assert AgentRole.RISK_MANAGER == "risk_manager"
    assert AgentRole.EXECUTOR == "executor"
    assert AgentRole.MONITOR == "monitor"


def test_agent_status_enum():
    """Test AgentStatus enum values"""
    assert AgentStatus.IDLE == "idle"
    assert AgentStatus.ANALYZING == "analyzing"
    assert AgentStatus.DECIDING == "deciding"
    assert AgentStatus.EXECUTING == "executing"
    assert AgentStatus.ERROR == "error"
    assert AgentStatus.COMPLETED == "completed"


# ==================== SUMMARY ====================

"""
Test Coverage Summary:
✅ Initialization (2 tests)
✅ Analyze method (5 tests)
✅ Cost tracking (3 tests)
✅ String representation (2 tests)
✅ Enums (2 tests)

TOTAL: 14 comprehensive tests
All testing BaseAgent behavior
"""


