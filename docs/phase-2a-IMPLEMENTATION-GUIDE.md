# Phase 2A Implementation Guide

**🎯 Quick Start Guide for AI Agents & Developers**

This document provides a step-by-step implementation guide for Phase 2A: Wallet Abstraction Layer.

---

## 📚 **DOCUMENTATION INDEX**

**Main Specification:** `phase-2a-wallet-abstraction-SPEC.md` (4,800+ lines)

### What's Included:
1. ✅ **Complete Database Schemas** - wallets, user_wallets, sync_log collections
2. ✅ **Base Wallet Interface** - Abstract class with 15+ methods
3. ✅ **Demo Wallet Implementation** - Full paper trading wallet (500+ lines)
4. ✅ **Pydantic Schemas** - 30+ request/response models
5. ✅ **Custom Exceptions** - 15+ wallet-specific errors
6. ✅ **Encryption Utilities** - Fernet encryption for credentials
7. ✅ **Celery Tasks** - Background balance syncing
8. ✅ **Service Layer** - 20+ business logic functions
9. ✅ **FastAPI Routers** - 15+ API endpoints with full documentation

---

## 🏗️ **IMPLEMENTATION ORDER**

### Day 1-2: Foundation & Database

#### Step 1: Create Directory Structure
```bash
cd Moniqo_BE/app

# Create wallet integration directories
mkdir -p integrations/wallets
touch integrations/__init__.py
touch integrations/wallets/__init__.py
touch integrations/wallets/base.py
touch integrations/wallets/demo_wallet.py
touch integrations/wallets/exceptions.py

# Create wallet module directories
mkdir -p modules/wallets
touch modules/wallets/__init__.py
touch modules/wallets/models.py
touch modules/wallets/schemas.py
touch modules/wallets/service.py
touch modules/wallets/router.py

# Create utils
touch utils/encryption.py

# Create tasks
mkdir -p tasks
touch tasks/__init__.py
touch tasks/balance_sync.py
touch tasks/celery_config.py
```

#### Step 2: Add Environment Variables
```bash
# Add to Moniqo_BE/.env

# Generate encryption key first:
python scripts/generate_encryption_key.py

# Then add to .env:
ENCRYPTION_KEY=your_generated_key_here

# Redis for Celery
REDIS_URL=redis://localhost:6379/0

# Polygon.io (Phase 2B+)
POLYGON_API_KEY=your_polygon_key_here
```

#### Step 3: Update requirements.txt
```bash
# Add these dependencies
echo "cryptography==41.0.7" >> requirements.txt
echo "celery[redis]==5.3.4" >> requirements.txt
echo "redis==5.0.1" >> requirements.txt

# Install
pip install -r requirements.txt
```

#### Step 4: Create Database Indexes
```python
# scripts/create_wallet_indexes.py

from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def create_indexes():
    client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    db = client.get_database("moniqo")
    
    # Wallets collection indexes
    await db.wallets.create_index("slug", unique=True)
    await db.wallets.create_index([("is_active", 1), ("order", 1)])
    await db.wallets.create_index("integration_type")
    await db.wallets.create_index("is_demo")
    await db.wallets.create_index("supported_markets")
    
    # User wallets collection indexes
    await db.user_wallets.create_index([("user_id", 1), ("is_active", 1)])
    await db.user_wallets.create_index([("user_id", 1), ("wallet_id", 1)])
    await db.user_wallets.create_index("status")
    await db.user_wallets.create_index("balance.last_synced_at")
    
    # Sync log with TTL (auto-delete after 30 days)
    await db.wallet_sync_log.create_index([("user_wallet_id", 1), ("started_at", -1)])
    await db.wallet_sync_log.create_index("status")
    await db.wallet_sync_log.create_index(
        "started_at",
        expireAfterSeconds=2592000  # 30 days
    )
    
    # Demo wallet state
    await db.demo_wallet_state.create_index("user_wallet_id", unique=True)
    
    print("✅ All wallet indexes created successfully")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(create_indexes())
```

Run it:
```bash
python scripts/create_wallet_indexes.py
```

---

### Day 3-4: Core Abstractions

#### Step 5: Implement Base Wallet Interface
Copy from spec: `app/integrations/wallets/base.py` (600+ lines)

Key classes:
- `BaseWallet` - Abstract base class
- `WalletBalance` - Balance data class
- `OrderResult` - Order execution result
- `MarketPrice` - Price data
- Enums: `OrderSide`, `OrderType`, `OrderStatus`, `TimeInForce`

