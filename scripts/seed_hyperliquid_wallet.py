#!/usr/bin/env python3
"""
Seed script to create Hyperliquid wallet definition in the database.

Usage:
    python scripts/seed_hyperliquid_wallet.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add backend directory to Python path for imports
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from app.config.settings import settings

async def seed_hyperliquid_wallet():
    """Seed Hyperliquid wallet definition into the database."""
    if settings is None:
        print("❌ Settings not loaded. Check your .env file.")
        return False
    
    print("Connecting to MongoDB...")
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
        
        db = client[settings.MONGODB_DB_NAME]
        
        # Check if Hyperliquid wallet already exists
        existing = await db.wallets.find_one({"slug": "hyperliquid"})
        if existing:
            print("⚠️  Hyperliquid wallet definition already exists.")
            print(f"   ID: {existing['_id']}")
            print("   Skipping seed...")
            return True
        
        # Create Hyperliquid wallet definition
        wallet_definition = {
            "name": "Hyperliquid",
            "slug": "hyperliquid",
            "description": "Decentralized perpetual futures exchange with on-chain transparency",
            "integration_type": "perpetuals",
            "is_active": True,
            "is_demo": False,
            "supports_futures": True,
            "supports_perpetuals": True,
            "max_leverage": 20,
            "supported_markets": ["perpetuals"],
            "supported_assets": ["BTC", "ETH", "SOL", "BNB", "DOGE", "XRP", "ADA", "AVAX", "MATIC", "LINK"],
            "auth_fields": [
                {
                    "key": "private_key",
                    "label": "Private Key",
                    "type": "password",
                    "required": True,
                    "encrypted": True,
                    "description": "Wallet private key (0x-prefixed hex string, 66 characters)"
                },
                {
                    "key": "wallet_address",
                    "label": "Wallet Address",
                    "type": "text",
                    "required": True,
                    "encrypted": False,
                    "description": "Wallet address (0x-prefixed hex string, 42 characters)"
                }
            ],
            "capabilities": {
                "spot_trading": False,
                "futures_trading": False,
                "perpetuals_trading": True,
                "margin_trading": False,
                "options_trading": False,
                "supported_order_types": ["market", "limit"],
                "leverage": {
                    "available": True,
                    "min": 1,
                    "max": 20,
                    "adjustable": True
                },
                "fees": {
                    "maker_fee_percent": 0.02,
                    "taker_fee_percent": 0.05,
                    "withdrawal_fee_percent": 0.0
                }
            },
            "api_config": {
                "base_url": "https://api.hyperliquid.xyz",
                "websocket_url": "wss://api.hyperliquid.xyz/ws",
                "requires_api_key": False,
                "requires_signature": True,
                "rate_limits": {
                    "requests_per_minute": 1000,
                    "orders_per_second": 10
                }
            },
            "order": 2,
            "tags": ["decentralized", "perpetuals", "on-chain", "low-fees"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": None,  # System seed
            "deleted_at": None
        }
        
        # Insert wallet definition
        result = await db.wallets.insert_one(wallet_definition)
        print(f"✅ Created Hyperliquid wallet definition!")
        print(f"   ID: {result.inserted_id}")
        print(f"   Slug: {wallet_definition['slug']}")
        print(f"   Max Leverage: {wallet_definition['max_leverage']}x")
        print()
        print("📝 Next steps:")
        print("   1. Users can now connect their Hyperliquid wallets")
        print("   2. Credentials (private_key) will be encrypted")
        print("   3. Trading flows can use Hyperliquid for perpetual futures")
        
        return True
        
    except Exception as e:
        print(f"❌ Error seeding Hyperliquid wallet: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        client.close()

if __name__ == "__main__":
    success = asyncio.run(seed_hyperliquid_wallet())
    sys.exit(0 if success else 1)
