"""
AI Model Factory

Factory pattern for creating LLM instances.
Similar to WalletFactory pattern.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Dict, Type, Optional, Any
from app.infrastructure.ai_providers.base import BaseLLM, ModelProvider
from app.infrastructure.ai_providers.gemini_model import GeminiModel
from app.infrastructure.ai_providers.groq_model import GroqModel
from app.infrastructure.ai_providers.openrouter_model import OpenRouterModel
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ModelFactory:
    """
    AI Model Factory
    
    Creates LLM instances based on provider type.
    Singleton pattern - one instance per application.
    
    Usage:
        factory = ModelFactory()
        
        # Create Gemini model
        gemini = factory.create_model(
            provider="gemini",
            model_name="gemini-1.5-pro",
            api_key="your_key"
        )
        
        # Create Groq model
        groq = factory.create_model(
            provider="groq",
            model_name="llama-3.3-70b-versatile",
            api_key="your_key"
        )
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize factory"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        
        # Registered model classes
        self._models: Dict[str, Type[BaseLLM]] = {}
        
        # Register default models
        self._register_default_models()
        
        logger.info("AI model factory initialized")
    
    def register(self, provider: str, model_class: Type[BaseLLM]):
        """
        Register a model class for a provider.
        
        Args:
            provider: Provider name (e.g., "gemini", "groq")
            model_class: Model class (must extend BaseLLM)
        """
        self._models[provider.lower()] = model_class
        logger.debug(f"Registered model provider: {provider}")
    
    def create_model(
        self,
        provider: str,
        model_name: str = "",
        api_key: str = "",
        **kwargs
    ) -> BaseLLM:
        """
        Create a model instance.
        
        Args:
            provider: Provider name (e.g., "gemini", "groq")
            model_name: Model name (e.g., "gemini-1.5-pro")
            api_key: API key for the provider
            **kwargs: Additional provider-specific config
            
        Returns:
            Model instance (extends BaseLLM)
            
        Raises:
            ValueError: Unknown provider or missing parameters
        """
        provider = provider.lower()
        
        # Get model class
        model_class = self._models.get(provider)
        
        if not model_class:
            raise ValueError(
                f"Unknown model provider: {provider}. "
                f"Available providers: {list(self._models.keys())}"
            )
        
        # Set default model names if not provided
        if not model_name:
            defaults = {
                "gemini": "gemini-1.5-pro",
                "groq": "llama-3.3-70b-versatile",
                "openrouter": "meta-llama/llama-3.1-8b-instruct:free",
                "openai": "gpt-4-turbo-preview",
                "anthropic": "claude-3-5-sonnet-20241022",
                "xai": "grok-beta",
                "ollama": "llama3"
            }
            model_name = defaults.get(provider, model_name)
        
        if not model_name:
            raise ValueError(f"Model name is required for provider: {provider}")
        
        # Create model instance
        try:
            model = model_class(
                model_name=model_name,
                api_key=api_key,
                **kwargs
            )
            
            logger.info(f"Created {provider} model: {model_name}")
            
            return model
        
        except Exception as e:
            logger.error(f"Failed to create {provider} model: {str(e)}")
            raise ValueError(f"Failed to create {provider} model: {str(e)}")
    
    def _register_default_models(self):
        """Register default model implementations"""
        self.register("gemini", GeminiModel)
        self.register("groq", GroqModel)
        self.register("openrouter", OpenRouterModel)
        
        # Future: Register other models
        # self.register("openai", OpenAIModel)
        # self.register("anthropic", AnthropicModel)
        # self.register("xai", XAIModel)
        # self.register("ollama", OllamaModel)
        
        logger.debug(f"Registered {len(self._models)} model providers")
    
    def get_available_providers(self) -> list:
        """Get list of available providers"""
        return list(self._models.keys())
    
    def is_provider_available(self, provider: str) -> bool:
        """Check if provider is available"""
        return provider.lower() in self._models


# Global factory instance
_factory = None


def get_model_factory() -> ModelFactory:
    """
    Get global model factory instance.
    
    Returns:
        Shared ModelFactory instance
        
    Example:
        from app.infrastructure.ai_providers.factory import get_model_factory
        
        factory = get_model_factory()
        model = factory.create_model("gemini", api_key="your_key")
    """
    global _factory
    
    if _factory is None:
        _factory = ModelFactory()
    
    return _factory


