"""
Pytest configuration and shared fixtures.

Provides test fixtures for database, HTTP client, and test data.
"""

import warnings

# Suppress deprecation warnings from third-party libraries
warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based.*config.*")

import pytest
import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# Ensure we're in project root directory so .env is found
# Pydantic Settings automatically searches current directory and parents for .env
_project_root = Path(__file__).parent.parent
_env_file = _project_root.joinpath(".env")

if not _env_file.exists():
    pytest.exit(
        f".env file not found at {_env_file}\n"
        f"Please create .env file based on env.example"
    )

# Change to project root (Pydantic Settings will find .env here)
os.chdir(_project_root)

# Now import settings - it will load from .env in project root
from app.main import app
from app.config.settings import settings

# Verify settings loaded successfully
if settings is None:
    pytest.exit(
        f"Failed to load settings from .env file.\n"
        f"Please ensure .env file exists at {_env_file} with all required variables.\n"
        f"See env.example for required variables."
    )

# Use the same database as configured (not a separate test database)
# We'll clean up test data after each test instead
TEST_DB_NAME = settings.MONGODB_DB_NAME if settings else "ai_trading_platform"
TEST_DB_NAME_REAL = settings.mongodb_db_name_real if settings else f"{TEST_DB_NAME}_real"
TEST_DB_NAME_DEMO = settings.mongodb_db_name_demo if settings else f"{TEST_DB_NAME}_demo"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Create event loop for async tests.
    
    Yields:
        asyncio.AbstractEventLoop: Event loop instance
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    Create test database connection.
    
    Creates a fresh test database for each test and drops it afterward.
    
    Yields:
        AsyncIOMotorDatabase: Test database instance
    """
    # Get MongoDB URL from settings or use default
    mongodb_url = settings.MONGODB_URL if settings else "mongodb://localhost:27017"
    
    # Create test database client
    client = AsyncIOMotorClient(mongodb_url)
    db = client[TEST_DB_NAME]
    
    # Drop incorrect email index on users collection if it exists
    # Users don't have email field - it's in auth collection
    try:
        await db.users.drop_index("email_1")
    except Exception:
        pass  # Index doesn't exist or can't be dropped, which is fine
    
    yield db
    
    # Clean up test data instead of dropping database
    try:
        # Drop test collections
        await db["auth"].delete_many({})
        await db["users"].delete_many({})
        await db["roles"].delete_many({})
        await db["permissions"].delete_many({})
        await db["plans"].delete_many({})
        await db["user_plans"].delete_many({})
        await db["notifications"].delete_many({})
        await db["wallets"].delete_many({})
        await db["credentials"].delete_many({})
        await db["user_wallets"].delete_many({})
        await db["orders"].delete_many({})
        await db["positions"].delete_many({})
        await db["executions"].delete_many({})
        await db["flows"].delete_many({})
    except Exception as e:
        print(f"Warning: Could not clean up test data: {e}")
    
    # Also clean up demo and real test databases if they exist
    try:
        from app.core.database import db_provider
        from app.core.context import TradingMode
        
        if db_provider._initialized:
            # Clean demo database
            db_demo = db_provider.get_db_for_mode(TradingMode.DEMO)
            await db_demo["orders"].delete_many({})
            await db_demo["positions"].delete_many({})
            await db_demo["executions"].delete_many({})
            await db_demo["flows"].delete_many({})
            await db_demo["user_wallets"].delete_many({})
            # Note: wallets collection is shared, so we don't delete it here
            
            # Clean real database
            db_real = db_provider.get_db_for_mode(TradingMode.REAL)
            await db_real["orders"].delete_many({})
            await db_real["positions"].delete_many({})
            await db_real["executions"].delete_many({})
            await db_real["flows"].delete_many({})
            await db_real["user_wallets"].delete_many({})
    except Exception as e:
        print(f"Warning: Could not clean up demo/real test databases: {e}")
    
    client.close()


@pytest.fixture(scope="function")
async def db_provider_initialized() -> AsyncGenerator[None, None]:
    """
    Initialize DatabaseProvider with test databases.
    
    This fixture ensures DatabaseProvider is initialized before tests run.
    Uses test database names from settings or defaults.
    """
    from app.core.database import db_provider
    
    # Initialize DatabaseProvider if not already initialized
    if not db_provider._initialized:
        await db_provider.initialize()
    
    yield
    
    # Note: We don't close DatabaseProvider here as it's a singleton
    # Cleanup is handled by individual test fixtures


@pytest.fixture(scope="function")
async def test_client(test_db: AsyncIOMotorDatabase) -> AsyncGenerator[AsyncClient, None]:
    """
    Create test HTTP client.
    
    Args:
        test_db: Test database fixture
        
    Yields:
        AsyncClient: HTTP client for testing API endpoints
    """
    # Note: DatabaseProvider is used for mode-specific routing
    # Test database is used for shared collections (users, auth, etc.)
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_user_data() -> dict:
    """
    Mock user registration data.
    
    Returns:
        dict: Valid user registration data
    """
    return {
        "email": "testuser@example.com",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
        "birthday": {
            "day": 15,
            "month": 6,
            "year": 1990
        },
        "phone_number": {
            "country_code": "+63",
            "mobile_number": "9171234567"
        }
    }


@pytest.fixture
def mock_user_data_minimal() -> dict:
    """
    Mock user registration data with minimal required fields.
    
    Returns:
        dict: Minimal valid user registration data
    """
    return {
        "email": "minimaluser@example.com",
        "password": "TestPassword123!",
        "first_name": "Minimal",
        "last_name": "User",
        "birthday": {
            "day": 1,
            "month": 1,
            "year": 1995
        }
    }


@pytest.fixture
def mock_admin_data() -> dict:
    """
    Mock admin user registration data.
    
    Returns:
        dict: Admin user registration data
    """
    return {
        "email": "admin@example.com",
        "password": "AdminPassword123!",
        "first_name": "Admin",
        "last_name": "User",
        "birthday": {
            "day": 1,
            "month": 1,
            "year": 1985
        }
    }


@pytest.fixture
async def registered_user(test_client: AsyncClient, mock_user_data: dict) -> dict:
    """
    Create and return a registered user.
    
    Args:
        test_client: HTTP client fixture
        mock_user_data: User data fixture
        
    Returns:
        dict: Registered user data with tokens
    """
    response = await test_client.post("/api/v1/auth/register", json=mock_user_data)
    return response.json()


@pytest.fixture
async def verified_user(test_db: AsyncIOMotorDatabase, registered_user: dict) -> dict:
    """
    Create a verified user.
    
    Args:
        test_db: Test database fixture
        registered_user: Registered user fixture
        
    Returns:
        dict: Verified user data
    """
    # Manually verify the user in database
    await test_db["auth"].update_one(
        {"email": registered_user["data"]["email"]},
        {"$set": {"is_verified": True}}
    )
    return registered_user


@pytest.fixture
async def user_token(
    test_client: AsyncClient,
    verified_user: dict,
    mock_user_data: dict,
    test_db: AsyncIOMotorDatabase,
    superuser_token: str
) -> str:
    """
    Get access token for verified user with a role that has users, plans, user_plans, and notifications permissions.
    
    Args:
        test_client: HTTP client fixture
        verified_user: Verified user fixture
        mock_user_data: User data fixture
        test_db: Test database fixture
        superuser_token: Superuser token to create permissions/roles
        
    Returns:
        str: Access token
    """
    headers = {"Authorization": f"Bearer {superuser_token}"}
    
    # Create permissions for users, plans, user_plans, and notifications
    permissions_to_create = [
        {"resource": "users", "action": "read", "description": "Read users"},
        {"resource": "users", "action": "write", "description": "Write users"},
        {"resource": "plans", "action": "read", "description": "Read plans"},
        {"resource": "plans", "action": "write", "description": "Write plans"},
        {"resource": "user_plans", "action": "read", "description": "Read user plans"},
        {"resource": "user_plans", "action": "write", "description": "Write user plans"},
        {"resource": "notifications", "action": "read", "description": "Read notifications"},
        {"resource": "notifications", "action": "write", "description": "Write notifications"},
    ]
    
    permission_ids = []
    
    for perm in permissions_to_create:
        perm_response = await test_client.post(
            "/api/v1/permissions",
            json=perm,
            headers=headers
        )
        
        if perm_response.status_code == 400:
            # Permission already exists, get it
            existing_perm = await test_db.permissions.find_one({
                "resource": perm["resource"],
                "action": perm["action"],
                "is_deleted": False
            })
            if existing_perm:
                permission_ids.append(str(existing_perm["_id"]))
        else:
            permission_ids.append(perm_response.json()["data"]["_id"])
    
    # Create a "User" role with both permissions
    role_response = await test_client.post(
        "/api/v1/roles",
        json={"name": "User", "description": "Regular user with read/write access", "permissions": permission_ids},
        headers=headers
    )
    
    # If role already exists, get it
    if role_response.status_code == 400:
        existing_role = await test_db.roles.find_one({"name": "User", "is_deleted": False})
        role_id = existing_role["_id"] if existing_role else None
    else:
        role_id_str = role_response.json()["data"]["_id"]
        from bson import ObjectId
        role_id = ObjectId(role_id_str)
    
    # Assign role to user
    if role_id:
        # Find auth record by email to get auth_id
        auth_record = await test_db.auth.find_one({"email": mock_user_data["email"], "is_deleted": False})
        if auth_record:
            # Find user by auth_id
            user = await test_db.users.find_one({"auth_id": auth_record["_id"], "is_deleted": False})
            if user:
                await test_db.users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"user_role": role_id}}
                )
    
    # Login and return token
    login_data = {
        "email": mock_user_data["email"],
        "password": mock_user_data["password"]
    }
    response = await test_client.post("/api/v1/auth/login", json=login_data)
    return response.json()["data"]["access_token"]


@pytest.fixture
async def admin_token(test_client: AsyncClient, test_db: AsyncIOMotorDatabase, mock_admin_data: dict) -> str:
    """
    Get access token for admin user.
    
    Args:
        test_client: HTTP client fixture
        test_db: Test database fixture
        mock_admin_data: Admin data fixture
        
    Returns:
        str: Admin access token
    """
    # Register admin
    response = await test_client.post("/api/v1/auth/register", json=mock_admin_data)
    
    # Verify admin
    await test_db["auth"].update_one(
        {"email": mock_admin_data["email"]},
        {"$set": {"is_verified": True}}
    )
    
    # Create admin role and assign to user
    # (This will be implemented later when roles module is ready)
    
    # Login and get token
    login_data = {
        "email": mock_admin_data["email"],
        "password": mock_admin_data["password"]
    }
    response = await test_client.post("/api/v1/auth/login", json=login_data)
    return response.json()["data"]["access_token"]


@pytest.fixture
async def superuser_token(
    test_client: AsyncClient,
    test_db: AsyncIOMotorDatabase
) -> str:
    """
    Create a superuser with Superadmin role and return authentication token.
    
    Returns:
        Access token for superuser with all permissions
    """
    from app.config.settings import settings
    from app.core.security import hash_password
    from datetime import datetime
    from bson import ObjectId
    
    # Use superadmin credentials from settings
    superuser_email = settings.SUPERADMIN_EMAIL if settings else "superadmin@example.com"
    superuser_password = "SuperSecurePassword123!"
    
    # Check if superuser already exists
    existing_auth = await test_db["auth"].find_one({"email": superuser_email, "is_deleted": False})
    
    if not existing_auth:
        # Create all permissions for superadmin
        all_permissions = [
            {"resource": "users", "action": "read"},
            {"resource": "users", "action": "write"},
            {"resource": "roles", "action": "read"},
            {"resource": "roles", "action": "write"},
            {"resource": "permissions", "action": "read"},
            {"resource": "permissions", "action": "write"},
            {"resource": "plans", "action": "read"},
            {"resource": "plans", "action": "write"},
            {"resource": "user_plans", "action": "read"},
            {"resource": "user_plans", "action": "write"},
            {"resource": "notifications", "action": "read"},
            {"resource": "notifications", "action": "write"},
            {"resource": "wallets", "action": "read"},
            {"resource": "wallets", "action": "write"},
        ]
        
        permission_ids = []
        for perm in all_permissions:
            # Check if permission exists
            existing_perm = await test_db["permissions"].find_one({
                "resource": perm["resource"],
                "action": perm["action"],
                "is_deleted": False
            })
            
            if existing_perm:
                permission_ids.append(existing_perm["_id"])
            else:
                # Create permission
                perm_doc = {
                    "resource": perm["resource"],
                    "action": perm["action"],
                    "description": f"{perm['action'].capitalize()} {perm['resource']}",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "is_deleted": False
                }
                perm_result = await test_db["permissions"].insert_one(perm_doc)
                permission_ids.append(perm_result.inserted_id)
        
        # Create or get Superadmin role
        superadmin_role = await test_db["roles"].find_one({"name": "Superadmin", "is_deleted": False})
        
        if not superadmin_role:
            role_doc = {
                "name": "Superadmin",
                "description": "Superadmin with all permissions",
                "permissions": permission_ids,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_deleted": False
            }
            role_result = await test_db["roles"].insert_one(role_doc)
            superadmin_role_id = role_result.inserted_id
        else:
            superadmin_role_id = superadmin_role["_id"]
        
        # Create auth record directly
        auth_doc = {
            "email": superuser_email,
            "password_hash": hash_password(superuser_password),
            "is_verified": True,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_deleted": False
        }
        auth_result = await test_db["auth"].insert_one(auth_doc)
        auth_id = auth_result.inserted_id
        
        # Create user record with Superadmin role
        user_doc = {
            "auth_id": auth_id,
            "first_name": "Super",
            "last_name": "Admin",
            "birthday": {"day": 1, "month": 1, "year": 1990},
            "avatar_url": None,
            "phone_number": {"country_code": None, "mobile_number": None},
            "user_role": superadmin_role_id,  # Assign Superadmin role
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_deleted": False
        }
        await test_db["users"].insert_one(user_doc)
    else:
        # If superuser exists but doesn't have a role, assign Superadmin role
        auth_id = existing_auth["_id"]
        user = await test_db["users"].find_one({"auth_id": auth_id, "is_deleted": False})
        
        if user and not user.get("user_role"):
            # Create Superadmin role if it doesn't exist
            superadmin_role = await test_db["roles"].find_one({"name": "Superadmin", "is_deleted": False})
            
            if not superadmin_role:
                # Create all permissions
                all_permissions = [
                    {"resource": "users", "action": "read"},
                    {"resource": "users", "action": "write"},
                    {"resource": "roles", "action": "read"},
                    {"resource": "roles", "action": "write"},
                    {"resource": "permissions", "action": "read"},
                    {"resource": "permissions", "action": "write"},
                    {"resource": "plans", "action": "read"},
                    {"resource": "plans", "action": "write"},
                    {"resource": "user_plans", "action": "read"},
                    {"resource": "user_plans", "action": "write"},
                    {"resource": "notifications", "action": "read"},
                    {"resource": "notifications", "action": "write"},
                    {"resource": "wallets", "action": "read"},
                    {"resource": "wallets", "action": "write"},
                ]
                
                permission_ids = []
                for perm in all_permissions:
                    existing_perm = await test_db["permissions"].find_one({
                        "resource": perm["resource"],
                        "action": perm["action"],
                        "is_deleted": False
                    })
                    
                    if existing_perm:
                        permission_ids.append(existing_perm["_id"])
                    else:
                        perm_doc = {
                            "resource": perm["resource"],
                            "action": perm["action"],
                            "description": f"{perm['action'].capitalize()} {perm['resource']}",
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                            "is_deleted": False
                        }
                        perm_result = await test_db["permissions"].insert_one(perm_doc)
                        permission_ids.append(perm_result.inserted_id)
                
                role_doc = {
                    "name": "Superadmin",
                    "description": "Superadmin with all permissions",
                    "permissions": permission_ids,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "is_deleted": False
                }
                role_result = await test_db["roles"].insert_one(role_doc)
                superadmin_role_id = role_result.inserted_id
            else:
                superadmin_role_id = superadmin_role["_id"]
            
            # Assign role to user
            await test_db["users"].update_one(
                {"_id": user["_id"]},
                {"$set": {"user_role": superadmin_role_id}}
            )
    
    # Login and get token
    login_data = {
        "email": superuser_email,
        "password": superuser_password
    }
    response = await test_client.post("/api/v1/auth/login", json=login_data)
    return response.json()["data"]["access_token"]

