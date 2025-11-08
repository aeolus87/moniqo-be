"""
MongoDB database connection using Motor (async driver).

Provides database instance and connection management with lifespan events.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Global database client and database instances
_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def connect_to_mongodb() -> None:
    """
    Connect to MongoDB database.
    
    This function is called during application startup.
    Creates a connection pool and tests the connection.
    
    Raises:
        Exception: If connection to MongoDB fails
    """
    global _client, _database
    
    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}")
        
        # Create MongoDB client
        _client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,  # 5 seconds timeout
            maxPoolSize=10,  # Maximum number of connections in the pool
            minPoolSize=1,   # Minimum number of connections in the pool
        )
        
        # Get database instance
        _database = _client[settings.MONGODB_DB_NAME]
        
        # Test the connection
        await _client.admin.command("ping")
        
        logger.info(f"Successfully connected to MongoDB database: {settings.MONGODB_DB_NAME}")
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise


async def close_mongodb_connection() -> None:
    """
    Close MongoDB database connection.
    
    This function is called during application shutdown.
    Closes all connections in the pool.
    """
    global _client, _database
    
    if _client:
        logger.info("Closing MongoDB connection")
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance.
    
    Returns:
        AsyncIOMotorDatabase: MongoDB database instance
        
    Raises:
        RuntimeError: If database is not connected
    """
    if _database is None:
        raise RuntimeError(
            "Database is not connected. Call connect_to_mongodb() first."
        )
    return _database


# Convenience alias
get_db = get_database

