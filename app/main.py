"""
FastAPI main application.

Entry point for the AI Agent Trading Platform backend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from app.config import settings
from app.config.database import connect_to_mongodb, close_mongodb_connection
from app.utils.cache import get_redis_client, close_redis_connection
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting application...")
    
    try:
        # Connect to MongoDB
        await connect_to_mongodb()
        
        # Connect to Redis
        await get_redis_client()
        
        # TODO: Run initialization scripts (Sprint 34)
        
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    try:
        # Close MongoDB connection
        await close_mongodb_connection()
        
        # Close Redis connection
        await close_redis_connection()
        
        logger.info("Application shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# API Description
API_DESCRIPTION = """
## 🚀 AI Agent Trading Platform API

A comprehensive REST API for managing AI-powered automated trading agents with advanced features including authentication, role-based access control, subscription management, and real-time notifications.

### 🔐 Authentication

This API uses **JWT (JSON Web Token)** authentication with Bearer tokens.

**How to authenticate:**
1. Register a new account at `POST /api/v1/auth/register`
2. Verify your email using the link sent to your inbox
3. Login at `POST /api/v1/auth/login` to receive an access token
4. Include the token in all subsequent requests: `Authorization: Bearer <your_token>`

**Token Information:**
- Access tokens expire after 30 minutes
- Refresh tokens expire after 7 days
- Use `POST /api/v1/auth/refresh` to get a new access token

### 🔒 Authorization (RBAC)

The API implements Role-Based Access Control with three levels:
- **Superadmin**: Full system access (user management, roles, permissions)
- **Admin**: Manage plans, view users
- **User**: Manage own profile, subscriptions, notifications

### 📊 Rate Limiting

API requests are rate-limited to prevent abuse:
- **Regular users**: 100 requests per minute
- **Admins**: Unlimited (configurable)
- Rate limit headers are included in responses

### 📄 Pagination

All list endpoints support pagination using query parameters:
- `limit` (default: 10, max: 5000): Number of items per page
- `offset` (default: 0): Number of items to skip

**Response format:**
```json
{
  "items": [...],
  "total": 150,
  "limit": 10,
  "offset": 0,
  "has_more": true
}
```

### 📮 Response Format

All API responses follow a standardized format:

**Success Response:**
```json
{
  "status_code": 200,
  "message": "Operation successful",
  "data": { ... },
  "error": null
}
```

**Error Response:**
```json
{
  "status_code": 400,
  "message": "Operation failed",
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Detailed error message"
  }
}
```

### 🎯 Features

- **User Management**: Registration, profile management, avatar uploads
- **Authentication**: Email verification, password reset, JWT tokens
- **RBAC**: Flexible role and permission management
- **Subscription Plans**: Tiered pricing with feature/limit management
- **Notifications**: Real-time in-app notifications
- **Caching**: Redis-based caching for improved performance
- **Soft Deletes**: All resources support soft deletion for data recovery

### 📞 Support

For questions or issues, please contact our support team.
"""

# Create FastAPI application
app = FastAPI(
    title="AI Agent Trading Platform API",
    version="1.0.0",
    description=API_DESCRIPTION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "AI Agent Trading Platform Team",
        "email": "support@aiagenttrading.com",
        "url": "https://aiagenttrading.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings else ["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.permissions.router import router as permissions_router
from app.modules.roles.router import router as roles_router
from app.modules.plans.router import router as plans_router
from app.modules.user_plans.router import router as user_plans_router
from app.modules.notifications.router import router as notifications_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(permissions_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")
app.include_router(plans_router, prefix="/api/v1")
app.include_router(user_plans_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")

# TODO: Add middleware (Sprint 31-33)
# TODO: Include more routers (Sprint 16, 18, 22, 24, 26)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.APP_NAME if settings else "AI Agent Trading Platform",
        "version": settings.APP_VERSION if settings else "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME if settings else "AI Agent Trading Platform",
        "version": settings.APP_VERSION if settings else "1.0.0"
    }


# Custom OpenAPI schema
def custom_openapi():
    """
    Generate custom OpenAPI schema with security and tags.
    
    Returns:
        dict: Custom OpenAPI schema with JWT security and organized tags
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    # Generate base schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        contact=app.contact,
        license_info=app.license_info
    )
    
    # Add security scheme for JWT
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT access token. Format: Bearer <token>"
        }
    }
    
    # Add tags with descriptions
    openapi_schema["tags"] = [
        {
            "name": "Authentication",
            "description": "User registration, login, email verification, and password reset endpoints. Handles JWT token generation and management."
        },
        {
            "name": "Users",
            "description": "User profile management including profile updates, avatar uploads, and user administration. Regular users can manage their own profiles, while admins can manage all users."
        },
        {
            "name": "Roles",
            "description": "Role management for Role-Based Access Control (RBAC). Define roles and assign permissions to control user access levels. Superadmin only."
        },
        {
            "name": "Permissions",
            "description": "Permission management for granular access control. Create and manage permissions that can be assigned to roles. Superadmin only."
        },
        {
            "name": "Plans",
            "description": "Subscription plan management with features and limits. Define pricing tiers for different user access levels. Admins can create and manage plans."
        },
        {
            "name": "User Plans",
            "description": "User subscription management including creating, updating, cancelling, and renewing subscriptions. Users can manage their own subscriptions."
        },
        {
            "name": "Notifications",
            "description": "User notification system for in-app messages. Supports different notification types (info, success, warning, error) with read/unread status tracking."
        }
    ]
    
    # Cache the schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Set custom OpenAPI
app.openapi = custom_openapi

