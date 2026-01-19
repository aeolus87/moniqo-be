"""
Base Agent - Abstract Base Class for AI Agents

Unified interface for all AI trading agents.
Specialized agents extend this base class.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone
from enum import Enum

from app.integrations.ai.base import BaseLLM
from app.integrations.ai.factory import get_model_factory
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AgentRole(str, Enum):
    """Agent role types"""
    MARKET_ANALYST = "market_analyst"
    SENTIMENT_ANALYST = "sentiment_analyst"
    RISK_MANAGER = "risk_manager"
    EXECUTOR = "executor"
    MONITOR = "monitor"


class AgentStatus(str, Enum):
    """Agent status"""
    IDLE = "idle"
    ANALYZING = "analyzing"
    DECIDING = "deciding"
    EXECUTING = "executing"
    ERROR = "error"
    COMPLETED = "completed"


class BaseAgent(ABC):
    """
    Abstract base class for AI trading agents.
    
    All specialized agents extend this class.
    
    Usage:
        class MarketAnalystAgent(BaseAgent):
            async def analyze(self, context):
                # Implementation
                pass
        
        agent = MarketAnalystAgent(
            role=AgentRole.MARKET_ANALYST,
            model_provider="gemini"
        )
        
        result = await agent.process(context)
    """
    
    def __init__(
        self,
        role: AgentRole,
        model_provider: str = "gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize AI agent.
        
        Args:
            role: Agent role (e.g., AgentRole.MARKET_ANALYST)
            model_provider: LLM provider (e.g., "gemini", "groq")
            model_name: Specific model name (optional)
            api_key: API key for model (optional, can use env)
            **kwargs: Additional config
        """
        self.role = role
        self.model_provider = model_provider
        self.status = AgentStatus.IDLE
        
        # Initialize LLM model
        factory = get_model_factory()
        
        # Get API key from kwargs or env
        if not api_key:
            import os
            api_key_env = {
                "gemini": "GEMINI_API_KEY",
                "groq": "GROQ_API_KEY",
                "openrouter": "OPENROUTER_API_KEY",
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "xai": "XAI_API_KEY"
            }
            api_key = os.getenv(api_key_env.get(model_provider.lower(), ""), "")
        
        self.model = factory.create_model(
            provider=model_provider,
            model_name=model_name or "",
            api_key=api_key,
            **kwargs
        )
        
        # Agent state
        self.cost_tracking = {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": Decimal("0")
        }
        
        # Config
        self.config = kwargs
        
        logger.info(f"{role.value} agent initialized with {model_provider} model")
    
    @abstractmethod
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process context and generate decision.
        
        Args:
            context: Context data (market data, positions, etc.)
            
        Returns:
            Dict with agent decision/recommendation
            
        Example:
            {
                "action": "buy" | "sell" | "hold",
                "confidence": 0.85,
                "reasoning": "Market showing bullish momentum...",
                "recommendation": {...}
            }
        """
        pass
    
    async def analyze(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        structured: bool = False,
        schema: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Analyze using LLM model with automatic fallback to OpenRouter on rate limits.
        
        Args:
            prompt: Analysis prompt
            system_prompt: System instructions
            temperature: Sampling temperature
            structured: Whether to return structured output
            schema: JSON schema for structured output
            
        Returns:
            Text response or structured dict
        """
        try:
            self.status = AgentStatus.ANALYZING
            
            # Track request
            self.cost_tracking["total_requests"] += 1
            
            # Generate response
            if structured and schema:
                result = await self.model.generate_structured_output(
                    prompt=prompt,
                    schema=schema,
                    system_prompt=system_prompt,
                    temperature=temperature
                )
            else:
                result = await self.model.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature
                )
            
            # Track cost
            model_info = self.model.get_model_info()
            self.cost_tracking["total_input_tokens"] += model_info["total_input_tokens"]
            self.cost_tracking["total_output_tokens"] += model_info["total_output_tokens"]
            self.cost_tracking["total_cost_usd"] += Decimal(str(model_info["total_cost_usd"]))
            
            self.status = AgentStatus.IDLE
            
            return result
        
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for rate limit errors (429) - fallback to OpenRouter
            if "429" in str(e) or "rate_limit" in error_str or "rate limit" in error_str:
                logger.warning(f"{self.role.value} agent hit rate limit on {self.model_provider}, falling back to OpenRouter")
                
                try:
                    result = await self._fallback_analyze(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        structured=structured,
                        schema=schema
                    )
                    self.status = AgentStatus.IDLE
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback to OpenRouter also failed: {fallback_error}")
                    self.status = AgentStatus.ERROR
                    raise fallback_error
            
            self.status = AgentStatus.ERROR
            logger.error(f"{self.role.value} agent analysis failed: {str(e)}")
            raise
    
    async def _fallback_analyze(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        structured: bool = False,
        schema: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Fallback analysis using OpenRouter when primary provider hits rate limits.
        """
        import os
        factory = get_model_factory()
        
        # Create OpenRouter fallback model
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY not set - cannot fallback")
        
        fallback_model = factory.create_model(
            provider="openrouter",
            model_name="meta-llama/llama-3.1-70b-instruct",  # Good fallback model
            api_key=openrouter_key
        )
        
        logger.info(f"Using OpenRouter fallback for {self.role.value} agent")
        
        # Generate response with fallback
        if structured and schema:
            result = await fallback_model.generate_structured_output(
                prompt=prompt,
                schema=schema,
                system_prompt=system_prompt,
                temperature=temperature
            )
        else:
            result = await fallback_model.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature
            )
        
        # Track cost from fallback
        model_info = fallback_model.get_model_info()
        self.cost_tracking["total_input_tokens"] += model_info["total_input_tokens"]
        self.cost_tracking["total_output_tokens"] += model_info["total_output_tokens"]
        self.cost_tracking["total_cost_usd"] += Decimal(str(model_info["total_cost_usd"]))
        
        return result
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost tracking summary"""
        return {
            "role": self.role.value,
            "total_requests": self.cost_tracking["total_requests"],
            "total_input_tokens": self.cost_tracking["total_input_tokens"],
            "total_output_tokens": self.cost_tracking["total_output_tokens"],
            "total_cost_usd": float(self.cost_tracking["total_cost_usd"]),
            "average_cost_per_request": (
                float(self.cost_tracking["total_cost_usd"]) / self.cost_tracking["total_requests"]
                if self.cost_tracking["total_requests"] > 0 else 0
            )
        }
    
    def reset_cost_tracking(self):
        """Reset cost tracking"""
        self.cost_tracking = {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": Decimal("0")
        }
        self.model.reset_usage()
    
    def __str__(self) -> str:
        """String representation"""
        return f"{self.role.value} agent ({self.model_provider})"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return (
            f"<{self.__class__.__name__} "
            f"role={self.role.value} "
            f"provider={self.model_provider} "
            f"status={self.status.value} "
            f"cost=${float(self.cost_tracking['total_cost_usd']):.4f}>"
        )


