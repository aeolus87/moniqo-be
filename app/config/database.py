"""
MongoDB database connection using Motor (async driver).

Provides database instance and connection management with lifespan events.
Supports separate databases for demo and real trading modes.
"""

import logging
from enum import Enum

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from beanie import init_beanie

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TradingMode(str, Enum):
    """Trading mode enum."""
    DEMO = "demo"
    REAL = "real"


# Global database client and database instances
_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None  # Legacy: defaults to demo for safety
_database_real: AsyncIOMotorDatabase | None = None
_database_demo: AsyncIOMotorDatabase | None = None


async def connect_to_mongodb() -> None:
    """
    Connect to MongoDB databases (real and demo).
    
    This function is called during application startup.
    Creates a connection pool and tests the connection.
    Connects to both real and demo databases for physical isolation.
    
    Raises:
        Exception: If connection to MongoDB fails
    """
    global _client, _database, _database_real, _database_demo
    
    try:
        current_settings = get_settings()

        if current_settings is None:
            raise RuntimeError(
                "Application settings could not be initialised. "
                "Verify that your .env file exists and contains all required values."
            )

        logger.info("Connecting to MongoDB at %s", current_settings.MONGODB_URL)
        
        # Create MongoDB client
        _client = AsyncIOMotorClient(
            current_settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,  # 5 seconds timeout
            maxPoolSize=10,  # Maximum number of connections in the pool
            minPoolSize=1,   # Minimum number of connections in the pool
        )
        
        # Test the connection
        await _client.admin.command("ping")
        
        # Get database instances for real and demo
        db_name_real = current_settings.mongodb_db_name_real
        db_name_demo = current_settings.mongodb_db_name_demo
        
        _database_real = _client[db_name_real]
        _database_demo = _client[db_name_demo]
        
        # Legacy: Default to demo database for backward compatibility (fail-safe)
        _database = _database_demo
        
        # Initialize Beanie with document models
        # Note: Beanie models are tied to a specific database instance at initialization
        # For mode-specific collections (orders, positions), we use repositories instead
        # Beanie is initialized for demo database for backward compatibility
        # When migrating to repositories, Beanie models will be used less frequently
        from app.modules.positions.models import PositionUpdate
        # Note: Order and Position Beanie models removed - using repositories instead
        # from app.modules.orders.models import Order
        # from app.modules.positions.models import Position
        
        # Initialize Beanie for demo database (default/legacy)
        await init_beanie(
            database=_database_demo,
            document_models=[PositionUpdate]  # Order and Position removed - using repositories
        )
        
        # Note: Real database operations should use repositories (OrderRepository, PositionRepository)
        # which handle database selection based on trading mode context
        
        logger.info(
            "Successfully connected to MongoDB databases: %s (real), %s (demo)",
            db_name_real,
            db_name_demo,
        )
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise


async def close_mongodb_connection() -> None:
    """
    Close MongoDB database connections.
    
    This function is called during application shutdown.
    Closes all connections in the pool.
    """
    global _client, _database, _database_real, _database_demo
    
    if _client:
        logger.info("Closing MongoDB connections")
        _client.close()
        _client = None
        _database = None
        _database_real = None
        _database_demo = None
        logger.info("MongoDB connections closed")


def get_database(mode: TradingMode | None = None) -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance for specified trading mode.
    
    Args:
        mode: Trading mode (DEMO or REAL). If None, defaults to DEMO for safety.
    
    Returns:
        AsyncIOMotorDatabase: MongoDB database instance
        
    Raises:
        RuntimeError: If database is not connected
    """
    if _client is None:
        raise RuntimeError(
            "Database is not connected. Call connect_to_mongodb() first."
        )
    
    # Default to demo for safety (fail-safe)
    if mode is None or mode == TradingMode.DEMO:
        if _database_demo is None:
            raise RuntimeError("Demo database is not connected.")
        return _database_demo
    
    if mode == TradingMode.REAL:
        if _database_real is None:
            raise RuntimeError("Real database is not connected.")
        return _database_real
    
    # Fallback to demo for safety
    if _database_demo is None:
        raise RuntimeError("Database is not connected.")
    return _database_demo


def get_database_real() -> AsyncIOMotorDatabase:
    """Get real trading database instance."""
    return get_database(TradingMode.REAL)


def get_database_demo() -> AsyncIOMotorDatabase:
    """Get demo trading database instance."""
    return get_database(TradingMode.DEMO)


# Convenience alias (backward compatibility - defaults to demo)
get_db = get_database

