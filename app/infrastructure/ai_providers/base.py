"""
BaseLLM - Abstract Base Class for LLM Integrations

Unified interface for all LLM providers.
Similar to BaseWallet pattern for wallet integrations.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from datetime import datetime
from enum import Enum


class ModelProvider(str, Enum):
    """LLM provider types"""
    GEMINI = "gemini"
    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    XAI = "xai"
    OLLAMA = "ollama"


class ModelError(Exception):
    """Base exception for model errors"""
    pass


class ModelConnectionError(ModelError):
    """Connection error with model provider"""
    pass


class ModelAuthenticationError(ModelError):
    """Authentication error with model provider"""
    pass


class ModelRateLimitError(ModelError):
    """Rate limit exceeded"""
    pass


class ModelTokenLimitError(ModelError):
    """Token limit exceeded"""
    pass


class BaseLLM(ABC):
    """
    Abstract base class for LLM integrations.
    
    All LLM providers must implement this interface.
    Similar to BaseWallet pattern.
    
    Usage:
        # In concrete implementation
        class GeminiModel(BaseLLM):
            async def generate_response(self, prompt, **kwargs):
                # Implementation
                pass
        
        # Usage
        model = GeminiModel(api_key="key", model_name="gemini-1.5-pro")
        response = await model.generate_response("Analyze BTC market")
        cost = model.calculate_cost(input_tokens=100, output_tokens=50)
    """
    
    def __init__(
        self,
        provider: ModelProvider,
        model_name: str,
        api_key: str,
        **kwargs
    ):
        """
        Initialize LLM model.
        
        Args:
            provider: Model provider (e.g., ModelProvider.GEMINI)
            model_name: Model name (e.g., "gemini-1.5-pro")
            api_key: API key for the provider
            **kwargs: Additional provider-specific config
        """
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        self.config = kwargs
        
        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = Decimal("0")
    
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text response from model.
        
        Args:
            prompt: User prompt/question
            system_prompt: System instructions (optional)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate (optional)
            **kwargs: Provider-specific parameters
            
        Returns:
            Generated text response
            
        Raises:
            ModelConnectionError: Connection failed
            ModelAuthenticationError: Invalid API key
            ModelRateLimitError: Rate limit exceeded
            ModelTokenLimitError: Token limit exceeded
        """
        pass
    
    @abstractmethod
    async def generate_structured_output(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured output (JSON) from model.
        
        Args:
            prompt: User prompt/question
            schema: JSON schema for output format
            system_prompt: System instructions (optional)
            temperature: Sampling temperature (0.0-2.0)
            **kwargs: Provider-specific parameters
            
        Returns:
            Structured output (dict matching schema)
            
        Raises:
            ModelError: Generation failed
            ModelTokenLimitError: Token limit exceeded
        """
        pass
    
    @abstractmethod
    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """
        Calculate cost for token usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to model provider.
        
        Returns:
            Dict with connection status and latency
            
        Raises:
            ModelConnectionError: Connection failed
            ModelAuthenticationError: Invalid API key
        """
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model information.
        
        Returns:
            Dict with model details
        """
        return {
            "provider": self.provider.value,
            "model_name": self.model_name,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": float(self.total_cost_usd),
            "config": self.config
        }
    
    def track_usage(
        self,
        input_tokens: int,
        output_tokens: int
    ):
        """
        Track token usage and cost.
        
        Args:
            input_tokens: Input tokens used
            output_tokens: Output tokens used
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        cost = self.calculate_cost(input_tokens, output_tokens)
        self.total_cost_usd += cost
    
    def reset_usage(self):
        """Reset usage tracking"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = Decimal("0")
    
    def __str__(self) -> str:
        """String representation"""
        return f"{self.provider.value}:{self.model_name}"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return (
            f"<{self.__class__.__name__} "
            f"provider={self.provider.value} "
            f"model={self.model_name} "
            f"cost=${float(self.total_cost_usd):.4f}>"
        )


