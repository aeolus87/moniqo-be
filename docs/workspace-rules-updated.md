# Updated Workspace Rules for Moniqo Backend

**Source of Truth:** `docs/project.md`

This document contains updated workspace rules that align with the comprehensive project documentation in `project.md`. These rules should replace or supplement the existing `.cursorrules` configuration.

---

## Rule 1: Test-Driven Development (TDD) - MANDATORY

### Overview
Test-Driven Development is **MANDATORY** for all features in this project. Never write implementation code before writing its tests.

### TDD Workflow - NEVER DEVIATE

**FOR EVERY SINGLE FEATURE/MODULE YOU BUILD:**

1. ✅ **WRITE TEST CASES FIRST** (Test-Driven Development)
   - Write **POSITIVE test cases** (happy path scenarios)
   - Write **NEGATIVE test cases** (error scenarios, edge cases, validation failures)
   - Include tests for: authentication, authorization, validation, business logic, error handling
   - Use descriptive test names: `test_create_user_with_valid_data_returns_201()`

2. ✅ **THEN IMPLEMENT THE FEATURE**
   - Write the actual implementation that makes tests pass
   - Follow SOLID principles
   - Use atomic, single-purpose functions
   - Add detailed docstrings and comments

3. ✅ **RUN TESTS CONTINUOUSLY**
   - Verify all tests pass before moving to next feature
   - Ensure no regression in existing tests

### Testing Framework
- **Framework:** pytest + pytest-asyncio + httpx
- **Coverage Target:** 80%+ code coverage
- **Async Testing:** Use `pytest-asyncio` for FastAPI endpoints

### Test Structure for Every Module

#### Positive Test Cases (Happy Path)
```python
async def test_create_user_with_valid_data_returns_201()
async def test_login_with_valid_credentials_returns_tokens()
async def test_get_user_by_id_returns_user_data()
async def test_update_user_with_valid_data_returns_updated_user()
async def test_delete_user_soft_deletes_user()
async def test_list_users_returns_paginated_results()
```

#### Negative Test Cases (Error Scenarios)
```python
async def test_create_user_with_duplicate_email_returns_400()
async def test_create_user_with_invalid_email_returns_422()
async def test_login_with_wrong_password_returns_401()
async def test_access_protected_route_without_token_returns_401()
async def test_access_forbidden_route_returns_403()
async def test_get_nonexistent_user_returns_404()
async def test_exceed_rate_limit_returns_429()
```

#### Edge Cases
```python
async def test_pagination_with_limit_exceeding_max_uses_max_limit()
async def test_soft_deleted_users_not_returned_in_list()
async def test_cache_invalidation_after_update()
async def test_token_expiration_returns_401()
```

### Test Fixtures (tests/conftest.py)
```python
@pytest.fixture
async def test_client() -> AsyncClient

@pytest.fixture
async def test_db() -> AsyncIOMotorDatabase

@pytest.fixture
async def superadmin_token() -> str

@pytest.fixture
async def regular_user_token() -> str
```

---

## Rule 2: FastAPI Backend Patterns

### Background Tasks Pattern

**Use FastAPI's built-in BackgroundTasks** - not Celery or ARQ (unless complex scheduling needed).

#### Usage Pattern
```python
from fastapi import BackgroundTasks

@router.post("/register")
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks
):
    # Create user (synchronous response)
    user = await create_user(user_data)
    
    # Add background task (non-blocking)
    background_tasks.add_task(send_welcome_email, user.email, user.first_name)
    
    return {"message": "User created successfully"}
```

#### Task Functions (app/tasks/)
```python
# app/tasks/email_tasks.py
async def send_welcome_email(email: str, first_name: str):
    """Send welcome email in background."""
    await email_service.send_welcome_email(email, first_name)

async def send_verification_email(email: str, token: str):
    """Send verification email in background."""
    await email_service.send_verification_email(email, token)
```

### Dependency Injection Pattern

