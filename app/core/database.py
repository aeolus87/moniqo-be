"""
MongoDB Database Provider

Provides automatic database routing based on trading mode context.
Uses contextvars to determine which database (real/demo) to use.

Author: Moniqo Team
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.context import TradingMode, get_trading_mode
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseProvider:
    """
    Database Provider
    
    Automatically routes to correct database (real/demo) based on trading mode context.
    Uses contextvars to determine mode - no need to pass mode explicitly.
    
    Usage:
        db = db_provider.get_db()
        orders = await db["orders"].find_one({...})
    """
    
    def __init__(self):
        """Initialize database provider."""
        self._real_client: AsyncIOMotorClient | None = None
        self._demo_client: AsyncIOMotorClient | None = None
        self._real_db: AsyncIOMotorDatabase | None = None
        self._demo_db: AsyncIOMotorDatabase | None = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize database connections.
        
        Must be called during app startup before using get_db().
        """
        if self._initialized:
            return
        
        settings = get_settings()
        if not settings:
            raise RuntimeError("Settings not loaded")
        
        mongodb_url = settings.MONGODB_URL
        db_name_real = settings.mongodb_db_name_real
        db_name_demo = settings.mongodb_db_name_demo
        
        logger.info(f"Initializing DatabaseProvider: real={db_name_real}, demo={db_name_demo}")
        
        # Create clients (can use same URL, different databases)
        self._real_client = AsyncIOMotorClient(
            mongodb_url,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=10,
            minPoolSize=1,
        )
        
        self._demo_client = AsyncIOMotorClient(
            mongodb_url,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=10,
            minPoolSize=1,
        )
        
        # Test connections
        await self._real_client.admin.command("ping")
        await self._demo_client.admin.command("ping")
        
        # Get database instances
        self._real_db = self._real_client[db_name_real]
        self._demo_db = self._demo_client[db_name_demo]
        
        # Create indexes for both databases
        await self._create_indexes(self._real_db)
        await self._create_indexes(self._demo_db)
        
        self._initialized = True
        
        logger.info(
            "DatabaseProvider initialized: real=%s, demo=%s",
            db_name_real,
            db_name_demo
        )
    
    def get_db(self) -> AsyncIOMotorDatabase:
        """
        Get database instance for current trading mode.
        
        Automatically determines mode from contextvars.
        Defaults to DEMO if mode cannot be determined (fail-safe).
        
        Returns:
            AsyncIOMotorDatabase: Database instance for current mode
            
        Raises:
            RuntimeError: If provider not initialized
        """
        if not self._initialized:
            raise RuntimeError(
                "DatabaseProvider not initialized. Call initialize() first."
            )
        
        mode = get_trading_mode()
        
        if mode == TradingMode.REAL:
            if self._real_db is None:
                raise RuntimeError("Real database not initialized")
            return self._real_db
        
        # Default to demo (fail-safe)
        if self._demo_db is None:
            raise RuntimeError("Demo database not initialized")
        return self._demo_db
    
    def get_db_for_mode(self, mode: TradingMode) -> AsyncIOMotorDatabase:
        """
        Get database instance for specified trading mode.
        
        Args:
            mode: Trading mode (DEMO or REAL)
            
        Returns:
            AsyncIOMotorDatabase: Database instance for specified mode
        """
        if not self._initialized:
            raise RuntimeError("DatabaseProvider not initialized")
        
        if mode == TradingMode.REAL:
            if self._real_db is None:
                raise RuntimeError("Real database not initialized")
            return self._real_db
        
        if self._demo_db is None:
            raise RuntimeError("Demo database not initialized")
        return self._demo_db
    
    async def _create_indexes(self, db: AsyncIOMotorDatabase) -> None:
        """
        Create indexes for collections.
        
        Wrapped in try/except to handle production scenarios where
        index creation might take time or fail due to locks.
        
        Args:
            db: Database instance to create indexes on
        """
        logger.info(f"Ensuring indexes for {db.name}...")
        
        try:
            # Orders collection indexes
            orders_coll = db["orders"]
            await orders_coll.create_index("user_id")
            await orders_coll.create_index("status")
            await orders_coll.create_index("created_at")
            await orders_coll.create_index([("user_id", 1), ("status", 1), ("created_at", -1)])
            await orders_coll.create_index([("user_wallet_id", 1), ("status", 1)])
            await orders_coll.create_index("position_id")
            await orders_coll.create_index("external_order_id")
            await orders_coll.create_index([("status", 1), ("order_type", 1)])
            await orders_coll.create_index([("symbol", 1), ("created_at", -1)])
            
            logger.info(f"Indexes verified for {db.name}.orders")
        except Exception as e:
            error_msg = str(e)
            # Permission errors are expected in some environments - log as debug
            if "not authorized" in error_msg.lower() or "unauthorized" in error_msg.lower():
                logger.debug(f"Index creation skipped for {db.name}.orders (permission issue): {e}")
            else:
                logger.warning(f"Failed to create indexes for {db.name}.orders: {e}")
            # Don't raise - indexes can be created later, app should still start
        
        try:
            # Positions collection indexes
            positions_coll = db["positions"]
            await positions_coll.create_index("user_id")
            await positions_coll.create_index("status")
            await positions_coll.create_index("opened_at")
            await positions_coll.create_index([("user_id", 1), ("status", 1), ("opened_at", -1)])
            await positions_coll.create_index([("user_wallet_id", 1), ("status", 1)])
            await positions_coll.create_index([("status", 1), ("symbol", 1)])
            await positions_coll.create_index("flow_id")
            await positions_coll.create_index([("symbol", 1), ("opened_at", -1)])
            
            logger.info(f"Indexes verified for {db.name}.positions")
        except Exception as e:
            error_msg = str(e)
            # Permission errors are expected in some environments - log as debug
            if "not authorized" in error_msg.lower() or "unauthorized" in error_msg.lower():
                logger.debug(f"Index creation skipped for {db.name}.positions (permission issue): {e}")
            else:
                logger.warning(f"Failed to create indexes for {db.name}.positions: {e}")
            # Don't raise - indexes can be created later, app should still start
    
    async def close(self) -> None:
        """Close all database connections."""
        if self._real_client:
            self._real_client.close()
            self._real_client = None
        
        if self._demo_client:
            self._demo_client.close()
            self._demo_client = None
        
        self._real_db = None
        self._demo_db = None
        self._initialized = False
        
        logger.info("DatabaseProvider closed")


# Global database provider instance
db_provider = DatabaseProvider()
