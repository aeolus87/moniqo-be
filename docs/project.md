# 🚀 FastAPI Backend Development Prompt for AI Implementation

You are tasked with building a production-ready **FastAPI backend** for an **AI Agent Trading Platform**. This is a comprehensive, enterprise-grade system that must follow **SOLID principles**, be **highly maintainable**, **extensible**, and **fully tested**.

---

## 📌 WORKSPACE CONTEXT

**Important:** This document aligns with the Moniqo workspace rules and conventions:

- **Project Type:** Scaffold development - building from ground up with comprehensive documentation
- **Active Directory:** `Moniqo_BE/` - All development happens here
- **Reference Directory:** `Moniqo_BE_FORK/` - Read-only reference implementation (never modify)
- **Workspace Rules:** This project follows workspace-level rules for:
  - Code quality and documentation standards
  - Environment variables policy (no hardcoded values)
  - Project structure conventions
  - Git workflow and deployment guidelines
  - Security and testing best practices

**See workspace `.cursorrules` for complete guidelines.**

---

## 📋 CRITICAL DEVELOPMENT RULES

### 🎯 **MANDATORY WORKFLOW - NEVER DEVIATE FROM THIS:**

**FOR EVERY SINGLE FEATURE/MODULE YOU BUILD:**

1. ✅ **WRITE TEST CASES FIRST** (Test-Driven Development)
   - Write **POSITIVE test cases** (happy path scenarios)
   - Write **NEGATIVE test cases** (error scenarios, edge cases, validation failures)
   - Include tests for: authentication, authorization, validation, business logic, error handling
   - Use descriptive test names: `test_create_user_with_valid_data_returns_201()`
   
2. ✅ **THEN IMPLEMENT THE FEATURE**
   - Write the actual implementation that makes tests pass
   - Follow SOLID principles (Single Responsibility, Open/Closed, etc.)
   - Use atomic, single-purpose functions
   - Add detailed docstrings and comments

3. ✅ **RUN TESTS CONTINUOUSLY**
   - Verify all tests pass before moving to next feature
   - Ensure no regression in existing tests

**NEVER write implementation code before writing its tests!**

---

## 🏗️ PROJECT ARCHITECTURE PRINCIPLES