#### Common Dependencies
```python
# app/core/dependencies.py

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get authenticated user from JWT token."""
    # Verify token, get user
    return user

async def require_permission(resource: str, action: str):
    """Dependency to check user permissions."""
    def permission_checker(current_user: User = Depends(get_current_user)):
        # Check if user has permission
        if not has_permission(current_user, resource, action):
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return permission_checker
```

#### Usage in Routes
```python
@router.get("/users", dependencies=[Depends(require_permission("users", "read"))])
async def list_users():
    pass
```

### Error Handling Pattern

#### Custom Exceptions
```python
# app/core/exceptions.py

class DuplicateEmailError(Exception):
    """Raised when email already exists."""
    pass

class InsufficientPermissionsError(Exception):
    """Raised when user lacks required permissions."""
    pass
```

#### Usage
```python
# ✅ CORRECT - Use custom exceptions
from app.core.exceptions import DuplicateEmailError

async def create_user(user_data: UserCreate) -> User:
    existing_user = await find_user_by_email(user_data.email)
    if existing_user:
        raise DuplicateEmailError(f"Email {user_data.email} already registered")
```

---

## Rule 3: MongoDB/Motor Patterns

### Database Technology
- **Database:** MongoDB
- **Driver:** Motor (async)
- **Connection:** AsyncIOMotorClient

### Soft Delete Pattern (MANDATORY)

**ALL collections must support soft deletes using `is_deleted` flag.**

```python
# ALWAYS include is_deleted in queries
async def get_user_by_id(user_id: ObjectId) -> User | None:
    user_dict = await db.users.find_one({
        "_id": user_id,
        "is_deleted": False  # ✅ ALWAYS CHECK
    })
    return User(**user_dict) if user_dict else None

# Soft delete - don't actually delete
async def delete_user(user_id: ObjectId) -> bool:
    result = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0
```

### Collection Structure

All collections must have:
```python
{
    "_id": ObjectId,
    # ... collection-specific fields ...
    "created_at": datetime,
    "updated_at": datetime,
    "is_deleted": bool  # For soft delete
}
```

### ObjectId References

Use ObjectId references for relationships (normalized approach):
```python
# Users collection
{
    "_id": ObjectId,
    "auth_id": ObjectId,      # Reference to auth collection
    "user_role": ObjectId,    # Reference to roles collection
    # ...
}
```

### Async Patterns

```python
# ✅ CORRECT - Use await for Motor operations
user = await db.users.find_one({"_id": user_id})
users = await db.users.find({"is_deleted": False}).to_list(length=100)
result = await db.users.insert_one(user_dict)
```

---

## Rule 4: Authentication & Authorization (RBAC)

### JWT Authentication

#### Token Structure
- **Access Token:** 30 minutes expiration
- **Refresh Token:** 7 days expiration
- **Algorithm:** HS256
- **Secret:** From environment variable `JWT_SECRET_KEY`

#### Implementation
```python
# app/core/security.py

def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
```

### Role-Based Access Control (RBAC)

#### Structure
- **Users** → have → **Roles**
- **Roles** → have → **Permissions**
- **Permissions** → format: `{resource}:{action}` (e.g., `users:read`, `users:write`)

#### Collections
```python
# Roles Collection
{
    "_id": ObjectId,
    "name": str,              # "Admin", "User"
    "permissions": [ObjectId] # Array of permission IDs
}

# Permissions Collection
{
    "_id": ObjectId,
    "resource": str,          # "users", "plans", "agents"
    "action": str             # "read", "write", "delete"
}
```

#### Permission Checking
```python
# app/core/dependencies.py

async def require_permission(resource: str, action: str):
    """Check if user has required permission."""
    async def permission_checker(current_user: User = Depends(get_current_user)):
        # Get user's role
        role = await get_role(current_user.user_role)
        
        # Get role's permissions
        permissions = await get_permissions(role.permissions)
        
        # Check if permission exists
        required_permission = f"{resource}:{action}"
        if not any(f"{p.resource}:{p.action}" == required_permission for p in permissions):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        return current_user
    return permission_checker
```

### Email Verification

- If `AUTO_VERIFY_EMAIL=False`: Send verification email
- If `AUTO_VERIFY_EMAIL=True`: Auto-verify (for development)

