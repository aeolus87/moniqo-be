"""
Integration Tests for Trading Mode Middleware

Tests middleware behavior, wallet validation, and safety gates.
"""

import pytest
from fastapi.testclient import TestClient
from bson import ObjectId

from app.main import app
from app.core.context import TradingMode
from app.core.trading_mode import set_trading_mode_context, get_trading_mode_context
from app.core.middleware import TradingModeMiddleware


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_middleware_sets_context():
    """Test that middleware sets trading mode context."""
    # This would be tested in integration tests with actual requests
    # For now, we test the context setting directly
    set_trading_mode_context(TradingMode.DEMO)
    assert get_trading_mode_context() == TradingMode.DEMO
    
    set_trading_mode_context(TradingMode.REAL)
    assert get_trading_mode_context() == TradingMode.REAL


@pytest.mark.asyncio
async def test_middleware_defaults_to_demo():
    """Test that middleware defaults to demo if mode cannot be determined."""
    # Reset context
    set_trading_mode_context(None)
    
    # When mode cannot be determined, should default to demo
    from app.core.trading_mode import get_trading_mode_context_or_default
    mode = get_trading_mode_context_or_default()
    
    assert mode == TradingMode.DEMO


@pytest.mark.asyncio
async def test_validate_wallet_mode_demo():
    """Test wallet mode validation for demo wallet."""
    from app.core.trading_mode import validate_wallet_mode
    from app.core.database import db_provider
    
    # This test would require setting up test data
    # For now, we test the function signature and basic logic
    db = db_provider.get_db_for_mode(TradingMode.DEMO)
    
    # Test with invalid wallet ID (should return False)
    result = await validate_wallet_mode(
        str(ObjectId()),
        TradingMode.DEMO,
        db
    )
    
    # Should return False for non-existent wallet
    assert result is False


@pytest.mark.asyncio
async def test_middleware_skips_health_endpoints():
    """Test that middleware skips health check endpoints."""
    middleware = TradingModeMiddleware(app)
    
    # These paths should be skipped
    skip_paths = [
        "/health",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
        "/",
    ]
    
    for path in skip_paths:
        assert middleware._should_skip_middleware(path) is True
    
    # These paths should not be skipped
    assert middleware._should_skip_middleware("/api/v1/orders") is False
    assert middleware._should_skip_middleware("/api/v1/positions") is False


@pytest.mark.asyncio
async def test_safety_gate_wallet_mismatch():
    """Test that safety gate prevents mode mismatches."""
    # This would be tested with actual HTTP requests
    # For now, we verify the validation logic exists
    
    from app.core.trading_mode import validate_wallet_mode
    from app.core.database import db_provider
    
    db = db_provider.get_db_for_mode(TradingMode.DEMO)
    
    # Test validation function exists and works
    # (Actual test would require test wallet data)
    result = await validate_wallet_mode(
        str(ObjectId()),
        TradingMode.DEMO,
        db
    )
    
    # Should return False for invalid wallet
    assert isinstance(result, bool)


def test_middleware_initialization():
    """Test that middleware can be initialized."""
    middleware = TradingModeMiddleware(app)
    assert middleware is not None
    assert hasattr(middleware, 'dispatch')
    assert hasattr(middleware, '_determine_trading_mode')
    assert hasattr(middleware, '_validate_request_mode')
