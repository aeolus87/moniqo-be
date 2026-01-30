"""
FastAPI main application.

Entry point for the AI Agent Trading Platform backend.
"""

import warnings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Suppress deprecation warnings from third-party libraries
# passlib uses deprecated 'crypt' module until it updates for Python 3.13
warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib")
# Pydantic V2 migration warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based.*config.*")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import asyncio
import socketio
from app.core.config import settings
from app.core.database import db_provider
from app.utils.cache import get_redis_client, close_redis_client
from app.utils.logger import get_logger
from app.infrastructure.tasks.position_tracker import get_position_tracker
from app.infrastructure.market_data.market_data_service import MarketDataService, set_market_data_service, get_market_data_service
from app.infrastructure.market_data.binance_ws_client import BinanceWebSocketClient

logger = get_logger(__name__)


async def _position_monitor_loop() -> None:
    """
    Continuously monitor positions and emit Socket.IO updates.
    
    Monitors positions in both demo and real databases independently.
    """
    from app.core.context import set_trading_mode, TradingMode
    
    interval = max(1, int(getattr(settings, "POSITION_MONITOR_INTERVAL_SECONDS", 5)))
    while True:
        try:
            # Monitor demo positions
            db_demo = db_provider.get_db_for_mode(TradingMode.DEMO)
            demo_count = await db_demo["positions"].count_documents({
                "status": "open",
                "deleted_at": None
            })
            
            if demo_count > 0:
                set_trading_mode(TradingMode.DEMO)
                tracker_demo = await get_position_tracker()
                await tracker_demo.monitor_all_positions()
            
            # Monitor real positions
            db_real = db_provider.get_db_for_mode(TradingMode.REAL)
            real_count = await db_real["positions"].count_documents({
                "status": "open",
                "deleted_at": None
            })
            
            if real_count > 0:
                set_trading_mode(TradingMode.REAL)
                tracker_real = await get_position_tracker()
                await tracker_real.monitor_all_positions()
            
            if demo_count == 0 and real_count == 0:
                # Log once per minute instead of every 5 seconds when no positions
                logger.debug("No open positions to monitor")
        except Exception as e:
            logger.warning(f"Position monitor loop error: {e}")
        await asyncio.sleep(interval)