### **Design Patterns:**
- **Feature-based folder structure** (not layer-based)
- **SOLID principles** throughout
- **Atomic functions** - each function does ONE thing well
- **DRY (Don't Repeat Yourself)** - create reusable utilities
- **Open for extension, closed for modification**
- **Dependency Injection** where appropriate
- **Repository pattern** for database operations
- **Service layer** for business logic

### **Code Quality Standards:**
- **Type hints** everywhere (Python 3.11+ style)
- **Docstrings** for all functions/classes (Google style)
- **Comments** explaining WHY, not WHAT
- **Error handling** with custom exceptions
- **Logging** at appropriate levels
- **Validation** using Pydantic
- **No hardcoded values** - use config/env vars

---

## 📁 PROJECT STRUCTURE

**Note:** All development occurs in `Moniqo_BE/` directory. The `Moniqo_BE_FORK/` directory is a reference implementation only - never modify files in that directory.

```
Moniqo_BE/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entry point
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py              # Pydantic settings (load from .env)
│   │   └── database.py              # MongoDB connection setup
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py              # JWT, password hashing, token management
│   │   ├── dependencies.py          # FastAPI dependencies (get_current_user, etc.)
│   │   ├── exceptions.py            # Custom exception classes
│   │   └── responses.py             # Standardized response models
│   │
│   ├── providers/                   # Third-party integrations
│   │   ├── __init__.py
│   │   ├── aws/
│   │   │   ├── __init__.py
│   │   │   ├── config.py           # AWS configuration
│   │   │   └── s3_service.py       # S3 operations (upload, delete, get_url)
│   │   └── resend/
│   │       ├── __init__.py
│   │       ├── config.py           # Resend configuration
│   │       └── email_service.py    # Email operations (send_welcome, send_verification, etc.)
│   │
│   ├── modules/                     # Feature modules
│   │   ├── __init__.py
│   │   │
│   │   ├── auth/                    # Authentication module
│   │   │   ├── __init__.py
│   │   │   ├── models.py           # MongoDB Auth collection model
│   │   │   ├── schemas.py          # Pydantic DTOs (LoginRequest, TokenResponse, etc.)
│   │   │   ├── service.py          # Business logic (register, login, verify_email, etc.)
│   │   │   ├── router.py           # API endpoints (/api/v1/auth/...)
│   │   │   └── dependencies.py     # Auth-specific dependencies
│   │   │
│   │   ├── users/
│   │   │   ├── __init__.py
│   │   │   ├── models.py           # User model
│   │   │   ├── schemas.py          # UserCreate, UserUpdate, UserResponse DTOs
│   │   │   ├── service.py          # User business logic
│   │   │   ├── router.py           # User endpoints
│   │   │   └── dependencies.py
│   │   │
│   │   ├── roles/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   │
│   │   ├── permissions/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   │
│   │   ├── plans/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   │
│   │   ├── notifications/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   │
│   │   └── [PHASE 2 MODULES - Create base structure with placeholders]
│   │       ├── wallets/
│   │       ├── agents/
│   │       ├── prompts/
│   │       ├── user_wallets/
│   │       ├── user_plans/
│   │       ├── user_settings/
│   │       ├── user_trades/
│   │       ├── user_flows/
│   │       └── user_prompts/
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── cache.py                # Redis caching utilities
│   │   ├── logger.py               # Logging configuration
│   │   ├── pagination.py           # Pagination helpers (limit/offset)
│   │   └── validators.py           # Custom validators
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── rate_limiter.py         # Rate limiting (100/min per user, unlimited for admins)
│   │   ├── logging_middleware.py   # Request/response logging
│   │   └── error_handler.py        # Global error handling
│   │
│   └── tasks/                      # Background tasks (using FastAPI BackgroundTasks)
│       ├── __init__.py
│       ├── email_tasks.py          # Async email sending functions
│       └── notification_tasks.py   # Async notification functions
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   ├── test_auth.py                # Auth module tests
│   ├── test_users.py               # User module tests
│   ├── test_roles.py
│   ├── test_permissions.py
│   ├── test_plans.py
│   ├── test_notifications.py
│   └── ...
│
├── scripts/
│   ├── init_superadmin.py          # Create superadmin on startup
│   └── init_default_data.py        # Create default roles/permissions/free plan
│
├── .env.example                    # Environment variables template
├── .gitignore
├── requirements.txt                # Python dependencies
├── docker-compose.yml              # Docker setup (see workspace docker-deployment rules)
├── Dockerfile                      # Production container definition
└── README.md
```

**Deployment Note:** This project follows workspace-level Docker and deployment guidelines. See workspace `.cursorrules` `docker-deployment` rule for container setup and deployment best practices.

---

## 🗄️ DATABASE MODELS & RELATIONSHIPS

### **Technology Stack:**
- **Database:** MongoDB
- **ODM:** Motor (async) + Beanie (async ODM)
- **Relationships:** Use ObjectId references (normalized) with proper indexing

### **Collections:**

#### **1. Auth Collection**
```python
{
    "_id": ObjectId,
    "email": str,              # Unique, indexed, lowercase
    "password_hash": str,      # Bcrypt hashed
    "is_verified": bool,       # Can auto-verify via ENV: AUTO_VERIFY_EMAIL
    "is_active": bool,         # For account suspension
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool,        # Soft delete
}
```

#### **2. Users Collection**
```python
{
    "_id": ObjectId,
    "auth_id": ObjectId,       # Reference to auth collection
    "first_name": str,
    "last_name": str,
    "birthday": {
        "day": int,            # 1-31
        "month": int,          # 1-12
        "year": int            # e.g., 1990
    },
    "avatar_url": str | None,  # Default: generate from first_name[0]
    "phone_number": {
        "country_code": str | None,  # e.g., "+63"
        "mobile_number": str | None  # If country_code exists, mobile_number is required (and vice versa)
    },
    "user_role": ObjectId,     # Reference to roles collection (one-to-one)
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

**Validation Rules:**
- `phone_number`: If `country_code` is provided, `mobile_number` is required (and vice versa)
- `avatar_url`: If null, generate default avatar with first letter of `first_name`

#### **3. Roles Collection**
```python
{
    "_id": ObjectId,
    "name": str,               # Unique (e.g., "Admin", "User")
    "description": str,
    "permissions": [ObjectId], # Array of permission IDs (many-to-many)
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

**Initial Roles (created by init script):**
- `Admin` (all permissions)
- `User` (limited permissions)

#### **4. Permissions Collection**
```python
{
    "_id": ObjectId,
    "resource": str,           # e.g., "users", "plans", "agents"
    "action": str,             # e.g., "read", "write", "delete"
    "description": str,
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

**Permission Format:** `{resource}:{action}` (e.g., `users:read`, `users:write`, `plans:create`)

**Initial Permissions (created by init script):**
- `users:read`, `users:write`, `users:delete`
- `roles:read`, `roles:write`, `roles:delete`
- `permissions:read`, `permissions:write`, `permissions:delete`
- `plans:read`, `plans:write`, `plans:delete`
- (Add more as needed)

#### **5. Plans Collection**
```python
{
    "_id": ObjectId,
    "name": str,               # "Free", "Pro", "Enterprise"
    "description": str,
    "price": float,            # Monthly price
    "features": [
        {
            "resource": str,   # Related to permissions
            "title": str,
            "description": str
        }
    ],
    "limits": [
        {
            "resource": str,   # e.g., "api_calls", "agents", "trades_per_day"
            "title": str,
            "description": str,
            "value": int       # Limit value
        }
    ],
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

**Default Plan:** Create a "Free" plan on init

#### **6. User_Plans Collection**
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,       # Reference to users (one-to-many)
    "plan_id": ObjectId,       # Reference to plans
    "status": str,             # "active", "expired", "cancelled"
    "start_date": datetime,
    "end_date": datetime | None,
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

**Note:** A user can have multiple plans over time

#### **7. Notifications Collection**
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,       # Reference to users
    "notifications": [
        {
            "title": str,
            "description": str,
            "created_at": datetime,
            "is_viewed": bool
        }
    ],
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

---

## 🔧 PHASE 2 MODELS (Abstracted Base Structures)

**For these collections, create:**
1. **Base model structure** with common fields
2. **Placeholder comments** for domain-specific fields
3. **CRUD operations** that work with the base structure
4. **Extensibility** for future enhancements

#### **8. Wallets Collection** (Provider-agnostic)
```python
{
    "_id": ObjectId,
    "name": str,               # "Binance", "Coinbase", "MetaMask"
    "type": str,               # "CEX", "DEX", "Wallet"
    "provider": str,           # Provider identifier
    "supported_currencies": [str],  # ["BTC", "ETH", "USDT"]
    "config": dict,            # Provider-specific config (flexible)
    # TODO: Add provider-specific fields as needed
    "is_active": bool,
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

#### **9. Agents Collection** (AI model agnostic)
```python
{
    "_id": ObjectId,
    "name": str,               # "GPT-4", "Claude Sonnet"
    "provider": str,           # "OpenAI", "Anthropic", "DeepSeek"
    "model_id": str,           # "gpt-4-turbo", "claude-sonnet-4"
    "capabilities": [str],     # ["trading", "analysis", "prediction"]
    "cost_per_call": float,
    "config": dict,            # Provider-specific config (flexible)
    # TODO: Add provider-specific fields as needed
    "is_active": bool,
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

#### **10. Prompts Collection**
```python
{
    "_id": ObjectId,
    "title": str,
    "description": str,
    "prompt": str,             # The actual prompt text
    "category": str,           # "trading", "analysis", "risk_management"
    "is_public": bool,         # Public templates vs private
    "created_by": ObjectId | None,  # User who created (if custom)
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

#### **11. User_Flows Collection** (Automation workflows)
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "title": str,
    "description": str,
    "flow": [
        {
            "step": int,       # 0, 1, 2, ... (execution order)
            "prompt_id": ObjectId,  # Reference to prompts
            "agent_id": ObjectId,   # Reference to agents
            "config": dict     # Step-specific configuration
        }
    ],
    "status": str,             # "active", "paused", "stopped"
    "last_run": datetime | None,
    # TODO: Add execution history, error logs, etc.
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

#### **12. User_Trades Collection**
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "flow_id": ObjectId | None,     # If trade was from a flow
    "agent_id": ObjectId | None,    # Which agent executed
    "trade_type": str,              # "crypto", "forex"
    "symbol": str,                  # "BTC/USDT", "EUR/USD"
    "side": str,                    # "buy", "sell"
    "entry_price": float,
    "exit_price": float | None,
    "quantity": float,
    "leverage": int,
    "profit_loss": float | None,
    "status": str,                  # "open", "closed", "cancelled"
    "executed_at": datetime,
    "closed_at": datetime | None,
    # TODO: Add fees, slippage, exchange, etc.
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

#### **13. User_Wallets Collection**
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "wallet_id": ObjectId,         # Reference to wallets
    "credentials": dict,           # Encrypted API keys, addresses, etc.
    "balance": float,              # Cached balance
    "is_active": bool,
    # TODO: Add balance history, transaction logs, etc.
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

#### **14. User_Prompts Collection**
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "prompt_id": ObjectId | None,  # If based on a template
    "title": str,
    "description": str,
    "prompt": str,                 # Custom prompt text
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

#### **15. User_Settings Collection**
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,           # One-to-one with users
    "preferences": dict,           # Flexible settings structure
    "notifications_enabled": bool,
    "email_notifications": bool,
    "theme": str,                  # "light", "dark"
    # TODO: Add more settings as needed
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool
}
```

---

## ⚙️ CONFIGURATION & ENVIRONMENT VARIABLES

**Important:** This project follows the workspace-level environment variables policy:
- **NEVER hardcode** any configuration values in code
- **ALWAYS use** environment variables for all settings
- Create `.env.example` with placeholder values (commit this)
- Create `.env` with actual values (NEVER commit this)
- See workspace `.cursorrules` for detailed policy

### **.env.example** (Create this file)
```ini
# App Configuration
APP_NAME=AI Agent Trading Platform
APP_VERSION=1.0.0
ENVIRONMENT=development  # development, staging, production
DEBUG=True

# Server
HOST=0.0.0.0
PORT=8000

# Database
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=ai_trading_platform

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_TTL_SECONDS=86400  # 1 day

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email Auto-Verification
AUTO_VERIFY_EMAIL=False  # Set to True to skip email verification

# Superadmin
SUPERADMIN_EMAIL=admin@example.com
SUPERADMIN_PASSWORD=SuperSecurePassword123!
SUPERADMIN_FIRST_NAME=Super
SUPERADMIN_LAST_NAME=Admin

# AWS S3
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
AWS_S3_BUCKET_NAME=your-bucket-name

# File Upload Limits
MAX_AVATAR_SIZE_MB=5
ALLOWED_AVATAR_TYPES=image/jpeg,image/png,image/gif

# Resend Email
RESEND_API_KEY=your-resend-api-key
FROM_EMAIL=noreply@yourdomain.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100  # Per user
ADMIN_RATE_LIMIT_ENABLED=False  # Admins have unlimited

# Pagination
DEFAULT_PAGE_SIZE=10
MAX_PAGE_SIZE=5000

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE_PATH=logs/app.log

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Background Tasks
# Note: Using FastAPI BackgroundTasks (no broker needed)
# If upgrading to Celery later, uncomment:
# CELERY_BROKER_URL=redis://localhost:6379/1
# CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

---

## 🔐 AUTHENTICATION & AUTHORIZATION

### **Authentication Flow:**
1. **Registration**
   - POST `/api/v1/auth/register`
   - Create auth + user records
   - Send verification email (if AUTO_VERIFY_EMAIL=False)
   - Assign default "User" role
   - Assign default "Free" plan

2. **Email Verification**
   - GET `/api/v1/auth/verify-email?token={token}`
   - Verify JWT token
   - Set `is_verified=True` in auth collection

3. **Login**
   - POST `/api/v1/auth/login`
   - Verify email + password
   - Return access_token + refresh_token

4. **Token Refresh**
   - POST `/api/v1/auth/refresh`
   - Verify refresh_token
   - Return new access_token

5. **Password Reset**
   - POST `/api/v1/auth/forgot-password` → Send reset email
   - POST `/api/v1/auth/reset-password` → Reset with token

### **Authorization (RBAC):**
- **Dependency:** `require_permission(resource: str, action: str)`
- **Usage in routes:**
```python
@router.get("/users", dependencies=[Depends(require_permission("users", "read"))])
async def list_users():
    pass
```

- **Permission Check Flow:**
  1. Extract user from JWT token
  2. Get user's role
  3. Get role's permissions
  4. Check if `{resource}:{action}` exists in permissions
  5. Raise 403 if not authorized

---

## 🚀 API ENDPOINTS STRUCTURE

### **Versioning:** All endpoints under `/api/v1/`

### **Standardized Response Format (MANDATORY):**
```python
{
    "status_code": int,        # HTTP status code (200, 201, 400, etc.)
    "message": str,            # Human-readable message
    "data": Any | None,        # Response data (null on error)
    "error": {                 # Only present on error
        "code": str,           # Error code (e.g., "VALIDATION_ERROR")
        "message": str         # Detailed error message
    } | None
}
```

### **Example Success Response:**
```json
{
    "status_code": 201,
    "message": "User created successfully",
    "data": {
        "id": "507f1f77bcf86cd799439011",
        "email": "user@example.com",
        "first_name": "John"
    },
    "error": null
}
```

### **Example Error Response:**
```json
{
    "status_code": 400,
    "message": "Validation failed",
    "data": null,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Email is already registered"
    }
}
```

---

## 📝 PAGINATION

### **Request:**
- Query params: `?limit=10&offset=0`
- Default: `limit=10` (from env: DEFAULT_PAGE_SIZE)
- Max: `limit=5000` (from env: MAX_PAGE_SIZE)

### **Response:**
```json
{
    "status_code": 200,
    "message": "Users retrieved successfully",
    "data": {
        "items": [...],
        "total": 150,
        "limit": 10,
        "offset": 0,
        "has_more": true
    },
    "error": null
}
```

---

## 🔄 CACHING WITH REDIS

### **Cache Strategy:**
- Cache GET requests for list/detail endpoints
- TTL: 1 day max (configurable via REDIS_TTL_SECONDS)
- Cache key format: `{module}:{operation}:{params_hash}`
- Invalidate cache on CREATE/UPDATE/DELETE operations

### **Example:**
```python
# Cache key: "users:list:limit=10&offset=0"
# TTL: 86400 seconds (1 day)
```

### **Utilities (utils/cache.py):**
```python
async def get_cache(key: str) -> Any | None
async def set_cache(key: str, value: Any, ttl: int = None) -> None
async def delete_cache(key: str) -> None
async def delete_cache_pattern(pattern: str) -> None  # e.g., "users:*"
```

---

## 🛡️ RATE LIMITING

### **Rules:**
- **Regular users:** 100 requests/minute (from env: RATE_LIMIT_PER_MINUTE)
- **Admins:** Unlimited (if ADMIN_RATE_LIMIT_ENABLED=False)

### **Implementation:**
- Use Redis for rate limit counters
- Key format: `rate_limit:{user_id}:{minute}`
- Return 429 (Too Many Requests) when exceeded

---

## 📧 EMAIL INTEGRATION (Resend)

### **Email Types:**
1. **Welcome Email** - Sent on registration
2. **Verification Email** - Email verification link
3. **Password Reset Email** - Password reset link
4. **Notification Email** - For background notifications (future)

### **Email Service (providers/resend/email_service.py):**
```python
async def send_welcome_email(email: str, first_name: str)
async def send_verification_email(email: str, token: str)
async def send_password_reset_email(email: str, token: str)
async def send_notification_email(email: str, title: str, body: str)
```

---

## 📁 FILE UPLOAD (AWS S3)

### **Avatar Upload:**
- Endpoint: POST `/api/v1/users/avatar`
- Max size: 5MB (from env: MAX_AVATAR_SIZE_MB)
- Allowed types: JPEG, PNG, GIF (from env: ALLOWED_AVATAR_TYPES)
- S3 path: `avatars/{user_id}/{timestamp}_{filename}`

### **S3 Service (providers/aws/s3_service.py):**
```python
async def upload_file(file: UploadFile, folder: str) -> str  # Returns S3 URL
async def delete_file(file_url: str) -> bool
async def generate_presigned_url(file_key: str, expiration: int = 3600) -> str
```

---

## 🧪 TESTING REQUIREMENTS

### **Testing Framework:**
- **pytest** + **pytest-asyncio** + **httpx** (for async testing)
- **Coverage:** Aim for 80%+ code coverage

### **Test Structure (for EVERY module):**

#### **1. Positive Test Cases (Happy Path)**
```python
async def test_create_user_with_valid_data_returns_201()
async def test_login_with_valid_credentials_returns_tokens()
async def test_get_user_by_id_returns_user_data()
async def test_update_user_with_valid_data_returns_updated_user()
async def test_delete_user_soft_deletes_user()
async def test_list_users_returns_paginated_results()
async def test_admin_can_create_role()
async def test_superadmin_can_access_all_endpoints()
```

#### **2. Negative Test Cases (Error Scenarios)**
```python
async def test_create_user_with_duplicate_email_returns_400()
async def test_create_user_with_invalid_email_returns_422()
async def test_login_with_wrong_password_returns_401()
async def test_access_protected_route_without_token_returns_401()
async def test_access_forbidden_route_returns_403()
async def test_create_user_with_missing_required_fields_returns_422()
async def test_get_nonexistent_user_returns_404()
async def test_update_user_with_invalid_data_returns_422()
async def test_phone_number_without_country_code_returns_422()
async def test_exceed_rate_limit_returns_429()
async def test_upload_oversized_avatar_returns_413()
async def test_upload_invalid_file_type_returns_422()
```

#### **3. Edge Cases**
```python
async def test_pagination_with_limit_exceeding_max_uses_max_limit()
async def test_soft_deleted_users_not_returned_in_list()
async def test_cache_invalidation_after_update()
async def test_token_expiration_returns_401()
```

### **Test Fixtures (tests/conftest.py):**
```python
@pytest.fixture
async def test_client() -> AsyncClient

@pytest.fixture
async def test_db() -> AsyncIOMotorDatabase

@pytest.fixture
async def superadmin_token() -> str

@pytest.fixture
async def regular_user_token() -> str

@pytest.fixture
async def test_user_data() -> dict
```

---

## 🪵 LOGGING

### **Log Levels:**
- **Development:** DEBUG (detailed logs)
- **Production:** INFO (minimal logs, no sensitive data)

### **What to Log:**
- API requests (method, path, user_id, IP)
- API responses (status_code, execution_time)
- Errors (with stack traces)
- Auth events (login, logout, failed attempts)
- Database operations (slow queries)
- Background task execution

### **Log Format:**
```
[2025-11-02 10:30:45] [INFO] [auth.service] User login successful: user_id=123, ip=192.168.1.1
[2025-11-02 10:31:12] [ERROR] [users.service] Failed to create user: ValidationError: Email already exists
```

### **Implementation:**
- Use Python's `logging` module
- Rotate log files daily
- Store in `logs/` directory
- DO NOT log passwords, tokens, or sensitive data

---

## 🔄 BACKGROUND TASKS

### **Implementation:** Use **FastAPI's built-in BackgroundTasks**

FastAPI provides a simple way to run background tasks without complex queue systems. For this project, we'll use the lightweight `BackgroundTasks` feature.

### **Usage Pattern:**
```python
from fastapi import BackgroundTasks

@router.post("/register")
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks
):
    # Create user
    user = await create_user(user_data)
    
    # Add background task to send email (non-blocking)
    background_tasks.add_task(send_welcome_email, user.email, user.first_name)
    
    return {"message": "User created successfully"}
```

### **Task Functions (app/tasks/):**

1. **Email Tasks (email_tasks.py)**
   ```python
   async def send_welcome_email(email: str, first_name: str):
       """Send welcome email in background."""
       await email_service.send_welcome_email(email, first_name)
   
   async def send_verification_email(email: str, token: str):
       """Send verification email in background."""
       await email_service.send_verification_email(email, token)
   
   async def send_password_reset_email(email: str, token: str):
       """Send password reset email in background."""
       await email_service.send_password_reset_email(email, token)
   ```

2. **Notification Tasks (notification_tasks.py)**
   ```python
   async def create_notification(user_id: ObjectId, title: str, description: str):
       """Create notification in background."""
       await notification_service.create_notification(user_id, title, description)
   
   async def send_notification_email(user_id: ObjectId, notification_id: ObjectId):
       """Send notification email in background."""
       notification = await get_notification(notification_id)
       user = await get_user(user_id)
       await email_service.send_notification_email(user.email, notification.title, notification.description)
   ```

### **Future Tasks (placeholder):**
- Process trades
- Execute flows
- Sync wallet balances

**Note:** For more complex scenarios requiring task scheduling, retries, or distributed processing, consider upgrading to Celery or ARQ later.

---

## 🚦 INITIALIZATION SCRIPTS

### **scripts/init_superadmin.py**

```python
"""
Create superadmin account on first startup.
Run this script on application startup (in main.py).
"""

async def init_superadmin():
    """
    Creates superadmin account if it doesn't exist.
    Uses credentials from environment variables.
    """
    # Check if superadmin already exists
    # If not, create:
    #   1. Auth record with SUPERADMIN_EMAIL, hashed SUPERADMIN_PASSWORD
    #   2. User record with SUPERADMIN_FIRST_NAME, SUPERADMIN_LAST_NAME
    #   3. Assign "Admin" role (create if doesn't exist)
    #   4. Set is_verified=True, is_active=True
```

### **scripts/init_default_data.py**
```python
"""
Initialize default roles, permissions, and plans.
Run this on first startup.
"""

async def init_default_roles():
    """
    Create default roles:
    - Admin (all permissions)
    - User (limited permissions)
    """
    pass

async def init_default_permissions():
    """
    Create default permissions:
    - users:read, users:write, users:delete
    - roles:read, roles:write, roles:delete
    - permissions:read, permissions:write, permissions:delete
    - plans:read, plans:write, plans:delete
    - agents:read, agents:write, agents:execute
    - trades:read, trades:write
    - flows:read, flows:write, flows:execute
    - wallets:read, wallets:write
    - prompts:read, prompts:write
    """
    pass

async def init_default_plans():
    """
    Create default "Free" plan:
    - name: "Free"
    - description: "Free tier for new users"
    - price: 0.0
    - features: Basic features
    - limits: Basic limits (e.g., 100 API calls/day, 1 agent, 10 trades/day)
    """
    pass
```

---

## 📦 DEPENDENCIES (requirements.txt)

```txt
# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
motor==3.3.2  # Async MongoDB driver
pymongo==4.6.0

# Authentication & Security
python-jose[cryptography]==3.3.0  # JWT
passlib[bcrypt]==1.7.4  # Password hashing
bcrypt==3.2.2  # Required for passlib bcrypt backend

# Redis (for caching and rate limiting)
redis==5.0.1

# AWS S3
boto3==1.34.10

# Email (Resend)
resend==0.8.0

# Background Tasks
# Note: Using FastAPI's built-in BackgroundTasks (no external dependencies needed)
# For more complex scenarios, consider: celery==5.3.4 or arq==0.25.0

# Validation & Serialization
pydantic==2.5.0
pydantic-core==2.14.1
email-validator==2.1.0
annotated-types==0.7.0

# HTTP Client
httptools==0.7.1  # For uvicorn performance

# Async Support
anyio==3.7.1
sniffio==1.3.1

# Web Sockets
websockets==15.0.1

# Utilities
python-dotenv==1.0.0
pyyaml==6.0.3
dnspython==2.8.0  # For MongoDB srv connections
click==8.3.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2  # For testing async endpoints
faker==20.1.0  # For generating test data

# Development Tools
black==23.12.0  # Code formatting
flake8==6.1.0  # Linting
mypy==1.7.1  # Type checking
```

**Note:** The dependencies listed above match the current virtual environment setup. Update versions as needed for your deployment.

---

## 🎯 PHASE 1 IMPLEMENTATION CHECKLIST

### **Step 1: Project Setup**
- [ ] Create project structure (all folders)
- [ ] Create `.env.example`
- [ ] Create `requirements.txt`
- [ ] Initialize Git repository with `.gitignore`

### **Step 2: Core Infrastructure**
- [ ] **config/settings.py** - Load environment variables
- [ ] **config/database.py** - MongoDB connection setup
- [ ] **core/responses.py** - Standardized response models
- [ ] **core/exceptions.py** - Custom exception classes
- [ ] **utils/logger.py** - Logging configuration
- [ ] **utils/cache.py** - Redis caching utilities
- [ ] **utils/pagination.py** - Pagination helpers

### **Step 3: Providers**
- [ ] **providers/aws/config.py** - AWS configuration
- [ ] **providers/aws/s3_service.py** - S3 upload/delete/presigned URL
- [ ] **providers/resend/config.py** - Resend configuration
- [ ] **providers/resend/email_service.py** - Email sending functions

### **Step 4: Auth Module (TDD)**
**WRITE TESTS FIRST:**
- [ ] Write positive test cases for auth
- [ ] Write negative test cases for auth
- [ ] Write edge case tests

**THEN IMPLEMENT:**
- [ ] **modules/auth/models.py** - Auth MongoDB model
- [ ] **modules/auth/schemas.py** - Pydantic DTOs
- [ ] **core/security.py** - JWT, password hashing
- [ ] **modules/auth/service.py** - Auth business logic
- [ ] **modules/auth/router.py** - Auth endpoints
- [ ] **core/dependencies.py** - `get_current_user` dependency

**ENDPOINTS:**
- [ ] POST `/api/v1/auth/register` - User registration
- [ ] POST `/api/v1/auth/login` - User login
- [ ] POST `/api/v1/auth/refresh` - Refresh token
- [ ] POST `/api/v1/auth/logout` - Logout (invalidate token)
- [ ] GET `/api/v1/auth/verify-email?token={token}` - Email verification
- [ ] POST `/api/v1/auth/forgot-password` - Request password reset
- [ ] POST `/api/v1/auth/reset-password` - Reset password with token

### **Step 5: Users Module (TDD)**
**WRITE TESTS FIRST:**
- [ ] Write positive test cases for users
- [ ] Write negative test cases for users
- [ ] Write edge case tests

**THEN IMPLEMENT:**
- [ ] **modules/users/models.py** - User MongoDB model
- [ ] **modules/users/schemas.py** - Pydantic DTOs
- [ ] **modules/users/service.py** - User business logic
- [ ] **modules/users/router.py** - User endpoints

**ENDPOINTS:**
- [ ] GET `/api/v1/users/me` - Get current user
- [ ] PUT `/api/v1/users/me` - Update current user
- [ ] DELETE `/api/v1/users/me` - Soft delete current user
- [ ] POST `/api/v1/users/me/avatar` - Upload avatar
- [ ] DELETE `/api/v1/users/me/avatar` - Delete avatar
- [ ] GET `/api/v1/users` - List users (admin only, paginated)
- [ ] GET `/api/v1/users/{user_id}` - Get user by ID (admin only)
- [ ] PUT `/api/v1/users/{user_id}` - Update user (admin only)
- [ ] DELETE `/api/v1/users/{user_id}` - Soft delete user (admin only)

### **Step 6: Permissions Module (TDD)**
**WRITE TESTS FIRST:**
- [ ] Write positive test cases for permissions
- [ ] Write negative test cases for permissions
- [ ] Write edge case tests

**THEN IMPLEMENT:**
- [ ] **modules/permissions/models.py** - Permission MongoDB model
- [ ] **modules/permissions/schemas.py** - Pydantic DTOs
- [ ] **modules/permissions/service.py** - Permission business logic
- [ ] **modules/permissions/router.py** - Permission endpoints

**ENDPOINTS:**
- [ ] GET `/api/v1/permissions` - List permissions (paginated)
- [ ] GET `/api/v1/permissions/{permission_id}` - Get permission by ID
- [ ] POST `/api/v1/permissions` - Create permission (superadmin only)
- [ ] PUT `/api/v1/permissions/{permission_id}` - Update permission (superadmin only)
- [ ] DELETE `/api/v1/permissions/{permission_id}` - Soft delete permission (superadmin only)

### **Step 7: Roles Module (TDD)**
**WRITE TESTS FIRST:**
- [ ] Write positive test cases for roles
- [ ] Write negative test cases for roles
- [ ] Write edge case tests

**THEN IMPLEMENT:**
- [ ] **modules/roles/models.py** - Role MongoDB model
- [ ] **modules/roles/schemas.py** - Pydantic DTOs
- [ ] **modules/roles/service.py** - Role business logic
- [ ] **modules/roles/router.py** - Role endpoints
- [ ] **core/dependencies.py** - Add `require_permission` dependency

**ENDPOINTS:**
- [ ] GET `/api/v1/roles` - List roles (paginated)
- [ ] GET `/api/v1/roles/{role_id}` - Get role by ID
- [ ] POST `/api/v1/roles` - Create role (superadmin only)
- [ ] PUT `/api/v1/roles/{role_id}` - Update role (superadmin only)
- [ ] DELETE `/api/v1/roles/{role_id}` - Soft delete role (superadmin only)
- [ ] POST `/api/v1/roles/{role_id}/permissions` - Add permissions to role
- [ ] DELETE `/api/v1/roles/{role_id}/permissions/{permission_id}` - Remove permission from role

### **Step 8: Plans Module (TDD)**
**WRITE TESTS FIRST:**
- [ ] Write positive test cases for plans
- [ ] Write negative test cases for plans
- [ ] Write edge case tests

**THEN IMPLEMENT:**
- [ ] **modules/plans/models.py** - Plan MongoDB model
- [ ] **modules/plans/schemas.py** - Pydantic DTOs
- [ ] **modules/plans/service.py** - Plan business logic
- [ ] **modules/plans/router.py** - Plan endpoints

**ENDPOINTS:**
- [ ] GET `/api/v1/plans` - List plans (public)
- [ ] GET `/api/v1/plans/{plan_id}` - Get plan by ID (public)
- [ ] POST `/api/v1/plans` - Create plan (admin only)
- [ ] PUT `/api/v1/plans/{plan_id}` - Update plan (admin only)
- [ ] DELETE `/api/v1/plans/{plan_id}` - Soft delete plan (admin only)

### **Step 9: User_Plans Module (TDD)**
**WRITE TESTS FIRST:**
- [ ] Write positive test cases for user_plans
- [ ] Write negative test cases for user_plans
- [ ] Write edge case tests

**THEN IMPLEMENT:**
- [ ] **modules/user_plans/models.py** - User_Plan MongoDB model
- [ ] **modules/user_plans/schemas.py** - Pydantic DTOs
- [ ] **modules/user_plans/service.py** - User_Plan business logic
- [ ] **modules/user_plans/router.py** - User_Plan endpoints

**ENDPOINTS:**
- [ ] GET `/api/v1/users/me/plans` - Get current user's plans
- [ ] POST `/api/v1/users/me/plans` - Subscribe to a plan
- [ ] PUT `/api/v1/users/me/plans/{user_plan_id}` - Update subscription status
- [ ] DELETE `/api/v1/users/me/plans/{user_plan_id}` - Cancel subscription

### **Step 10: Notifications Module (TDD)**
**WRITE TESTS FIRST:**
- [ ] Write positive test cases for notifications
- [ ] Write negative test cases for notifications
- [ ] Write edge case tests

**THEN IMPLEMENT:**
- [ ] **modules/notifications/models.py** - Notification MongoDB model
- [ ] **modules/notifications/schemas.py** - Pydantic DTOs
- [ ] **modules/notifications/service.py** - Notification business logic
- [ ] **modules/notifications/router.py** - Notification endpoints

**ENDPOINTS:**
- [ ] GET `/api/v1/notifications` - Get current user's notifications
- [ ] PUT `/api/v1/notifications/{notification_id}/view` - Mark notification as viewed
- [ ] DELETE `/api/v1/notifications/{notification_id}` - Delete notification

### **Step 11: Middleware**
- [ ] **middleware/rate_limiter.py** - Rate limiting (100/min users, unlimited admins)
- [ ] **middleware/logging_middleware.py** - Request/response logging
- [ ] **middleware/error_handler.py** - Global error handling

### **Step 12: Background Tasks**
- [ ] **tasks/email_tasks.py** - Email sending task functions (using FastAPI BackgroundTasks)
- [ ] **tasks/notification_tasks.py** - Notification task functions (using FastAPI BackgroundTasks)
- [ ] Update routers to use `BackgroundTasks` dependency for async operations

### **Step 13: Initialization Scripts**
- [ ] **scripts/init_superadmin.py** - Create superadmin on startup
- [ ] **scripts/init_default_data.py** - Create default roles/permissions/plans
- [ ] Update **main.py** to run init scripts on startup

### **Step 14: Main Application**
- [ ] **main.py** - FastAPI app setup
  - [ ] Include all routers
  - [ ] Add middleware
  - [ ] Setup CORS
  - [ ] Run initialization scripts
  - [ ] Setup lifespan events (startup/shutdown)

---

## 🔮 PHASE 2 IMPLEMENTATION (Abstracted Base Modules)

For each module below, create:
1. **Base model structure** with common fields
2. **CRUD endpoints** (Create, Read, Update, Delete, List)
3. **Placeholder comments** for domain-specific fields
4. **Tests** (positive, negative, edge cases)
5. **Documentation** explaining extensibility

### **Modules to Create:**
- [ ] **modules/wallets/** - Wallet provider management (abstracted)
- [ ] **modules/agents/** - AI agent/model management (abstracted)
- [ ] **modules/prompts/** - AI prompt templates
- [ ] **modules/user_wallets/** - User's connected wallets
- [ ] **modules/user_settings/** - User preferences/settings
- [ ] **modules/user_trades/** - User's trade history
- [ ] **modules/user_flows/** - User's automation workflows
- [ ] **modules/user_prompts/** - User's custom prompts

---

## 📝 CODE QUALITY STANDARDS

### **1. Type Hints (MANDATORY)**
```python
# ✅ CORRECT
async def create_user(user_data: UserCreate, db: AsyncIOMotorDatabase) -> User:
    pass

# ❌ INCORRECT
async def create_user(user_data, db):
    pass
```

### **2. Docstrings (Google Style)**
```python
async def create_user(user_data: UserCreate, db: AsyncIOMotorDatabase) -> User:
    """
    Creates a new user in the database.
    
    Args:
        user_data: User creation data (validated)
        db: MongoDB database instance
        
    Returns:
        User: Newly created user object
        
    Raises:
        DuplicateEmailError: If email already exists
        ValidationError: If data validation fails
    """
    pass
```

### **3. Error Handling**
```python
# ✅ CORRECT - Use custom exceptions
from app.core.exceptions import DuplicateEmailError

async def create_user(user_data: UserCreate) -> User:
    existing_user = await find_user_by_email(user_data.email)
    if existing_user:
        raise DuplicateEmailError(f"Email {user_data.email} already registered")
    # ... create user

# ❌ INCORRECT - Generic exceptions
async def create_user(user_data: UserCreate) -> User:
    existing_user = await find_user_by_email(user_data.email)
    if existing_user:
        raise Exception("Email exists")  # Too generic!
```

### **4. Logging**
```python
# ✅ CORRECT
logger.info(f"User created successfully: user_id={user.id}, email={user.email}")
logger.error(f"Failed to create user: {str(e)}", exc_info=True)

# ❌ INCORRECT - No context
logger.info("User created")
logger.error("Error")
```

### **5. Atomic Functions**
```python
# ✅ CORRECT - Single responsibility
async def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)

# ❌ INCORRECT - Multiple responsibilities
async def handle_password(password: str, action: str, hashed: str = None):
    if action == "hash":
        return pwd_context.hash(password)
    elif action == "verify":
        return pwd_context.verify(password, hashed)
```

### **6. Validation with Pydantic**
```python
# ✅ CORRECT - Use Pydantic validators
from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
    
    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: dict) -> dict:
        """Ensure country_code and mobile_number are both present or both absent."""
        country_code = v.get("country_code")
        mobile_number = v.get("mobile_number")
        
        if (country_code and not mobile_number) or (mobile_number and not country_code):
            raise ValueError("Both country_code and mobile_number must be provided together")
        
        return v