#### Step 6: Implement Custom Exceptions
Copy from spec: `app/integrations/wallets/exceptions.py` (150+ lines)

All exceptions inherit from `WalletBaseException`.

#### Step 7: Implement Encryption Utilities
Copy from spec: `app/utils/encryption.py` (300+ lines)

Test it:
```python
from app.utils.encryption import CredentialEncryption

encryptor = CredentialEncryption()

# Test encryption
encrypted = encryptor.encrypt_value("my_secret")
print(f"Encrypted: {encrypted}")

decrypted = encryptor.decrypt_value(encrypted)
print(f"Decrypted: {decrypted}")
assert decrypted == "my_secret", "Encryption/decryption failed!"
```

---

### Day 5-6: Demo Wallet Implementation

#### Step 8: Implement Demo Wallet
Copy from spec: `app/integrations/wallets/demo_wallet.py` (500+ lines)

This is the complete paper trading implementation with:
- Balance tracking
- Market order execution with slippage
- Limit order management
- MongoDB state persistence
- Realistic fee simulation

#### Step 9: Test Demo Wallet Manually
```python
# scripts/test_demo_wallet.py

import asyncio
from decimal import Decimal
from motor.motor_asyncio import AsyncIOMotorClient
from app.integrations.wallets.demo_wallet import DemoWallet
from app.integrations.wallets.base import OrderSide, OrderType

async def test_demo_wallet():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.get_database("moniqo_test")
    
    # Create demo wallet
    wallet = DemoWallet(
        wallet_id="demo_wallet_def_id",
        user_wallet_id="test_user_wallet_id",
        credentials={"initial_balance_usd": "10000"},
        config={"db": db}
    )
    
    # Initialize
    await wallet.initialize()
    print("✅ Wallet initialized")
    
    # Get balance
    balances = await wallet.get_balance()
    for bal in balances:
        print(f"   {bal.asset}: {bal.total}")
    
    # Place market buy order
    print("\n📈 Placing BUY order for 0.01 BTC...")
    order = await wallet.place_order(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        amount=Decimal("0.01")
    )
    print(f"✅ Order filled at {order.average_fill_price} USDT")
    print(f"   Fee: {order.fee} {order.fee_currency}")
    
    # Check new balance
    print("\n💰 New balances:")
    balances = await wallet.get_balance()
    for bal in balances:
        print(f"   {bal.asset}: {bal.total}")
    
    # Close
    await wallet.close()
    client.close()
    
    print("\n✅ Demo wallet test passed!")

if __name__ == "__main__":
    asyncio.run(test_demo_wallet())
```

Run it:
```bash
python scripts/test_demo_wallet.py
```

---

### Day 7-8: Schemas & Models

#### Step 10: Implement Pydantic Schemas
Copy from spec: `app/modules/wallets/schemas.py` (600+ lines)

30+ schemas for requests/responses including:
- `CreateWalletDefinitionRequest`
- `CreateUserWalletRequest`
- `RiskLimitsSchema`
- `WalletDefinitionResponse`
- `UserWalletResponse`

#### Step 11: Implement MongoDB Models
Create: `app/modules/wallets/models.py`

