# Phase 2 - Wallet Foundations

**Status:** 🚧 IN PROGRESS  
**Duration:** 8 days  
**Dependencies:** Phase 1 (Auth Baseline)

---

## 🎯 Objectives

Build the foundational wallet management system that supports:
- Platform-managed wallet definitions (admin controlled)
- Secure user credential storage (encrypted)
- User wallet instances with customizable limits
- AI-managed dynamic trading parameters

---

## 📋 Business Requirements

### User Stories

**As a platform administrator, I want to:**
- Define supported wallet types (Binance, Hyperliquid, etc.)
- Specify required credentials for each wallet type
- Configure wallet capabilities (spot, futures, leverage limits)
- Enable/disable wallet types

**As a user, I want to:**
- View available wallet types
- Securely connect my exchange credentials
- Create wallet instances with risk limits
- Set allowed trading symbols
- Pause/resume wallet trading
- See my wallet connection status

**As the system, I need to:**
- Encrypt all user credentials at rest
- Validate credentials match wallet requirements
- Track wallet usage and status
- Allow AI to manage dynamic parameters within user limits

---

## 🗄️ Database Collections

### 1. wallets (Platform Wallet Registry)

**Purpose:** Admin-managed catalog of supported exchanges/wallets

**Schema:**
```python
{
    "_id": ObjectId,
    "name": str,                          # "Binance"
    "slug": str,                          # "binance" (unique, indexed)
    "type": str,                          # "cex" | "dex" | "perpetuals"
    "description": str,
    "logo": str,                          # Optional URL
    
    # Dynamic credential requirements
    "auth_fields": [
        {
            "key": str,                   # "api_key", "api_secret", "private_key"
            "label": str,                 # "API Key" (for UI)
            "type": str,                  # "string" | "password" | "file"
            "required": bool,
            "encrypted": bool,            # Should this field be encrypted?
            "placeholder": str,           # UI hint
            "help_text": str              # User guidance
        }
    ],
    
    # Wallet capabilities
    "features": {
        "spot": bool,
        "futures": bool,
        "perpetuals": bool,
        "leverage": {
            "min": int,                   # e.g., 1
            "max": int                    # e.g., 125
        },
        "supported_assets": [str]         # ["BTC", "ETH", "SOL"]
    },
    
    # API configuration (for backend use)
    "api_config": {
        "base_url": str,
        "testnet_url": str,
        "websocket_url": str,
        "rate_limit": int                 # Requests per minute
    },
    
    "is_active": bool,
    "order": int,                         # Display order in UI
    "created_at": datetime,
    "updated_at": datetime
}
```

**Indexes:**
```python
db.wallets.create_index("slug", unique=True)
db.wallets.create_index([("is_active", 1), ("order", 1)])
```

**Enums:**
```python
WalletType = Literal["cex", "dex", "perpetuals"]
FieldType = Literal["string", "password", "file"]
```

**Seed Data:**
```python
[
    {
        "name": "Binance",
        "slug": "binance",
        "type": "cex",
        "description": "Leading cryptocurrency exchange with spot and futures trading",
        "auth_fields": [
            {
                "key": "api_key",
                "label": "API Key",
                "type": "string",
                "required": True,
                "encrypted": False,
                "placeholder": "Enter your Binance API key",
                "help_text": "Find this in your Binance account settings"
            },
            {
                "key": "api_secret",
                "label": "API Secret",
                "type": "password",
                "required": True,
                "encrypted": True,
                "placeholder": "Enter your API secret",
                "help_text": "Keep this secret and never share it"
            }
        ],
        "features": {
            "spot": True,
            "futures": True,
            "perpetuals": True,
            "leverage": {"min": 1, "max": 125},
            "supported_assets": ["BTC", "ETH", "BNB", "SOL", "USDT"]
        },
        "api_config": {
            "base_url": "https://api.binance.com",
            "testnet_url": "https://testnet.binance.vision",
            "websocket_url": "wss://stream.binance.com:9443",
            "rate_limit": 1200
        },
        "is_active": True,
        "order": 1
    },
    {
        "name": "Hyperliquid",
        "slug": "hyperliquid",
        "type": "perpetuals",
        "description": "Decentralized perpetuals exchange",
        "auth_fields": [
            {
                "key": "private_key",
                "label": "Private Key",
                "type": "password",
                "required": True,
                "encrypted": True,
                "placeholder": "Enter your wallet private key",
                "help_text": "Your Ethereum private key for signing transactions"
            }
        ],
        "features": {
            "spot": False,
            "futures": False,
            "perpetuals": True,
            "leverage": {"min": 1, "max": 50},
            "supported_assets": ["BTC", "ETH", "SOL"]
        },
        "api_config": {
            "base_url": "https://api.hyperliquid.xyz",
            "testnet_url": "https://api.hyperliquid-testnet.xyz",
            "websocket_url": "wss://api.hyperliquid.xyz/ws",
            "rate_limit": 300
        },
        "is_active": True,
        "order": 2
    }
]
```