---

## Rule 5: API Standards

### Standardized Response Format (MANDATORY)

**ALL API endpoints must use this response format:**

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

#### Success Response Example
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

#### Error Response Example
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

### Pagination Standards

#### Request
- Query params: `?limit=10&offset=0`
- Default: `limit=10` (from env: `DEFAULT_PAGE_SIZE`)
- Max: `limit=5000` (from env: `MAX_PAGE_SIZE`)

#### Response
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

### Rate Limiting

#### Rules
- **Regular users:** 100 requests/minute (from env: `RATE_LIMIT_PER_MINUTE`)
- **Admins:** Unlimited (if `ADMIN_RATE_LIMIT_ENABLED=False`)

#### Implementation
- Use Redis for rate limit counters
- Key format: `rate_limit:{user_id}:{minute}`
- Return 429 (Too Many Requests) when exceeded

### Caching Strategy

#### Cache Policy
- Cache GET requests for list/detail endpoints
- TTL: 1 day max (configurable via `REDIS_TTL_SECONDS`)
- Cache key format: `{module}:{operation}:{params_hash}`
- Invalidate cache on CREATE/UPDATE/DELETE operations

#### Example
```python
# utils/cache.py

async def get_cache(key: str) -> Any | None:
    """Get value from cache."""
    pass

async def set_cache(key: str, value: Any, ttl: int = None) -> None:
    """Set value in cache with TTL."""
    pass

async def delete_cache_pattern(pattern: str) -> None:
    """Delete all keys matching pattern (e.g., 'users:*')."""
    pass
```

---

## Rule 6: Module Organization

### Feature-Based Structure

**Use feature-based modules, not layer-based.**

```
app/modules/
├── auth/
│   ├── __init__.py
│   ├── models.py           # MongoDB models
│   ├── schemas.py          # Pydantic DTOs
│   ├── service.py          # Business logic
│   ├── router.py           # API endpoints
│   └── dependencies.py     # Module-specific dependencies
├── users/
│   ├── __init__.py
│   ├── models.py
│   ├── schemas.py
│   ├── service.py
│   ├── router.py
│   └── dependencies.py
└── [other modules...]
```

### Module File Patterns

#### models.py - Database Models
```python
"""
Database models for [module] module.
Uses Motor async driver with MongoDB.
"""

class UserModel:
    """User database model."""
    # Collection-specific fields
```

#### schemas.py - Pydantic DTOs
```python
"""
Pydantic schemas for [module] module.
Request/response data validation.
"""

class UserCreate(BaseModel):
    """Schema for creating a user."""
    email: EmailStr
    first_name: str
    # ... validation rules
```

#### service.py - Business Logic
```python
"""
Business logic for [module] module.
Contains service layer functions.
"""

class UserService:
    """Service layer for user operations."""
    
    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user object
            
        Raises:
            DuplicateEmailError: If email already exists
        """
        pass
```

#### router.py - API Endpoints
```python
"""
API routes for [module] module.
All endpoints under /api/v1/[module]/
"""

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.post("/", response_model=StandardResponse)
async def create_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks
):
    """Create a new user."""
    pass
```

### Phase 1 vs Phase 2 Modules

#### Phase 1 Modules (Full Implementation)
- auth
- users
- roles
- permissions
- plans
- user_plans
- notifications

#### Phase 2 Modules (Abstracted Base Structures)
- wallets (provider-agnostic)
- agents (AI model agnostic)
- prompts
- user_wallets
- user_settings
- user_trades
- user_flows
- user_prompts

---

## Rule 7: Code Quality Standards (Enhanced)

### Type Hints (MANDATORY)
```python
# ✅ CORRECT
async def create_user(user_data: UserCreate, db: AsyncIOMotorDatabase) -> User:
    pass

# ❌ INCORRECT
async def create_user(user_data, db):
    pass
```