```python
"""
MongoDB operations for wallet collections.

This layer handles direct database access.
Service layer calls these functions.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Dict, Optional
from datetime import datetime, timezone

# ==================== WALLET DEFINITIONS ====================

async def create_wallet(db: AsyncIOMotorDatabase, wallet_data: Dict) -> str:
    """Insert wallet definition"""
    result = await db.wallets.insert_one(wallet_data)
    return str(result.inserted_id)

async def get_wallet_by_id(db: AsyncIOMotorDatabase, wallet_id: str) -> Optional[Dict]:
    """Get wallet by ID"""
    return await db.wallets.find_one({"_id": ObjectId(wallet_id), "deleted_at": None})

async def get_wallet_by_slug(db: AsyncIOMotorDatabase, slug: str) -> Optional[Dict]:
    """Get wallet by slug"""
    return await db.wallets.find_one({"slug": slug, "deleted_at": None})

async def list_wallets(
    db: AsyncIOMotorDatabase,
    filters: Dict,
    skip: int = 0,
    limit: int = 100
) -> List[Dict]:
    """List wallets with filters"""
    cursor = db.wallets.find(filters).sort("order", 1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

async def count_wallets(db: AsyncIOMotorDatabase, filters: Dict) -> int:
    """Count wallets matching filters"""
    return await db.wallets.count_documents(filters)

async def update_wallet(
    db: AsyncIOMotorDatabase,
    wallet_id: str,
    update_data: Dict
) -> bool:
    """Update wallet definition"""
    result = await db.wallets.update_one(
        {"_id": ObjectId(wallet_id)},
        {"$set": update_data}
    )
    return result.modified_count > 0

async def soft_delete_wallet(db: AsyncIOMotorDatabase, wallet_id: str) -> bool:
    """Soft delete wallet"""
    result = await db.wallets.update_one(
        {"_id": ObjectId(wallet_id)},
        {
            "$set": {
                "deleted_at": datetime.now(timezone.utc),
                "is_active": False
            }
        }
    )
    return result.modified_count > 0

# ==================== USER WALLETS ====================

async def create_user_wallet(
    db: AsyncIOMotorDatabase,
    user_wallet_data: Dict
) -> str:
    """Insert user wallet"""
    result = await db.user_wallets.insert_one(user_wallet_data)
    return str(result.inserted_id)

async def get_user_wallet_by_id(
    db: AsyncIOMotorDatabase,
    user_wallet_id: str
) -> Optional[Dict]:
    """Get user wallet by ID"""
    return await db.user_wallets.find_one({
        "_id": ObjectId(user_wallet_id),
        "deleted_at": None
    })

async def list_user_wallets(
    db: AsyncIOMotorDatabase,
    filters: Dict,
    skip: int = 0,
    limit: int = 100
) -> List[Dict]:
    """List user wallets with filters"""
    cursor = db.user_wallets.find(filters).sort("created_at", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

async def count_user_wallets(db: AsyncIOMotorDatabase, filters: Dict) -> int:
    """Count user wallets matching filters"""
    return await db.user_wallets.count_documents(filters)

async def update_user_wallet(
    db: AsyncIOMotorDatabase,
    user_wallet_id: str,
    update_data: Dict
) -> bool:
    """Update user wallet"""
    result = await db.user_wallets.update_one(
        {"_id": ObjectId(user_wallet_id)},
        {"$set": update_data}
    )
    return result.modified_count > 0

async def soft_delete_user_wallet(
    db: AsyncIOMotorDatabase,
    user_wallet_id: str
) -> bool:
    """Soft delete user wallet"""
    result = await db.user_wallets.update_one(
        {"_id": ObjectId(user_wallet_id)},
        {
            "$set": {
                "deleted_at": datetime.now(timezone.utc),
                "is_active": False,
                "status": "deleted"
            }
        }
    )
    return result.modified_count > 0
```

---

### Day 9: Service Layer & Routers

#### Step 12: Implement Service Layer
Copy from spec: `app/modules/wallets/service.py` (800+ lines)

20+ functions including:
- `get_wallet_instance()` - Factory function
- `create_wallet_definition()`
- `create_user_wallet()`
- `sync_wallet_balance()`
- `test_wallet_connection()`
- `pause_user_wallet()`
- `resume_user_wallet()`

#### Step 13: Implement API Router
Copy from spec: `app/modules/wallets/router.py` (800+ lines)

15+ endpoints:
- `POST /wallets/definitions` - Create platform wallet
- `GET /wallets/definitions` - List available wallets
- `POST /wallets` - Create user wallet instance
- `GET /wallets` - List user's wallets
- `POST /wallets/{id}/test-connection` - Test connection
- `POST /wallets/{id}/sync-balance` - Manual balance sync
- `POST /wallets/{id}/pause` - Pause trading
- `POST /wallets/{id}/resume` - Resume trading

#### Step 14: Register Router in Main App
Edit: `app/main.py`

```python
# Add import
from app.modules.wallets.router import router as wallets_router

# Register router (around line 220)
app.include_router(wallets_router, prefix="/api/v1")
```

---

### Day 10: Celery & Background Tasks

#### Step 15: Implement Celery Tasks
Copy from spec:
- `app/tasks/celery_config.py`
- `app/tasks/balance_sync.py`

#### Step 16: Start Celery Worker
```bash
# Terminal 1: Start Celery worker
celery -A app.tasks.celery_config worker --loglevel=info

# Terminal 2: Start Celery beat (scheduler)
celery -A app.tasks.celery_config beat --loglevel=info

# Terminal 3: Start FastAPI
uvicorn app.main:app --reload
```

---

## 🧪 **TESTING CHECKLIST**

### Manual Testing Flow

1. **Start Services**
```bash
# Terminal 1: MongoDB
mongod

# Terminal 2: Redis
redis-server

# Terminal 3: Celery Worker
celery -A app.tasks.celery_config worker --loglevel=info

# Terminal 4: FastAPI
uvicorn app.main:app --reload
```