---

### 2. credentials (User Wallet Credentials)

**Purpose:** Securely store user's exchange API keys/secrets

**Schema:**
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,                  # Reference to users collection
    "wallet_id": ObjectId,                # Reference to wallets collection
    
    "name": str,                          # User-friendly name: "My Main Binance"
    
    # Encrypted credentials (structure matches wallet.auth_fields)
    "credentials": dict,                  # e.g., {"api_key": "plain", "api_secret": "encrypted..."}
    
    # Connection status
    "is_connected": bool,                 # Last connection test result
    "last_verified_at": datetime,         # Last successful connection
    "connection_error": str,              # Latest error message (if any)
    
    "environment": str,                   # "mainnet" | "testnet"
    
    "is_active": bool,
    "created_at": datetime,
    "updated_at": datetime
}
```

**Indexes:**
```python
db.credentials.create_index([("user_id", 1), ("wallet_id", 1)])
db.credentials.create_index([("user_id", 1), ("is_active", 1)])
```

**Enums:**
```python
Environment = Literal["mainnet", "testnet"]
```

**Security Requirements:**
- All fields marked `encrypted=True` in wallet.auth_fields MUST be encrypted
- Use `cryptography.fernet` for encryption
- Encryption key stored in environment variable `ENCRYPTION_KEY`
- Credentials NEVER logged or exposed in API responses
- Only encrypted values stored in database

---

### 3. user_wallets (User Wallet Instances)

**Purpose:** User-configured wallet instances with limits and AI state

**Schema:**
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,                  # Reference to users
    "credential_id": ObjectId,            # Reference to credentials
    "wallet_id": ObjectId,                # Reference to wallets
    
    "name": str,                          # "My Trading Wallet"
    
    # USER-DEFINED LIMITS (immutable by AI)
    "user_limits": {
        "max_total_risk": float,          # USD - Maximum total risk exposure
        "allowed_symbols": [str],         # Optional whitelist: ["BTC/USDT", "ETH/USDT"]
                                          # null = all symbols from wallet.features.supported_assets
        "trading_mode": str               # "conservative" | "moderate" | "aggressive"
    },
    
    # AI-MANAGED STATE (dynamic, updated by AI agents)
    "ai_managed_state": {
        # Current exposure
        "current_risk": float,            # Current USD at risk
        "daily_pnl": float,               # Today's profit/loss
        "open_positions": int,            # Count of open positions
        
        # AI-decided parameters (within user limits)
        "current_max_position_size": float,  # AI's current max per position
        "current_leverage": int,          # AI's current leverage setting
        "adaptive_stop_loss": float,      # % stop loss based on volatility
        
        # AI's market assessment
        "risk_score": int,                # 0-100 (0=safe, 100=extreme risk)
        "market_sentiment": str,          # "bullish" | "bearish" | "neutral" | "uncertain"
        "confidence_level": int,          # 0-100 (AI's confidence in its assessment)
        "last_ai_decision": datetime      # When AI last updated these values
    },
    
    "status": str,                        # "active" | "ai_paused" | "user_paused"
    "created_at": datetime,
    "updated_at": datetime
}
```

**Indexes:**
```python
db.user_wallets.create_index([("user_id", 1), ("status", 1)])
db.user_wallets.create_index("credential_id")
db.user_wallets.create_index("wallet_id")
```

