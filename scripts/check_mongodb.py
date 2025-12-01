#!/usr/bin/env python3
"""
Quick script to check MongoDB connection.

Usage:
    python scripts/check_mongodb.py
"""

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings

async def check_mongodb():
    """Check MongoDB connection."""
    if settings is None:
        print("❌ Settings not loaded. Check your .env file.")
        print("\nRequired environment variables:")
        print("- MONGODB_URL")
        print("- MONGODB_DB_NAME")
        print("- ENCRYPTION_KEY (for Phase 2)")
        print("- And others...")
        return False
    
    print(f"Attempting to connect to MongoDB...")
    print(f"URL: {settings.MONGODB_URL}")
    print(f"Database: {settings.MONGODB_DB_NAME}")
    print()
    
    try:
        client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000
        )
        
        # Test connection
        await client.admin.command("ping")
        print("✅ MongoDB connection successful!")
        
        # List databases
        db_list = await client.list_database_names()
        print(f"\nAvailable databases: {', '.join(db_list)}")
        
        # Check if our database exists
        if settings.MONGODB_DB_NAME in db_list:
            print(f"✅ Database '{settings.MONGODB_DB_NAME}' exists")
        else:
            print(f"⚠️  Database '{settings.MONGODB_DB_NAME}' will be created on first use")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure MongoDB is running:")
        print("   - Linux/WSL: sudo systemctl start mongod")
        print("   - Docker: docker run -d -p 27017:27017 mongo")
        print("   - macOS: brew services start mongodb-community")
        print("2. Check your MONGODB_URL in .env file")
        print("3. Verify MongoDB is listening on the correct port")
        return False

if __name__ == "__main__":
    success = asyncio.run(check_mongodb())
    sys.exit(0 if success else 1)