# Create Socket.IO server
sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    async_mode='asgi',
    logger=True,
    engineio_logger=True
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Setup clean logging on startup
    from app.core.logger import setup_development_logging
    setup_development_logging()

    # Startup
    logger.info("Starting application...")
    
    position_task: asyncio.Task | None = None
    try:
        # Initialize DatabaseProvider
        await db_provider.initialize()
    
        # Connect to Redis
        await get_redis_client()

        if getattr(settings, "POSITION_MONITOR_ENABLED", True):
            position_task = asyncio.create_task(_position_monitor_loop())
            app.state.position_monitor_task = position_task
        
        # Recover stuck executions on startup (check both databases)
        # Handle each database separately so one failure doesn't prevent checking the other
        from app.modules.flows.service import recover_stuck_executions
        from app.core.context import TradingMode
        
        demo_stats = {"total_recovered": 0, "recovered_expired": 0, "recovered_orphaned": 0}
        real_stats = {"total_recovered": 0, "recovered_expired": 0, "recovered_orphaned": 0}
        
        # Recover from demo database (continue even if it fails)
        try:
            db_demo = db_provider.get_db_for_mode(TradingMode.DEMO)
            demo_stats = await recover_stuck_executions(db_demo)
        except Exception as e:
            logger.debug(f"Could not recover stuck executions from demo database (may be permission issue): {e}")
        
        # Recover from real database (continue even if it fails)
        try:
            db_real = db_provider.get_db_for_mode(TradingMode.REAL)
            real_stats = await recover_stuck_executions(db_real)
        except Exception as e:
            logger.debug(f"Could not recover stuck executions from real database (may be permission issue): {e}")
        
        total_recovered = demo_stats["total_recovered"] + real_stats["total_recovered"]
        if total_recovered > 0:
            logger.info(
                f"Recovered {total_recovered} stuck executions on startup: "
                f"demo={demo_stats['total_recovered']} (expired={demo_stats['recovered_expired']}, orphaned={demo_stats['recovered_orphaned']}), "
                f"real={real_stats['total_recovered']} (expired={real_stats['recovered_expired']}, orphaned={real_stats['recovered_orphaned']})"
            )
        
        # Initialize market data service with Binance WebSocket
        try:
            market_provider = BinanceWebSocketClient(use_futures=True)
            market_service = MarketDataService(market_provider, sio)
            await market_service.start()  # Uses DatabaseProvider internally
            set_market_data_service(market_service)
            app.state.market_data_service = market_service
            logger.info("Market data service started")
        except Exception as e:
            logger.warning(f"Failed to start market data service: {e}")
        
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    try:
        if position_task:
            position_task.cancel()
            try:
                await position_task
            except asyncio.CancelledError:
                pass

        # Stop market data service
        market_service = get_market_data_service()
        if market_service:
            await market_service.stop()
            logger.info("Market data service stopped")

        # Close DatabaseProvider connections
        await db_provider.close()
        
        # Close Redis connection
        await close_redis_client()
        
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
    redirect_slashes=False,  # Disable automatic redirects to prevent 307 errors
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
# Default origins for development (Vite dev server on 5173, React on 3000)
default_cors_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# Get CORS origins from settings or use defaults
cors_origins = default_cors_origins
if settings:
    try:
        cors_origins = settings.cors_origins_list
        logger.info(f"CORS origins loaded from settings: {cors_origins}")
    except Exception as e:
        logger.warning(f"Failed to load CORS origins from settings: {e}, using defaults: {default_cors_origins}")