**Enums:**
```python
TradingMode = Literal["conservative", "moderate", "aggressive"]
MarketSentiment = Literal["bullish", "bearish", "neutral", "uncertain"]
WalletStatus = Literal["active", "ai_paused", "user_paused"]
```

**Business Rules:**
1. `allowed_symbols` must be subset of `wallet.features.supported_assets`
2. `credential_id` must reference valid, active credentials
3. Only one wallet instance per credential can be active
4. AI can ONLY modify `ai_managed_state` fields
5. User can modify `user_limits` and `status` only

---

## 🔌 API Endpoints

### Wallet Definitions (Admin)

```python
GET    /api/wallets/definitions
# List all platform wallet definitions
# Auth: Public (for viewing) or Admin (for full details)
# Response: WalletDefinitionListResponse
# Query params: ?type=cex&is_active=true

POST   /api/wallets/definitions
# Create new wallet definition
# Auth: Admin only
# Request: CreateWalletDefinitionRequest
# Response: WalletDefinitionResponse

GET    /api/wallets/definitions/{slug}
# Get wallet definition by slug
# Auth: Public
# Response: WalletDefinitionResponse

PATCH  /api/wallets/definitions/{slug}
# Update wallet definition
# Auth: Admin only
# Request: UpdateWalletDefinitionRequest
# Response: WalletDefinitionResponse

DELETE /api/wallets/definitions/{slug}
# Soft delete wallet definition (set is_active=False)
# Auth: Admin only
# Response: SuccessResponse
```

### User Credentials

```python
POST   /api/wallets/credentials
# Add new wallet credentials
# Auth: User
# Request: CreateCredentialsRequest
# Response: CredentialsResponse (without secrets)

GET    /api/wallets/credentials
# List user's credentials
# Auth: User
# Response: CredentialsListResponse
# Query params: ?wallet_id=xxx&is_active=true

GET    /api/wallets/credentials/{id}
# Get credential details
# Auth: User (own credentials only)
# Response: CredentialsResponse (without secrets)

PATCH  /api/wallets/credentials/{id}
# Update credentials
# Auth: User (own credentials only)
# Request: UpdateCredentialsRequest
# Response: CredentialsResponse

DELETE /api/wallets/credentials/{id}
# Delete credentials
# Auth: User (own credentials only)
# Response: SuccessResponse

POST   /api/wallets/credentials/{id}/test
# Test connection with credentials
# Auth: User (own credentials only)
# Response: ConnectionTestResponse
```

### User Wallets

```python
POST   /api/wallets
# Create user wallet instance
# Auth: User
# Request: CreateUserWalletRequest
# Response: UserWalletResponse

GET    /api/wallets
# List user's wallet instances
# Auth: User
# Response: UserWalletListResponse
# Query params: ?status=active

GET    /api/wallets/{id}
# Get wallet instance details
# Auth: User (own wallets only)
# Response: UserWalletResponse

PATCH  /api/wallets/{id}
# Update wallet limits or name
# Auth: User (own wallets only)
# Request: UpdateUserWalletRequest
# Response: UserWalletResponse

DELETE /api/wallets/{id}
# Delete wallet instance
# Auth: User (own wallets only)
# Response: SuccessResponse

PATCH  /api/wallets/{id}/pause
# Pause wallet trading
# Auth: User (own wallets only)
# Response: UserWalletResponse

PATCH  /api/wallets/{id}/resume
# Resume wallet trading
# Auth: User (own wallets only)
# Response: UserWalletResponse
```

---

## 📦 Implementation Structure

### Module Organization
```
app/modules/
├── wallets/
│   ├── __init__.py
│   ├── models.py           # MongoDB operations for wallet definitions
│   ├── schemas.py          # Pydantic models
│   ├── service.py          # Business logic
│   └── router.py           # API endpoints
│
├── credentials/
│   ├── __init__.py
│   ├── models.py           # MongoDB operations for credentials
│   ├── schemas.py          # Pydantic models
│   ├── service.py          # Business logic (includes encryption)
│   ├── encryption.py       # Encryption utilities
│   └── router.py           # API endpoints
│
└── user_wallets/
    ├── __init__.py
    ├── models.py           # MongoDB operations for user wallets
    ├── schemas.py          # Pydantic models
    ├── service.py          # Business logic
    └── router.py           # API endpoints
```