### Docstrings (Google Style - MANDATORY)
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
        
    Example:
        >>> user = await create_user(UserCreate(email="test@test.com"), db)
        >>> print(user.id)
    """
    pass
```

### Atomic Functions (Single Responsibility)
```python
# ✅ CORRECT - Each function does ONE thing
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

### Logging Standards
```python
# ✅ CORRECT - Context-rich logging
logger.info(f"User created successfully: user_id={user.id}, email={user.email}")
logger.error(f"Failed to create user: {str(e)}", exc_info=True)

# ❌ INCORRECT - No context
logger.info("User created")
logger.error("Error")
```

### NEVER Log These
- Passwords (plain or hashed)
- JWT tokens
- API keys
- Sensitive personal data

---

## Rule 8: Environment Variables Policy (Keep Existing)

**This rule remains unchanged - already comprehensive in workspace.**

### Key Points
- NEVER hardcode ANY configuration
- ALWAYS use environment variables
- Create `.env.example` with placeholders (commit this)
- Create `.env` with actual values (NEVER commit)
- ALL constants from `.env` files

---

## Rule 9: Scaffold Development Guidelines (Enhanced)

### Project Status
This is **scaffold development** - building from ground up with comprehensive documentation.

### Source of Truth
**`docs/project.md`** is the absolute source of truth for:
- Architecture decisions
- Implementation patterns
- Database schema
- API structure
- Module organization
- Testing requirements

### Initialization Scripts (MANDATORY)

#### scripts/init_superadmin.py
```python
"""
Create superadmin account on first startup.
Run this script on application startup (in main.py).
"""

async def init_superadmin():
    """
    Creates superadmin account if it doesn't exist.
    Uses credentials from environment variables:
    - SUPERADMIN_EMAIL
    - SUPERADMIN_PASSWORD
    - SUPERADMIN_FIRST_NAME
    - SUPERADMIN_LAST_NAME
    """
    pass
```

#### scripts/init_default_data.py
```python
"""
Initialize default roles, permissions, and plans.
Run this on first startup.
"""

async def init_default_roles():
    """Create default Admin and User roles."""
    pass

async def init_default_permissions():
    """Create default permissions for all resources."""
    pass

async def init_default_plans():
    """Create default Free plan."""
    pass
```

### Startup Integration
```python
# app/main.py

@app.on_event("startup")
async def startup_event():
    """Run initialization scripts on startup."""
    await init_superadmin()
    await init_default_data()
```

### Documentation Requirements
Every new feature must include:
- [ ] Comprehensive docstrings
- [ ] Usage examples
- [ ] Test coverage
- [ ] Update relevant documentation

---

## Integration Guide

### How to Apply These Rules

1. **Update `.cursorrules`**: Copy relevant sections from this document
2. **Reference in prompts**: Point to `docs/project.md` for detailed implementation
3. **Review checklist**: Use these rules as review criteria for all PRs
4. **Team alignment**: Ensure all developers understand these patterns

### Priority Order

1. **Highest Priority:**
   - Test-Driven Development (Rule 1)
   - API Standards (Rule 5)
   - Environment Variables (Rule 8)

2. **High Priority:**
   - FastAPI Patterns (Rule 2)
   - MongoDB Patterns (Rule 3)
   - Authentication & Authorization (Rule 4)

3. **Medium Priority:**
   - Module Organization (Rule 6)
   - Code Quality (Rule 7)
   - Scaffold Development (Rule 9)

---

## Summary of Changes

### New Rules Added
- ✅ Test-Driven Development mandate
- ✅ FastAPI BackgroundTasks pattern
- ✅ MongoDB/Motor async patterns
- ✅ Standardized API responses
- ✅ RBAC implementation
- ✅ Rate limiting specifics
- ✅ Caching strategy
- ✅ Pagination standards
- ✅ Initialization scripts requirement

### Existing Rules Enhanced
- ✅ Module organization with specific patterns
- ✅ Code quality with concrete examples
- ✅ Scaffold development with project.md reference

### Rules Kept As-Is
- ✅ Environment variables policy
- ✅ Documentation standards
- ✅ Project structure overview

---

**Last Updated:** Based on `docs/project.md` revision  
**Maintained By:** Development Team  
**Review Frequency:** Update when project.md changes