else:
    logger.warning(f"Settings not initialized, using default CORS origins: {default_cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add Trading Mode Middleware (after CORS, before routers)
from app.core.middleware import TradingModeMiddleware
app.add_middleware(TradingModeMiddleware)

# Include routers
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.permissions.router import router as permissions_router
from app.modules.roles.router import router as roles_router
from app.modules.plans.router import router as plans_router
from app.modules.user_plans.router import router as user_plans_router
from app.modules.notifications.router import router as notifications_router
from app.modules.wallets.router import router as wallets_router
from app.modules.credentials.router import router as credentials_router
from app.modules.user_wallets.router import router as user_wallets_router
from app.modules.orders.router import router as orders_router
from app.modules.positions.router import router as positions_router
from app.modules.ai_agents.router import router as ai_agents_router
from app.modules.market.router import router as market_router
from app.modules.flows.router import router as flows_router
from app.modules.risk_rules.router import router as risk_rules_router
from app.modules.conversations.router import router as conversations_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(permissions_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")
app.include_router(plans_router, prefix="/api/v1")
app.include_router(user_plans_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
# Register routers in REVERSE order of specificity (most specific LAST)
# FastAPI checks routers in REVERSE order of registration!
# More specific prefixes must be registered LAST so they're checked FIRST
# /api/v1/wallets matches user_wallets_router (register first - checked last)
# /api/v1/wallets/definitions matches wallets_router (register second)
# /api/v1/wallets/credentials matches credentials_router (register last - checked first)
app.include_router(user_wallets_router, prefix="/api/v1")
app.include_router(wallets_router, prefix="/api/v1")
app.include_router(credentials_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(positions_router, prefix="/api/v1")
app.include_router(ai_agents_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")
app.include_router(flows_router, prefix="/api/v1")
app.include_router(risk_rules_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")

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
        },
        {
            "name": "Wallets",
            "description": "Platform wallet definitions management. Admin-controlled catalog of supported exchanges/wallets with dynamic credential requirements, features, and API configuration."
        },
        {
            "name": "Credentials",
            "description": "User wallet credentials management. Securely store and manage exchange API keys and secrets with encryption. Users can add, update, delete, and test their credentials."
        },
        {
            "name": "User Wallets",
            "description": "User wallet instances management. Create and manage wallet instances with user-defined risk limits and AI-managed trading parameters. Supports pause/resume functionality."
        },
        {
            "name": "AI Agents",
            "description": "AI-powered trading agents for market analysis, risk assessment, and trade execution. Uses Groq, OpenRouter, or Gemini models for intelligent decision-making."
        },
        {
            "name": "Market Data",
            "description": "Real-time and historical market data from Binance (OHLCV, tickers, prices) and Coinlore (global stats, top coins). FREE - No API keys required."
        },
        {
            "name": "Flows",
            "description": "Trading automation flows management. Create, configure, and trigger AI-powered trading flows with market analysis, risk validation, and execution."
        }
    ]
    
    # Cache the schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Set custom OpenAPI
app.openapi = custom_openapi

# Socket.IO event handlers
@sio.on('connect')
async def connect(sid, environ, auth):
    """Handle client connection"""
    logger.info(f'Client connected: {sid}, auth: {auth}')
    if auth and auth.get('token'):
        # TODO: Validate token and store user_id
        # For now, allow connection
        pass
    return True

@sio.on('disconnect')
async def disconnect(sid):
    """Handle client disconnection"""
    logger.info(f'Client disconnected: {sid}')
    
    # Clean up market subscriptions
    market_service = get_market_data_service()
    if market_service:
        await market_service.handle_disconnect(sid)

@sio.on('subscribe_positions')
async def subscribe_positions(sid, data, callback=None):
    """Subscribe to position updates for a user"""
    user_id = data.get('user_id')
    if user_id:
        await sio.enter_room(sid, f'positions:{user_id}')
        logger.info(f'Client {sid} subscribed to positions for user {user_id}')
        response = {'success': True, 'room': f'positions:{user_id}'}
        if callback:
            await callback(response)
        return response
    response = {'success': False, 'error': 'user_id required'}
    if callback:
        await callback(response)
    return response

@sio.on('unsubscribe_positions')
async def unsubscribe_positions(sid, data, callback=None):
    """Unsubscribe from position updates"""
    user_id = data.get('user_id')
    if user_id:
        await sio.leave_room(sid, f'positions:{user_id}')
        logger.info(f'Client {sid} unsubscribed from positions for user {user_id}')
        response = {'success': True}
        if callback:
            await callback(response)
        return response
    response = {'success': False, 'error': 'user_id required'}
    if callback:
        await callback(response)
    return response

@sio.on('subscribe_market')
async def subscribe_market(sid, data, callback=None):
    """Subscribe to real-time market data for symbols"""
    symbols = data.get('symbols', [])
    if not symbols:
        response = {'success': False, 'error': 'symbols required'}
        if callback:
            await callback(response)
        return response
    
    market_service = get_market_data_service()
    if not market_service:
        response = {'success': False, 'error': 'Market data service not available'}
        if callback:
            await callback(response)
        return response
    
    await market_service.subscribe_user(sid, symbols)
    logger.info(f'Client {sid} subscribed to market data for: {symbols}')
    response = {'success': True, 'symbols': symbols}
    if callback:
        await callback(response)
    return response

@sio.on('unsubscribe_market')
async def unsubscribe_market(sid, data, callback=None):
    """Unsubscribe from real-time market data"""
    symbols = data.get('symbols')  # None means unsubscribe from all
    
    market_service = get_market_data_service()
    if market_service:
        await market_service.unsubscribe_user(sid, symbols)
        logger.info(f'Client {sid} unsubscribed from market data')
    
    response = {'success': True}
    if callback:
        await callback(response)
    return response

# Create Socket.IO ASGI app wrapper
socket_app = socketio.ASGIApp(sio, app)

# Export socket_app as the main app for uvicorn
# This allows Socket.IO to work alongside FastAPI
# Use: uvicorn app.main:socket_app --reload
# Or keep using app if Socket.IO is not needed: uvicorn app.main:app --reload
