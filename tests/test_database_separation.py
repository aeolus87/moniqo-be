"""
Tests for Database Separation

Tests that demo and real data are properly isolated in separate databases.
"""

import pytest
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.context import TradingMode
from app.core.database import db_provider
from app.repositories.order_repository import get_order_repository
from app.repositories.position_repository import get_position_repository
from app.repositories.flow_repository import get_flow_repository
from app.core.trading_mode import set_trading_mode_context, get_trading_mode_context


@pytest.mark.asyncio
async def test_database_separation_real_vs_demo():
    """Test that real and demo databases are separate instances."""
    db_real = db_provider.get_db_for_mode(TradingMode.REAL)
    db_demo = db_provider.get_db_for_mode(TradingMode.DEMO)
    
    assert db_real.name != db_demo.name
    assert db_real.name.endswith("_real") or "real" in db_real.name.lower()
    assert db_demo.name.endswith("_demo") or "demo" in db_demo.name.lower()


@pytest.mark.asyncio
async def test_repository_uses_correct_database():
    """Test that repositories use correct database based on mode."""
    # Test order repository
    repo_demo = get_order_repository(TradingMode.DEMO)
    repo_real = get_order_repository(TradingMode.REAL)
    
    assert repo_demo.repo.db.name != repo_real.repo.db.name
    assert "demo" in repo_demo.repo.db.name.lower() or repo_demo.repo.db.name.endswith("_demo")
    assert "real" in repo_real.repo.db.name.lower() or repo_real.repo.db.name.endswith("_real")


@pytest.mark.asyncio
async def test_order_repository_isolation(test_db: AsyncIOMotorDatabase):
    """Test that orders in demo and real databases are isolated."""
    # Create test orders in both databases
    demo_repo = get_order_repository(TradingMode.DEMO)
    real_repo = get_order_repository(TradingMode.REAL)
    
    test_user_id = ObjectId()
    
    # Insert order in demo
    demo_order = {
        "user_id": test_user_id,
        "symbol": "BTC/USDT",
        "side": "buy",
        "status": "pending",
        "deleted_at": None
    }
    demo_order_id = await demo_repo.insert_one(demo_order)
    
    # Insert order in real
    real_order = {
        "user_id": test_user_id,
        "symbol": "BTC/USDT",
        "side": "buy",
        "status": "pending",
        "deleted_at": None
    }
    real_order_id = await real_repo.insert_one(real_order)
    
    # Verify orders are in separate databases
    demo_orders = await demo_repo.find_by_user(str(test_user_id))
    real_orders = await real_repo.find_by_user(str(test_user_id))
    
    assert len(demo_orders) == 1
    assert len(real_orders) == 1
    assert demo_orders[0]["_id"] == demo_order_id
    assert real_orders[0]["_id"] == real_order_id
    assert demo_orders[0]["_id"] != real_orders[0]["_id"]
    
    # Verify demo repo can't see real orders and vice versa
    demo_count = await demo_repo.count_by_user(str(test_user_id))
    real_count = await real_repo.count_by_user(str(test_user_id))
    
    assert demo_count == 1
    assert real_count == 1


@pytest.mark.asyncio
async def test_position_repository_isolation(test_db: AsyncIOMotorDatabase):
    """Test that positions in demo and real databases are isolated."""
    demo_repo = get_position_repository(TradingMode.DEMO)
    real_repo = get_position_repository(TradingMode.REAL)
    
    test_user_id = ObjectId()
    
    # Insert position in demo
    demo_position = {
        "user_id": test_user_id,
        "symbol": "BTC/USDT",
        "side": "long",
        "status": "open",
        "deleted_at": None
    }
    demo_position_id = await demo_repo.insert_one(demo_position)
    
    # Insert position in real
    real_position = {
        "user_id": test_user_id,
        "symbol": "BTC/USDT",
        "side": "long",
        "status": "open",
        "deleted_at": None
    }
    real_position_id = await real_repo.insert_one(real_position)
    
    # Verify positions are isolated
    demo_positions = await demo_repo.find_by_user(str(test_user_id))
    real_positions = await real_repo.find_by_user(str(test_user_id))
    
    assert len(demo_positions) == 1
    assert len(real_positions) == 1
    assert demo_positions[0]["_id"] != real_positions[0]["_id"]


@pytest.mark.asyncio
async def test_trading_mode_context():
    """Test trading mode context management."""
    # Initially no context
    assert get_trading_mode_context() is None
    
    # Set context
    set_trading_mode_context(TradingMode.DEMO)
    assert get_trading_mode_context() == TradingMode.DEMO
    
    # Change context
    set_trading_mode_context(TradingMode.REAL)
    assert get_trading_mode_context() == TradingMode.REAL
    
    # Reset
    set_trading_mode_context(None)
    assert get_trading_mode_context() is None


@pytest.mark.asyncio
async def test_default_database_is_demo():
    """Test that default database is demo (fail-safe)."""
    db_default = db_provider.get_db()  # No mode specified, defaults to DEMO
    db_demo = db_provider.get_db_for_mode(TradingMode.DEMO)
    
    assert db_default.name == db_demo.name


@pytest.mark.asyncio
async def test_repository_factory_functions():
    """Test repository factory functions return correct instances."""
    # Order repository
    demo_order_repo = get_order_repository(TradingMode.DEMO)
    real_order_repo = get_order_repository(TradingMode.REAL)
    
    assert demo_order_repo.repo.db.name != real_order_repo.repo.db.name
    
    # Position repository
    demo_position_repo = get_position_repository(TradingMode.DEMO)
    real_position_repo = get_position_repository(TradingMode.REAL)
    
    assert demo_position_repo.repo.db.name != real_position_repo.repo.db.name
    
    # Flow repository
    demo_flow_repo = get_flow_repository(TradingMode.DEMO)
    real_flow_repo = get_flow_repository(TradingMode.REAL)
    
    assert demo_flow_repo.repo.db.name != real_flow_repo.repo.db.name