---

## 🧪 Test-Driven Development Plan

### Day 1-2: Wallet Definitions Module

#### Step 1: Write Tests First (test_wallets.py)
```python
# tests/test_wallets.py

def test_create_wallet_definition_with_valid_data_returns_201(client, admin_auth)
def test_create_wallet_definition_with_duplicate_slug_returns_400(client, admin_auth)
def test_create_wallet_definition_without_auth_returns_401(client)
def test_create_wallet_definition_as_user_returns_403(client, user_auth)

def test_list_wallet_definitions_returns_200(client)
def test_list_wallet_definitions_filters_by_type(client)
def test_list_wallet_definitions_filters_by_is_active(client)

def test_get_wallet_definition_by_slug_returns_200(client)
def test_get_wallet_definition_invalid_slug_returns_404(client)

def test_update_wallet_definition_as_admin_returns_200(client, admin_auth)
def test_update_wallet_definition_as_user_returns_403(client, user_auth)

def test_delete_wallet_definition_as_admin_returns_200(client, admin_auth)
def test_delete_wallet_definition_soft_deletes(client, admin_auth)
```

#### Step 2: Implement Models
```python
# app/modules/wallets/models.py

async def create_wallet(db, wallet_data)
async def find_wallet_by_slug(db, slug, include_inactive=False)
async def list_wallets(db, type=None, is_active=None)
async def update_wallet(db, slug, update_data)
async def soft_delete_wallet(db, slug)
```

#### Step 3: Implement Schemas
```python
# app/modules/wallets/schemas.py

class AuthFieldSchema(BaseModel)
class FeaturesSchema(BaseModel)
class ApiConfigSchema(BaseModel)
class CreateWalletDefinitionRequest(BaseModel)
class UpdateWalletDefinitionRequest(BaseModel)
class WalletDefinitionResponse(BaseModel)
```

#### Step 4: Implement Service
```python
# app/modules/wallets/service.py

async def create_wallet_definition(db, wallet_data, created_by_user_id)
async def get_wallet_definition(db, slug)
async def list_wallet_definitions(db, filters)
async def update_wallet_definition(db, slug, update_data)
async def seed_initial_wallets(db)
```

#### Step 5: Implement Router
```python
# app/modules/wallets/router.py

@router.post("/definitions", response_model=WalletDefinitionResponse)
async def create_wallet_definition(...)

@router.get("/definitions", response_model=List[WalletDefinitionResponse])
async def list_wallet_definitions(...)
```

#### Step 6: Run Tests
```bash
pytest tests/test_wallets.py -v
```

---

### Day 3-5: Credentials Module

#### Step 1: Write Tests First (test_credentials.py)
```python
# tests/test_credentials.py

def test_create_credentials_with_valid_data_returns_201(client, user_auth)
def test_create_credentials_encrypts_secrets(client, user_auth)
def test_create_credentials_validates_against_wallet_auth_fields(client, user_auth)

def test_list_credentials_returns_only_users_credentials(client, user_auth)
def test_list_credentials_does_not_expose_secrets(client, user_auth)

def test_get_credentials_returns_200(client, user_auth)
def test_get_credentials_other_user_returns_403(client, user_auth, other_user_auth)

def test_update_credentials_returns_200(client, user_auth)
def test_update_credentials_re_encrypts_secrets(client, user_auth)

def test_delete_credentials_returns_200(client, user_auth)

def test_test_connection_with_valid_credentials_returns_200(client, user_auth)
def test_test_connection_with_invalid_credentials_returns_400(client, user_auth)
```

#### Step 2: Implement Encryption
```python
# app/modules/credentials/encryption.py

def get_fernet_key() -> bytes
def encrypt_value(value: str) -> str
def decrypt_value(encrypted_value: str) -> str
def encrypt_credentials(credentials: dict, auth_fields: list) -> dict
def decrypt_credentials(credentials: dict, auth_fields: list) -> dict
```

#### Step 3: Implement Models
```python
# app/modules/credentials/models.py

async def create_credentials(db, credentials_data)
async def find_credentials_by_id(db, credentials_id, user_id)
async def list_user_credentials(db, user_id, filters)
async def update_credentials(db, credentials_id, user_id, update_data)
async def delete_credentials(db, credentials_id, user_id)
```

