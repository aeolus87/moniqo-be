"""
Model Factory Tests

Comprehensive tests for AI model factory.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from unittest.mock import Mock, patch

from app.integrations.ai.factory import ModelFactory, get_model_factory
from app.integrations.ai.base import ModelProvider
from app.integrations.ai.gemini_model import GeminiModel
from app.integrations.ai.groq_model import GroqModel


# ==================== FACTORY TESTS ====================

def test_model_factory_singleton():
    """Test factory is singleton"""
    factory1 = ModelFactory()
    factory2 = ModelFactory()
    
    assert factory1 is factory2
    assert id(factory1) == id(factory2)


def test_model_factory_get_available_providers():
    """Test getting available providers"""
    factory = ModelFactory()
    providers = factory.get_available_providers()
    
    assert "gemini" in providers
    assert "groq" in providers
    assert isinstance(providers, list)


def test_model_factory_is_provider_available():
    """Test checking if provider is available"""
    factory = ModelFactory()
    
    assert factory.is_provider_available("gemini") is True
    assert factory.is_provider_available("groq") is True
    assert factory.is_provider_available("unknown") is False


def test_model_factory_create_gemini_model():
    """Test creating Gemini model"""
    factory = ModelFactory()
    
    with patch('google.generativeai.configure'):
        with patch('google.generativeai.GenerativeModel'):
            model = factory.create_model(
                provider="gemini",
                model_name="gemini-1.5-pro",
                api_key="test_key"
            )
            
            assert isinstance(model, GeminiModel)
            assert model.provider == ModelProvider.GEMINI
            assert model.model_name == "gemini-1.5-pro"


def test_model_factory_create_groq_model():
    """Test creating Groq model"""
    factory = ModelFactory()
    
    with patch('groq.AsyncGroq'):
        model = factory.create_model(
            provider="groq",
            model_name="llama-3.3-70b-versatile",
            api_key="test_key"
        )
        
        assert isinstance(model, GroqModel)
        assert model.provider == ModelProvider.GROQ
        assert model.model_name == "llama-3.3-70b-versatile"


def test_model_factory_create_model_with_default_name():
    """Test creating model with default model name"""
    factory = ModelFactory()
    
    with patch('google.generativeai.configure'):
        with patch('google.generativeai.GenerativeModel'):
            model = factory.create_model(
                provider="gemini",
                api_key="test_key"
            )
            
            # Should use default: gemini-1.5-pro
            assert model.model_name == "gemini-1.5-pro"


def test_model_factory_create_model_unknown_provider():
    """Test creating model with unknown provider"""
    factory = ModelFactory()
    
    with pytest.raises(ValueError, match="Unknown model provider"):
        factory.create_model(
            provider="unknown_provider",
            api_key="test_key"
        )


def test_model_factory_register_provider():
    """Test registering custom provider"""
    factory = ModelFactory()
    
    # Create a test model class
    class TestModel:
        pass
    
    factory.register("test_provider", TestModel)
    
    assert factory.is_provider_available("test_provider") is True
    assert "test_provider" in factory.get_available_providers()


def test_get_model_factory_singleton():
    """Test get_model_factory returns singleton"""
    factory1 = get_model_factory()
    factory2 = get_model_factory()
    
    assert factory1 is factory2
    assert isinstance(factory1, ModelFactory)


# ==================== SUMMARY ====================

"""
Test Coverage Summary:
✅ Singleton pattern (2 tests)
✅ Provider availability (2 tests)
✅ Model creation (4 tests)
✅ Provider registration (1 test)
✅ Global factory (1 test)

TOTAL: 10 comprehensive tests
All testing factory behavior
"""


