"""
Trading Mode Middleware

Determines trading mode (demo/real) from request context and validates
that wallet/flow mode matches the determined context. Implements safety
gates to prevent mode mismatches.

Checks:
1. X-Moniqo-Mode header (highest priority)
2. JWT token payload (if available)
3. Request body/query/path parameters (wallet_id, flow_id)
4. Defaults to DEMO (fail-safe)
"""

from typing import Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from bson import ObjectId

from app.core.context import TradingMode, set_trading_mode
from app.core.database import db_provider
from app.core.security import decode_token
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TradingModeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to determine and validate trading mode from request context.
    
    Determines mode from:
    1. Request body (user_wallet_id, wallet_id, flow_id)
    2. Query parameters
    3. Path parameters
    
    Safety Gates:
    - If context is REAL but wallet is DEMO → HTTPException(403)
    - If context is DEMO but wallet is REAL → HTTPException(403)
    - Defaults to DEMO if mode cannot be determined (fail-safe)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and determine trading mode.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response
        """
        # Skip middleware for certain paths (health checks, docs, etc.)
        if self._should_skip_middleware(request.url.path):
            return await call_next(request)
        
        # Determine trading mode from request
        mode = await self._determine_trading_mode(request)
        
        # Set context for request
        set_trading_mode(mode)
        
        # Validate mode if wallet/flow IDs are present
        try:
            await self._validate_request_mode(request, mode)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating request mode: {e}")
            # Don't fail the request, but log the error
            # Default to demo for safety
        
        # Process request
        response = await call_next(request)
        
        return response
    
    def _should_skip_middleware(self, path: str) -> bool:
        """Check if middleware should be skipped for this path."""
        skip_paths = [
            "/health",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/",
        ]
        return any(path.startswith(skip) for skip in skip_paths)
    
    async def _determine_trading_mode(self, request: Request) -> TradingMode:
        """
        Determine trading mode from request context.
        
        Priority order:
        1. X-Moniqo-Mode header (highest priority)
        2. JWT token payload (trading_mode field)
        3. Request body/query/path parameters (wallet_id, flow_id)
        4. Defaults to DEMO (fail-safe)
        
        Returns:
            TradingMode: Determined mode (defaults to DEMO)
        """
        # Check X-Moniqo-Mode header first (highest priority)
        mode_header = request.headers.get("X-Moniqo-Mode", "").lower()
        if mode_header in ["real", "demo"]:
            logger.debug(f"Trading mode from header: {mode_header}")
            return TradingMode.REAL if mode_header == "real" else TradingMode.DEMO
        
        # Check JWT token for trading_mode field
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            payload = decode_token(token)
            if payload and "trading_mode" in payload:
                mode_str = payload["trading_mode"].lower()
                if mode_str in ["real", "demo"]:
                    logger.debug(f"Trading mode from JWT: {mode_str}")
                    return TradingMode.REAL if mode_str == "real" else TradingMode.DEMO
        
        # Try to get wallet/flow ID from request
        wallet_id = None
        flow_id = None
        
        # Check query parameters
        if "user_wallet_id" in request.query_params:
            wallet_id = request.query_params["user_wallet_id"]
        elif "wallet_id" in request.query_params:
            wallet_id = request.query_params["wallet_id"]
        
        if "flow_id" in request.query_params:
            flow_id = request.query_params["flow_id"]
        
        # Check path parameters
        if hasattr(request, "path_params"):
            if "wallet_id" in request.path_params:
                wallet_id = request.path_params["wallet_id"]
            elif "user_wallet_id" in request.path_params:
                wallet_id = request.path_params["user_wallet_id"]
            
            if "flow_id" in request.path_params:
                flow_id = request.path_params["flow_id"]
        
        # Try to parse request body for JSON requests
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Peek at request body without consuming it
                body = await request.body()
                if body:
                    import json
                    body_data = json.loads(body)
                    
                    if "user_wallet_id" in body_data:
                        wallet_id = body_data["user_wallet_id"]
                    elif "wallet_id" in body_data:
                        wallet_id = body_data["wallet_id"]
                    
                    if "flow_id" in body_data:
                        flow_id = body_data["flow_id"]
                    
                    # Recreate request with body for downstream handlers
                    async def receive():
                        return {"type": "http.request", "body": body}
                    request._receive = receive
            except Exception:
                # If body parsing fails, continue without it
                pass
        
        # Determine mode from wallet/flow
        if wallet_id:
            mode = await self._get_mode_from_wallet(wallet_id)
            if mode:
                return mode
        
        if flow_id:
            mode = await self._get_mode_from_flow(flow_id)
            if mode:
                return mode
        
        # Default to DEMO (fail-safe)
        logger.debug("Could not determine trading mode from request, defaulting to DEMO")
        return TradingMode.DEMO
    
    async def _get_mode_from_wallet(self, wallet_id: str) -> TradingMode | None:
        """
        Get trading mode from wallet ID.
        
        Args:
            wallet_id: User wallet ID
            
        Returns:
            TradingMode or None if wallet not found
        """
        try:
            # Use demo database to check wallet (wallets collection is shared)
            db = db_provider.get_db_for_mode(TradingMode.DEMO)
            
            user_wallet = await db.user_wallets.find_one({
                "_id": ObjectId(wallet_id),
                "deleted_at": None
            })
            
            if not user_wallet:
                return None
            
            # Check wallet definition
            wallet_def_id = user_wallet.get("wallet_provider_id")
            if not wallet_def_id:
                return None
            
            wallet_def = await db.wallets.find_one({
                "_id": ObjectId(wallet_def_id),
                "deleted_at": None
            })
            
            if not wallet_def:
                return None
            
            # Determine if demo
            is_demo = (
                wallet_def.get("is_demo", False) or
                wallet_def.get("integration_type") == "simulation" or
                "demo" in wallet_def.get("slug", "").lower() or
                user_wallet.get("use_testnet", False)
            )
            
            return TradingMode.DEMO if is_demo else TradingMode.REAL
            
        except Exception as e:
            logger.error(f"Error getting mode from wallet: {e}")
            return None
    
    async def _get_mode_from_flow(self, flow_id: str) -> TradingMode | None:
        """
        Get trading mode from flow ID.
        
        Args:
            flow_id: Flow ID
            
        Returns:
            TradingMode or None if flow not found
        """
        try:
            # Check both databases for flow
            for mode in [TradingMode.DEMO, TradingMode.REAL]:
                db = db_provider.get_db_for_mode(mode)
                flow = await db.flows.find_one({
                    "_id": ObjectId(flow_id),
                    "deleted_at": None
                })
                
                if flow:
                    # Flow exists in this database, so mode is determined
                    return mode
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting mode from flow: {e}")
            return None
    
    async def _validate_request_mode(
        self,
        request: Request,
        trading_mode: TradingMode
    ) -> None:
        """
        Validate that request wallet/flow matches determined trading mode.
        
        Args:
            request: FastAPI request object
            trading_mode: Determined trading mode
            
        Raises:
            HTTPException: If mode mismatch detected
        """
        # Get wallet ID from request
        wallet_id = None
        
        # Check query parameters
        if "user_wallet_id" in request.query_params:
            wallet_id = request.query_params["user_wallet_id"]
        elif "wallet_id" in request.query_params:
            wallet_id = request.query_params["wallet_id"]
        
        # Check path parameters
        if hasattr(request, "path_params"):
            if "wallet_id" in request.path_params:
                wallet_id = request.path_params["wallet_id"]
            elif "user_wallet_id" in request.path_params:
                wallet_id = request.path_params["user_wallet_id"]
        
        # Check request body
        if not wallet_id and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    import json
                    body_data = json.loads(body)
                    if "user_wallet_id" in body_data:
                        wallet_id = body_data["user_wallet_id"]
                    elif "wallet_id" in body_data:
                        wallet_id = body_data["wallet_id"]
                    
                    # Recreate request with body
                    async def receive():
                        return {"type": "http.request", "body": body}
                    request._receive = receive
            except Exception:
                pass
        
        # Validate wallet mode if wallet ID is present
        if wallet_id:
            is_valid = await self._validate_wallet_mode(wallet_id, trading_mode)
            
            if not is_valid:
                logger.error(
                    f"Trading mode mismatch: wallet_id={wallet_id}, "
                    f"determined_mode={trading_mode.value}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Trading mode mismatch: Wallet mode does not match "
                        f"request context. Determined mode: {trading_mode.value}"
                    )
                )
    
    async def _validate_wallet_mode(
        self,
        wallet_id: str,
        expected_mode: TradingMode
    ) -> bool:
        """
        Validate that a wallet matches the expected trading mode.
        
        Args:
            wallet_id: User wallet ID to validate
            expected_mode: Expected trading mode (DEMO or REAL)
        
        Returns:
            bool: True if wallet matches expected mode, False otherwise
        """
        try:
            # Use demo database to check wallet (wallets collection is shared)
            db = db_provider.get_db_for_mode(TradingMode.DEMO)
            
            # Get user_wallet
            user_wallet = await db.user_wallets.find_one({
                "_id": ObjectId(wallet_id),
                "deleted_at": None
            })
            
            if not user_wallet:
                logger.warning(f"Wallet not found: {wallet_id}")
                return False
            
            # Get wallet definition
            wallet_def_id = user_wallet.get("wallet_provider_id")
            if not wallet_def_id:
                logger.warning(f"Wallet definition not found for wallet: {wallet_id}")
                return False
            
            wallet_def = await db.wallets.find_one({
                "_id": ObjectId(wallet_def_id),
                "deleted_at": None
            })
            
            if not wallet_def:
                logger.warning(f"Wallet definition not found: {wallet_def_id}")
                return False
            
            # Determine if wallet is demo
            is_demo_wallet = (
                wallet_def.get("is_demo", False) or
                wallet_def.get("integration_type") == "simulation" or
                "demo" in wallet_def.get("slug", "").lower() or
                user_wallet.get("use_testnet", False)
            )
            
            # Check if wallet mode matches expected mode
            wallet_mode = TradingMode.DEMO if is_demo_wallet else TradingMode.REAL
            
            if wallet_mode != expected_mode:
                logger.warning(
                    f"Wallet mode mismatch: wallet_id={wallet_id}, "
                    f"wallet_mode={wallet_mode.value}, expected_mode={expected_mode.value}"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating wallet mode: {e}")
            return False