#### Step 4: Implement Service
```python
# app/modules/credentials/service.py

async def create_user_credentials(db, user_id, credentials_data)
async def get_user_credentials(db, user_id, credentials_id)
async def list_user_credentials(db, user_id, filters)
async def update_user_credentials(db, user_id, credentials_id, update_data)
async def delete_user_credentials(db, user_id, credentials_id)
async def test_connection(db, user_id, credentials_id)
```

#### Step 5: Implement Router
#### Step 6: Run Tests

---

### Day 6-8: User Wallets Module

#### Step 1: Write Tests First (test_user_wallets.py)
```python
# tests/test_user_wallets.py

def test_create_user_wallet_with_valid_data_returns_201(client, user_auth)
def test_create_user_wallet_validates_symbols_against_wallet_features(client, user_auth)
def test_create_user_wallet_initializes_ai_managed_state(client, user_auth)

def test_list_user_wallets_returns_200(client, user_auth)
def test_list_user_wallets_filters_by_status(client, user_auth)

def test_get_user_wallet_returns_200(client, user_auth)
def test_get_user_wallet_includes_ai_managed_state(client, user_auth)

def test_update_user_wallet_limits_returns_200(client, user_auth)
def test_update_user_wallet_cannot_modify_ai_managed_state(client, user_auth)

def test_pause_user_wallet_returns_200(client, user_auth)
def test_resume_user_wallet_returns_200(client, user_auth)

def test_delete_user_wallet_returns_200(client, user_auth)
```

#### Step 2-6: Implement (same pattern)

---

## 🔐 Security Implementation

### Encryption Setup
```python
# app/modules/credentials/encryption.py

from cryptography.fernet import Fernet
from app.config.settings import get_settings

def get_fernet_key() -> bytes:
    """Get encryption key from settings."""
    settings = get_settings()
    if not settings.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY not set in environment")
    return settings.ENCRYPTION_KEY.encode()

def encrypt_value(value: str) -> str:
    """Encrypt a single value."""
    f = Fernet(get_fernet_key())
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a single value."""
    f = Fernet(get_fernet_key())
    return f.decrypt(encrypted_value.encode()).decode()

def encrypt_credentials(credentials: dict, auth_fields: list) -> dict:
    """
    Encrypt credentials based on wallet auth_fields specification.
    
    Args:
        credentials: Raw credentials dict
        auth_fields: List of auth field definitions from wallet
        
    Returns:
        dict: Credentials with encrypted fields
    """
    encrypted = {}
    
    for field in auth_fields:
        key = field["key"]
        value = credentials.get(key)
        
        if value is None:
            continue
            
        if field.get("encrypted", False):
            encrypted[key] = encrypt_value(value)
        else:
            encrypted[key] = value
            
    return encrypted
```

### Environment Variable
```bash
# Generate new encryption key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env:
ENCRYPTION_KEY=your-generated-key-here
```

---

## ✅ Success Criteria

Phase 2 is complete when:

- [ ] All three modules implemented (wallets, credentials, user_wallets)
- [ ] All tests passing (>70% coverage)
- [ ] Credentials encryption working
- [ ] Connection testing functional
- [ ] API endpoints documented
- [ ] Admin can seed wallet definitions
- [ ] User can add and manage credentials
- [ ] User can create wallet instances with limits
- [ ] AI managed state structure in place
- [ ] Symbol validation working
- [ ] Pause/resume functionality working
- [ ] Security audit passed

---

## 📚 Reference Implementation

See `Moniqo_BE_FORK/src/` for reference:
- `nice_funcs.py` - Exchange API integration patterns
- `nice_funcs_hyperliquid.py` - Hyperliquid implementation
- `nice_funcs_aster.py` - Aster implementation
- `exchange_manager.py` - Exchange abstraction layer

**DO NOT copy directly** - understand patterns and adapt to our architecture.

---

## 🚀 Next Phase

**Phase 3 - AI Agent Foundations**
- Build AI agent template registry
- User agent instance configuration
- AI provider abstraction
- See [phase-3-ai-agents.md](phase-3-ai-agents.md)

---

*Phase 2 currently in progress. Follow TDD workflow strictly for all implementations.*

