"""
AI Agents API Router

Endpoints for AI agent operations (market analysis, etc.)

Author: Moniqo Team
Last Updated: 2025-01-17
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.modules.ai_agents.market_analyst_agent import MarketAnalystAgent
from app.modules.ai_agents.risk_manager_agent import RiskManagerAgent
from app.modules.ai_agents.executor_agent import ExecutorAgent
from app.modules.ai_agents.monitor_agent import MonitorAgent
from app.integrations.ai.factory import get_model_factory
from app.utils.logger import get_logger
import os

logger = get_logger(__name__)

router = APIRouter(prefix="/ai-agents", tags=["AI Agents"])


# ============ Request/Response Models ============

class MarketAnalysisRequest(BaseModel):
    """Request model for market analysis"""
    model_config = ConfigDict(protected_namespaces=())

    symbol: str = Field(default="BTC/USDT", description="Trading pair symbol")
    current_price: Optional[float] = Field(default=None, description="Current price")
    high_24h: Optional[float] = Field(default=None, description="24h high")
    low_24h: Optional[float] = Field(default=None, description="24h low")
    volume_24h: Optional[float] = Field(default=None, description="24h volume")
    change_24h_percent: Optional[float] = Field(default=None, description="24h change %")
    indicators: Optional[Dict[str, Any]] = Field(default=None, description="Technical indicators")
    model_provider: str = Field(default="groq", description="AI model provider (groq, openrouter, gemini)")


class MarketAnalysisResponse(BaseModel):
    """Response model for market analysis"""
    success: bool
    agent: str
    timestamp: datetime
    action: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_level: Optional[str] = None
    error: Optional[str] = None


class TestConnectionRequest(BaseModel):
    """Request model for connection test"""
    provider: str = Field(default="groq", description="AI provider to test")


class TestConnectionResponse(BaseModel):
    """Response model for connection test"""
    success: bool
    provider: str
    model_name: str
    latency_ms: Optional[int] = None
    response: Optional[str] = None
    message: str
    error: Optional[str] = None


class AvailableProvidersResponse(BaseModel):
    """Response model for available providers"""
    providers: List[str]
    default_provider: str
    default_model: str


# ============ Endpoints ============

@router.get("/providers", response_model=AvailableProvidersResponse)
async def get_available_providers():
    """Get list of available AI providers"""
    factory = get_model_factory()
    providers = factory.get_available_providers()
    
    return AvailableProvidersResponse(
        providers=providers,
        default_provider=os.getenv("AI_DEFAULT_PROVIDER", "groq"),
        default_model=os.getenv("AI_DEFAULT_MODEL", "llama-3.3-70b-versatile")
    )


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_ai_connection(request: TestConnectionRequest):
    """Test connection to AI provider"""
    try:
        factory = get_model_factory()
        
        # Get API key based on provider
        api_key_env = {
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY"
        }
        
        api_key = os.getenv(api_key_env.get(request.provider.lower(), ""), "")
        
        if not api_key:
            return TestConnectionResponse(
                success=False,
                provider=request.provider,
                model_name="",
                message=f"No API key configured for {request.provider}",
                error=f"Set {api_key_env.get(request.provider.lower(), 'API_KEY')} environment variable"
            )
        
        # Create model and test
        model = factory.create_model(
            provider=request.provider,
            api_key=api_key
        )
        
        result = await model.test_connection()
        
        return TestConnectionResponse(
            success=result["success"],
            provider=result.get("provider", request.provider),
            model_name=result.get("model_name", ""),
            latency_ms=result.get("latency_ms"),
            response=result.get("response"),
            message=result.get("message", "Connection successful")
        )
    
    except Exception as e:
        logger.error(f"AI connection test failed: {str(e)}")
        return TestConnectionResponse(
            success=False,
            provider=request.provider,
            model_name="",
            message="Connection test failed",
            error=str(e)
        )


@router.post("/analyze-market", response_model=MarketAnalysisResponse)
async def analyze_market(request: MarketAnalysisRequest):
    """
    Analyze market conditions and get trading recommendation.

    Uses AI agent to analyze market data and provide:
    - Trading action (buy/sell/hold)
    - Confidence score
    - Reasoning
    - Price targets (entry, stop-loss, take-profit)
    """
    try:
        # Build market data context
        market_data = {}
        if request.current_price:
            market_data["current_price"] = request.current_price
        if request.high_24h:
            market_data["high_24h"] = request.high_24h
        if request.low_24h:
            market_data["low_24h"] = request.low_24h
        if request.volume_24h:
            market_data["volume_24h"] = request.volume_24h
        if request.change_24h_percent:
            market_data["change_24h_percent"] = request.change_24h_percent

        # Create market analyst agent
        agent = MarketAnalystAgent(
            model_provider=request.model_provider
        )

        # Run analysis
        result = await agent.process({
            "symbol": request.symbol,
            "market_data": market_data,
            "indicators": request.indicators or {}
        })

        return MarketAnalysisResponse(
            success=result.get("success", False),
            agent=result.get("agent", "market_analyst"),
            timestamp=result.get("timestamp", datetime.now(timezone.utc)),
            action=result.get("action"),
            confidence=result.get("confidence"),
            reasoning=result.get("reasoning"),
            price_target=result.get("price_target"),
            stop_loss=result.get("stop_loss"),
            take_profit=result.get("take_profit"),
            risk_level=result.get("risk_level"),
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Market analysis failed: {str(e)}")
        return MarketAnalysisResponse(
            success=False,
            agent="market_analyst",
            timestamp=datetime.now(timezone.utc),
            error=str(e)
        )


@router.get("/prompts")
async def get_ai_agent_prompts():
    """
    Get AI agent prompts and configurations.

    Returns detailed information about each AI agent including:
    - System prompts
    - Capabilities
    - Role descriptions
    """
    agents_data = []

    # Market Analyst
    try:
        market_agent = MarketAnalystAgent.__new__(MarketAnalystAgent)
        system_prompt = market_agent._get_system_prompt()
        agents_data.append({
            "role": "market_analyst",
            "name": "Market Analyst Agent",
            "description": "Analyzes market conditions and generates trading signals",
            "system_prompt": system_prompt,
            "capabilities": [
                "Analyze market trends",
                "Evaluate technical indicators",
                "Assess market sentiment",
                "Generate buy/sell/hold signals"
            ]
        })
    except Exception as e:
        logger.warning(f"Could not load market analyst prompts: {str(e)}")

    # Risk Manager
    try:
        risk_agent = RiskManagerAgent.__new__(RiskManagerAgent)
        system_prompt = risk_agent._get_system_prompt()
        agents_data.append({
            "role": "risk_manager",
            "name": "Risk Manager Agent",
            "description": "Validates trading decisions and manages risk limits",
            "system_prompt": system_prompt,
            "capabilities": [
                "Validate order requests against risk limits",
                "Check position sizes",
                "Monitor daily loss limits",
                "Approve or reject trades"
            ]
        })
    except Exception as e:
        logger.warning(f"Could not load risk manager prompts: {str(e)}")

    # Executor
    try:
        executor_agent = ExecutorAgent.__new__(ExecutorAgent)
        agents_data.append({
            "role": "executor",
            "name": "Executor Agent",
            "description": "Executes approved trading decisions",
            "system_prompt": "You are an order execution coordinator. Your role is to validate execution logic and coordinate with the trading platform to place orders safely and efficiently.",
            "capabilities": [
                "Execute buy/sell orders",
                "Monitor order execution",
                "Handle partial fills",
                "Update positions"
            ]
        })
    except Exception as e:
        logger.warning(f"Could not load executor prompts: {str(e)}")

    # Monitor
    try:
        monitor_agent = MonitorAgent.__new__(MonitorAgent)
        agents_data.append({
            "role": "monitor",
            "name": "Monitor Agent",
            "description": "Monitors positions and market conditions",
            "system_prompt": "You are a position monitoring specialist. Your role is to continuously monitor open positions, track P&L, detect exit conditions, and recommend position adjustments.",
            "capabilities": [
                "Monitor open positions",
                "Track P&L changes",
                "Detect exit conditions",
                "Recommend adjustments"
            ]
        })
    except Exception as e:
        logger.warning(f"Could not load monitor prompts: {str(e)}")

    return {
        "agents": agents_data,
        "total": len(agents_data)
    }


@router.get("/health")
async def health_check():
    """Health check for AI agents module"""
    groq_key = os.getenv("GROQ_API_KEY", "")
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    
    return {
        "status": "healthy",
        "providers": {
            "groq": "configured" if groq_key else "not configured",
            "openrouter": "configured" if openrouter_key else "not configured",
            "gemini": "configured" if gemini_key else "not configured"
        },
        "default_provider": os.getenv("AI_DEFAULT_PROVIDER", "groq"),
        "timestamp": datetime.now(timezone.utc)
    }
