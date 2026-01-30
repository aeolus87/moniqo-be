"""
Phase 1 Integration Test Fixtures

Provides fixtures and utilities for testing database isolation, safety gates,
and context-based routing for Orders, Positions, and Wallets.
"""

import pytest
from typing import AsyncGenerator
from bson import ObjectId
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.context import TradingMode, set_trading_mode, get_trading_mode
from app.core.database import db_provider


async def set_test_mode(mode: TradingMode) -> None:
    """
    Helper to set trading mode context for tests.
    
    Args:
        mode: Trading mode (DEMO or REAL)
    """
    set_trading_mode(mode)


async def verify_order_in_database(
    order_id: str,
    mode: TradingMode,
    should_exist: bool
) -> bool:
    """
    Verify order exists or doesn't exist in specified database.
    
    Args:
        order_id: Order ID to check
        mode: Trading mode (DEMO or REAL)
        should_exist: Whether order should exist
        
    Returns:
        bool: True if verification passes
    """
    db = db_provider.get_db_for_mode(mode)
    order = await db["orders"].find_one({"_id": ObjectId(order_id)})
    exists = order is not None
    return exists == should_exist


async def verify_position_in_database(
    position_id: str,
    mode: TradingMode,
    should_exist: bool
) -> bool:
    """
    Verify position exists or doesn't exist in specified database.
    
    Args:
        position_id: Position ID to check
        mode: Trading mode (DEMO or REAL)
        should_exist: Whether position should exist
        
    Returns:
        bool: True if verification passes
    """
    db = db_provider.get_db_for_mode(mode)
    position = await db["positions"].find_one({"_id": ObjectId(position_id)})
    exists = position is not None
    return exists == should_exist


async def create_test_wallet_definition(
    db: AsyncIOMotorDatabase,
    name: str = "Test Wallet",
    slug: str = "test-wallet",
    is_demo: bool = True,
    integration_type: str = "simulation"
) -> str:
    """
    Create a test wallet definition.
    
    Args:
        db: Database instance (use demo DB for shared collection)
        name: Wallet name
        slug: Wallet slug
        is_demo: Whether wallet is demo
        integration_type: Integration type
        
    Returns:
        str: Wallet definition ID
    """
    wallet_def = {
        "name": name,
        "slug": slug,
        "description": f"Test {name}",
        "integration_type": integration_type,
        "is_demo": is_demo,
        "is_active": True,
        "required_credentials": [],
        "supported_symbols": ["BTC/USDT", "ETH/USDT"],
        "supported_order_types": ["market", "limit"],
        "supports_margin": False,
        "supports_futures": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "deleted_at": None
    }
    
    result = await db["wallets"].insert_one(wallet_def)
    return str(result.inserted_id)


async def create_test_user_wallet(
    db: AsyncIOMotorDatabase,
    user_id: str,
    wallet_provider_id: str,
    use_testnet: bool = True,
    custom_name: str = "Test Wallet"
) -> str:
    """
    Create a test user wallet.
    
    Args:
        db: Database instance (mode-specific)
        user_id: User ID
        wallet_provider_id: Wallet definition ID
        use_testnet: Whether to use testnet (demo)
        custom_name: Custom wallet name
        
    Returns:
        str: User wallet ID
    """
    user_wallet = {
        "user_id": ObjectId(user_id),
        "wallet_provider_id": ObjectId(wallet_provider_id),
        "custom_name": custom_name,
        "use_testnet": use_testnet,
        "credentials": {},
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "deleted_at": None
    }
    
    result = await db["user_wallets"].insert_one(user_wallet)
    return str(result.inserted_id)


@pytest.fixture
async def test_demo_wallet_setup(db_provider_initialized) -> AsyncGenerator[dict, None]:
    """
    Create a complete demo wallet setup (definition + user wallet).
    
    Requires DatabaseProvider to be initialized.
    
    Yields:
        dict: Contains wallet_definition_id and user_wallet_id
    """
    # Use demo database for wallet definition (shared collection)
    db_demo = db_provider.get_db_for_mode(TradingMode.DEMO)
    
    # Create demo wallet definition
    wallet_def_id = await create_test_wallet_definition(
        db_demo,
        name="Demo Test Wallet",
        slug="demo-test-wallet",
        is_demo=True,
        integration_type="simulation"
    )
    
    # Create demo user wallet in demo database
    test_user_id = str(ObjectId())
    user_wallet_id = await create_test_user_wallet(
        db_demo,
        user_id=test_user_id,
        wallet_provider_id=wallet_def_id,
        use_testnet=True,
        custom_name="Demo Test Wallet"
    )
    
    yield {
        "wallet_definition_id": wallet_def_id,
        "user_wallet_id": user_wallet_id,
        "user_id": test_user_id
    }
    
    # Cleanup
    await db_demo["wallets"].delete_one({"_id": ObjectId(wallet_def_id)})
    await db_demo["user_wallets"].delete_one({"_id": ObjectId(user_wallet_id)})


@pytest.fixture
async def test_real_wallet_setup(db_provider_initialized) -> AsyncGenerator[dict, None]:
    """
    Create a complete real wallet setup (definition + user wallet).
    
    Requires DatabaseProvider to be initialized.
    
    Yields:
        dict: Contains wallet_definition_id and user_wallet_id
    """
    # Use demo database for wallet definition (shared collection)
    db_demo = db_provider.get_db_for_mode(TradingMode.DEMO)
    
    # Create real wallet definition
    wallet_def_id = await create_test_wallet_definition(
        db_demo,
        name="Real Test Wallet",
        slug="real-test-wallet",
        is_demo=False,
        integration_type="exchange"
    )
    
    # Create real user wallet in real database
    db_real = db_provider.get_db_for_mode(TradingMode.REAL)
    test_user_id = str(ObjectId())
    user_wallet_id = await create_test_user_wallet(
        db_real,
        user_id=test_user_id,
        wallet_provider_id=wallet_def_id,
        use_testnet=False,
        custom_name="Real Test Wallet"
    )
    
    yield {
        "wallet_definition_id": wallet_def_id,
        "user_wallet_id": user_wallet_id,
        "user_id": test_user_id
    }
    
    # Cleanup
    await db_demo["wallets"].delete_one({"_id": ObjectId(wallet_def_id)})
    await db_real["user_wallets"].delete_one({"_id": ObjectId(user_wallet_id)})