2. **Test API Endpoints** (use Postman/Thunder Client/curl)

```bash
# 1. List available wallet types
curl http://localhost:8000/api/v1/wallets/definitions

# 2. Login to get JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "your_password"}'

# Save the access_token as TOKEN

# 3. Create demo wallet
curl -X POST http://localhost:8000/api/v1/wallets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "DEMO_WALLET_ID_FROM_STEP_1",
    "custom_name": "My First Demo Wallet",
    "credentials": {
      "initial_balance_usd": "10000"
    },
    "risk_limits": {
      "max_position_size_usd": 1000,
      "max_total_exposure_usd": 5000,
      "max_open_positions": 5,
      "daily_loss_limit_usd": 500,
      "stop_loss_default_percent": 2.0,
      "take_profit_default_percent": 5.0
    }
  }'

# 4. List your wallets
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/wallets

# 5. Test connection
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/wallets/{WALLET_ID}/test-connection

# 6. Sync balance
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/wallets/{WALLET_ID}/sync-balance

# 7. Get wallet details
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/wallets/{WALLET_ID}
```

3. **Check Swagger Docs**
```
http://localhost:8000/api/docs
```
All wallet endpoints should be visible with full documentation.

---

## ✅ **SUCCESS CRITERIA**

Phase 2A is complete when:

- [ ] All files created in correct locations
- [ ] Database indexes created successfully
- [ ] Encryption key generated and set in .env
- [ ] Demo wallet can be instantiated
- [ ] Demo wallet can execute market orders
- [ ] User can create wallet via API
- [ ] User can list their wallets
- [ ] Connection test works
- [ ] Balance sync works
- [ ] Celery worker processes balance sync task
- [ ] All API endpoints return proper responses
- [ ] Swagger documentation shows all endpoints
- [ ] No credentials exposed in API responses
- [ ] Soft delete works for wallets
- [ ] Pause/resume functionality works

---

## 🐛 **TROUBLESHOOTING**

### Common Issues:

**1. Encryption Error: "ENCRYPTION_KEY not set"**
```bash
# Generate key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env:
ENCRYPTION_KEY=your_key_here
```

**2. MongoDB Connection Error**
```bash
# Check MongoDB is running:
mongosh

# Check connection string in .env:
MONGODB_URL=mongodb://localhost:27017/moniqo
```

**3. Redis Connection Error**
```bash
# Check Redis is running:
redis-cli ping
# Should return: PONG

# Check .env:
REDIS_URL=redis://localhost:6379/0
```

**4. Celery Not Processing Tasks**
```bash
# Make sure Celery worker is running:
celery -A app.tasks.celery_config worker --loglevel=info

# Check Redis has tasks:
redis-cli
> KEYS *
```

**5. Import Errors**
```bash
# Make sure you're in venv:
source venv/bin/activate

# Reinstall requirements:
pip install -r requirements.txt
```

---

## 📊 **MONITORING & LOGS**

### Check Logs:
```bash
# Application logs
tail -f logs/app.log

# Celery worker logs
# (shown in terminal where worker is running)

# MongoDB logs
tail -f /var/log/mongodb/mongod.log

# Redis logs
redis-cli MONITOR
```

### Monitor Celery Tasks:
```bash
# Using Flower (optional)
pip install flower
celery -A app.tasks.celery_config flower
# Visit: http://localhost:5555
```

---

## 🎯 **NEXT STEPS: Phase 2B**

After Phase 2A is complete:

1. **Add Binance Integration**
   - Implement `BinanceWallet` class
   - Test on Binance testnet

2. **Add Market Data**
   - Integrate Polygon.io WebSocket
   - Real-time price feeds
   - OHLCV data fetching

3. **Improve Demo Wallet**
   - Use real market prices
   - Limit order execution logic
   - Stop loss/take profit triggers

---

## 📖 **ADDITIONAL RESOURCES**

- **Full Specification:** `phase-2a-wallet-abstraction-SPEC.md`
- **Workspace Rules:** `.cursor/rules/`
- **Existing Phase 1 Code:** `app/modules/auth/`, `app/modules/users/`
- **MongoDB Docs:** https://www.mongodb.com/docs/drivers/motor/
- **Celery Docs:** https://docs.celeryq.dev/
- **Cryptography Docs:** https://cryptography.io/

---

**🎉 You're ready to implement Phase 2A! Follow this guide step-by-step, and you'll have a production-ready wallet abstraction layer.**

**Questions? Check the full spec document or logs for debugging.**