```

### **7. Repository Pattern**
```python
# ✅ CORRECT - Separate data access from business logic

# In models.py or repository.py
class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["users"]
    
    async def find_by_email(self, email: str) -> User | None:
        """Find user by email."""
        user_dict = await self.collection.find_one({"email": email, "is_deleted": False})
        return User(**user_dict) if user_dict else None
    
    async def create(self, user_data: dict) -> User:
        """Create new user."""
        result = await self.collection.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        return User(**user_data)

# In service.py
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
    
    async def register_user(self, user_data: UserCreate) -> User:
        """Business logic for user registration."""
        # Check if email exists
        existing = await self.repo.find_by_email(user_data.email)
        if existing:
            raise DuplicateEmailError()
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Create user
        user_dict = {**user_data.dict(), "password_hash": hashed_password}
        return await self.repo.create(user_dict)
```

---

## 🚨 CRITICAL REMINDERS

### **NEVER DO THESE:**
1. ❌ Write implementation before tests
2. ❌ Skip error handling
3. ❌ Use generic exception messages
4. ❌ Log sensitive data (passwords, tokens)
5. ❌ Hardcode values (use env vars)
6. ❌ Skip type hints
7. ❌ Skip docstrings
8. ❌ Ignore soft deletes (always check `is_deleted=False`)
9. ❌ Return raw database errors to users
10. ❌ Skip validation

### **ALWAYS DO THESE:**
1. ✅ Write tests first (TDD)
2. ✅ Use standardized response format
3. ✅ Handle errors gracefully
4. ✅ Log important events
5. ✅ Validate all inputs with Pydantic
6. ✅ Use atomic, single-purpose functions
7. ✅ Add type hints and docstrings
8. ✅ Check permissions before operations
9. ✅ Invalidate cache on mutations
10. ✅ Use soft deletes (is_deleted flag)

---

## 🎯 IMPLEMENTATION ORDER

Follow this exact order for systematic development:

1. **Project Setup** → Structure, env, dependencies
2. **Core Infrastructure** → Config, database, responses, exceptions
3. **Providers** → AWS S3, Resend email
4. **Auth Module** → Tests first, then implementation
5. **Users Module** → Tests first, then implementation
6. **Permissions Module** → Tests first, then implementation
7. **Roles Module** → Tests first, then implementation
8. **Plans Module** → Tests first, then implementation
9. **User_Plans Module** → Tests first, then implementation
10. **Notifications Module** → Tests first, then implementation
11. **Middleware** → Rate limiting, logging, error handling
12. **Background Tasks** → Celery/ARQ setup, email/notification tasks
13. **Initialization Scripts** → Superadmin, default data
14. **Main Application** → Wire everything together
15. **Phase 2 Modules** → Abstracted base structures

---

## 📊 SUCCESS CRITERIA

Before considering Phase 1 complete, ensure:

- [ ] All tests pass (80%+ coverage)
- [ ] Superadmin can be created on startup
- [ ] Users can register, login, verify email
- [ ] RBAC works (roles, permissions, authorization)
- [ ] Plans can be created and assigned to users
- [ ] Notifications work (in-app + email)
- [ ] File upload works (S3)
- [ ] Caching works (Redis, 1-day TTL)
- [ ] Rate limiting works (100/min users, unlimited admins)
- [ ] Logging works (different levels for dev/prod)
- [ ] Background tasks work (FastAPI BackgroundTasks for email sending)
- [ ] Soft delete works everywhere
- [ ] Pagination works on all list endpoints
- [ ] Standardized responses everywhere
- [ ] API documentation (auto-generated by FastAPI)

---

## 🎓 FINAL INSTRUCTIONS

You are now ready to build this system. Remember:

1. **ALWAYS write tests BEFORE implementation** (Test-Driven Development)
2. **Follow SOLID principles** - make code extensible
3. **Use atomic functions** - single responsibility
4. **Document everything** - docstrings, comments (see workspace documentation standards)
5. **Handle errors gracefully** - custom exceptions
6. **Log appropriately** - context, not spam
7. **Validate strictly** - Pydantic validators
8. **Test thoroughly** - positive, negative, edge cases (see workspace testing guidelines)
9. **No hardcoded values** - environment variables only (see workspace env policy)
10. **Follow workspace rules** - security, git workflow, naming conventions

### Workspace Integration

This document works in conjunction with workspace-level rules:
- **Code Quality:** Documentation standards, code formatting
- **Security:** Best practices, authentication patterns
- **Testing:** Testing guidelines for backend
- **Git Workflow:** Version control, commit conventions
- **Environment Variables:** Strict no-hardcoding policy
- **Docker Deployment:** Container setup and deployment

**Access workspace rules via `.cursorrules` for complete guidelines.**

### Development Approach

Since this is **scaffold development**, prioritize:
- Comprehensive documentation at every step
- Clear architectural decision records
- Well-documented code with examples
- Incremental development with testing

**Build Phase 1 completely before Phase 2. Each feature must be fully tested and working before moving to the next.**

Good luck! 🚀