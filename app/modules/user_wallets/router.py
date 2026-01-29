"""
User Wallets Router

FastAPI endpoints for wallet management.

Endpoints:
- GET /api/v1/wallets/definitions - List wallet providers
- GET /api/v1/wallets/definitions/{id} - Get wallet provider
- GET /api/v1/user-wallets - List user's wallets
- POST /api/v1/user-wallets - Create user wallet
- GET /api/v1/user-wallets/{id} - Get user wallet
- PUT /api/v1/user-wallets/{id} - Update user wallet
- DELETE /api/v1/user-wallets/{id} - Delete user wallet
- POST /api/v1/user-wallets/{id}/test-connection - Test connection
- POST /api/v1/user-wallets/{id}/sync-balance - Sync balance
- GET /api/v1/user-wallets/{id}/sync-logs - Get sync logs

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.config.database import get_database
from app.core.dependencies import get_current_user
from app.modules.user_wallets.schemas import (
    WalletDefinitionResponse,
    WalletDefinitionListResponse,
    CreateUserWalletRequest,
    UpdateUserWalletRequest,
    UserWalletResponse,
    UserWalletListResponse,
    ConnectionTestResponse,
    SyncBalanceResponse,
    WalletSyncLogResponse,
    WalletSyncLogListResponse,
    ErrorResponse,
    AddBalanceRequest,
    AddBalanceResponse
)
from app.modules.user_wallets import service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==================== WALLET DEFINITIONS ====================

@router.get(
    "/wallets/definitions",
    response_model=WalletDefinitionListResponse,
    summary="List Wallet Providers",
    description="Get list of available wallet providers (exchanges, demo wallets, etc.)",
    tags=["Wallets"]
)
async def list_wallet_definitions(
    is_active: bool = True,
    integration_type: str = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of wallet providers.
    
    Returns wallet providers that users can connect to.
    """
    try:
        wallets = await service.get_wallet_definitions(
            db=db,
            is_active=is_active,
            integration_type=integration_type
        )
        
        return WalletDefinitionListResponse(
            wallets=wallets,
            total=len(wallets)
        )
    
    except Exception as e:
        logger.error(f"Failed to list wallet definitions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/wallets/definitions/{wallet_id}",
    response_model=WalletDefinitionResponse,
    summary="Get Wallet Provider",
    description="Get details of a specific wallet provider",
    tags=["Wallets"]
)
async def get_wallet_definition(
    wallet_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Get single wallet provider details."""
    try:
        wallet = await service.get_wallet_definition(db, wallet_id)
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet provider {wallet_id} not found"
            )
        
        return wallet
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get wallet definition: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== USER WALLETS ====================

@router.get(
    "/user-wallets",
    response_model=UserWalletListResponse,
    summary="List My Wallets",
    description="Get list of your wallet connections",
    tags=["User Wallets"]
)
async def list_user_wallets(
    is_active: bool = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of user's wallet connections.
    
    Returns all wallets the user has connected (Binance, Demo, etc.).
    """
    try:
        wallets = await service.get_user_wallets(
            db=db,
            user_id=str(current_user["_id"]),
            is_active=is_active
        )
        
        return UserWalletListResponse(
            wallets=wallets,
            total=len(wallets)
        )
    
    except Exception as e:
        logger.error(f"Failed to list user wallets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/user-wallets",
    response_model=UserWalletResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Wallet Connection",
    description="Connect a new wallet (exchange account, demo wallet, etc.)",
    tags=["User Wallets"]
)
async def create_user_wallet(
    request: CreateUserWalletRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Create new wallet connection.
    
    Connects your account to a wallet provider (e.g., Binance).
    Credentials are encrypted before storage.
    """
    try:
        wallet = await service.create_user_wallet(
            db=db,
            user_id=str(current_user["_id"]),
            wallet_provider_id=request.wallet_provider_id,
            custom_name=request.custom_name,
            credentials=request.credentials,
            risk_limits=request.risk_limits
        )
        
        logger.info(
            f"User {current_user['email']} created wallet: {request.custom_name}"
        )
        
        return wallet
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create user wallet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/user-wallets/{wallet_id}",
    response_model=UserWalletResponse,
    summary="Get Wallet Details",
    description="Get details of a specific wallet connection",
    tags=["User Wallets"]
)
async def get_user_wallet(
    wallet_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Get single wallet connection details."""
    try:
        wallet = await service.get_user_wallet(
            db=db,
            user_wallet_id=wallet_id,
            user_id=str(current_user["_id"])
        )
        
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {wallet_id} not found"
            )
        
        return wallet
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user wallet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put(
    "/user-wallets/{wallet_id}",
    response_model=UserWalletResponse,
    summary="Update Wallet",
    description="Update wallet settings (name, credentials, risk limits)",
    tags=["User Wallets"]
)
async def update_user_wallet(
    wallet_id: str,
    request: UpdateUserWalletRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Update wallet connection settings."""
    try:
        # Build update dict (only non-None fields)
        update_data = {}
        if request.custom_name is not None:
            update_data["custom_name"] = request.custom_name
        if request.credentials is not None:
            update_data["credentials"] = request.credentials
        if request.is_active is not None:
            update_data["is_active"] = request.is_active
        if request.risk_limits is not None:
            update_data["risk_limits"] = request.risk_limits
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        wallet = await service.update_user_wallet(
            db=db,
            user_wallet_id=wallet_id,
            user_id=str(current_user["_id"]),
            update_data=update_data
        )
        
        logger.info(f"User {current_user['email']} updated wallet {wallet_id}")
        
        return wallet
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update user wallet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/user-wallets/{wallet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Wallet",
    description="Disconnect and delete a wallet connection",
    tags=["User Wallets"]
)
async def delete_user_wallet(
    wallet_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Delete wallet connection (soft delete)."""
    try:
        await service.delete_user_wallet(
            db=db,
            user_wallet_id=wallet_id,
            user_id=str(current_user["_id"])
        )
        
        logger.info(f"User {current_user['email']} deleted wallet {wallet_id}")
        
        return None
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete user wallet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== WALLET OPERATIONS ====================

@router.post(
    "/user-wallets/{wallet_id}/test-connection",
    response_model=ConnectionTestResponse,
    summary="Test Wallet Connection",
    description="Test connection to wallet/exchange to verify credentials",
    tags=["User Wallets"]
)
async def test_wallet_connection(
    wallet_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Test wallet connection.
    
    Verifies that credentials are correct and exchange is reachable.
    Updates connection status in database.
    """
    try:
        result = await service.test_wallet_connection(
            db=db,
            user_wallet_id=wallet_id,
            user_id=str(current_user["_id"])
        )
        
        if result["success"]:
            logger.info(
                f"Connection test success: user={current_user['email']}, "
                f"wallet={wallet_id}, latency={result['latency_ms']}ms"
            )
        else:
            logger.warning(
                f"Connection test failed: user={current_user['email']}, "
                f"wallet={wallet_id}, error={result['error']}"
            )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Connection test error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/user-wallets/{wallet_id}/sync-balance",
    response_model=SyncBalanceResponse,
    summary="Sync Wallet Balance",
    description="Fetch latest balance from exchange and update database",
    tags=["User Wallets"]
)
async def sync_wallet_balance(
    wallet_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Sync wallet balance.
    
    Fetches current balances from exchange and updates database.
    Creates sync log entry for audit trail.
    """
    try:
        result = await service.sync_wallet_balance(
            db=db,
            user_wallet_id=wallet_id,
            user_id=str(current_user["_id"])
        )
        
        if result["success"]:
            logger.info(
                f"Balance sync success: user={current_user['email']}, "
                f"wallet={wallet_id}, duration={result['sync_duration_ms']}ms"
            )
        else:
            logger.warning(
                f"Balance sync failed: user={current_user['email']}, "
                f"wallet={wallet_id}, error={result['error']}"
            )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Balance sync error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/user-wallets/{wallet_id}/sync-logs",
    response_model=WalletSyncLogListResponse,
    summary="Get Sync History",
    description="Get balance sync history for wallet",
    tags=["User Wallets"]
)
async def get_wallet_sync_logs(
    wallet_id: str,
    limit: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Get balance sync logs.
    
    Returns history of balance synchronization attempts.
    Useful for debugging and audit trail.
    """
    try:
        logs = await service.get_wallet_sync_logs(
            db=db,
            user_wallet_id=wallet_id,
            user_id=str(current_user["_id"]),
            limit=min(limit, 100)  # Max 100
        )
        
        return WalletSyncLogListResponse(
            logs=logs,
            total=len(logs)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get sync logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/user-wallets/{wallet_id}/add-balance",
    response_model=AddBalanceResponse,
    summary="Add Balance to Demo Wallet",
    description="Manually add balance to a demo wallet (demo wallets only)",
    tags=["User Wallets"]
)
async def add_demo_wallet_balance(
    wallet_id: str,
    request: AddBalanceRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Add balance to demo wallet.
    
    Only works for demo wallets. Allows manually adding funds
    to the demo wallet for testing purposes.
    """
    from decimal import Decimal
    from app.integrations.wallets.factory import get_wallet_factory
    
    try:
        # Verify wallet ownership
        user_wallet = await db.user_wallets.find_one({
            "_id": ObjectId(wallet_id),
            "user_id": str(current_user["_id"]),
            "deleted_at": None
        })
        
        if not user_wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        # Check if it's a demo wallet
        wallet_provider = await db.wallets.find_one({
            "_id": ObjectId(user_wallet["wallet_provider_id"]),
            "deleted_at": None
        })
        
        if not wallet_provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet provider not found"
            )
        
        wallet_type = wallet_provider.get("slug", wallet_provider.get("integration_type", "")).split("-")[0]
        
        if wallet_type not in ["demo", "simulation"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This endpoint only works for demo wallets"
            )
        
        # Create wallet instance
        factory = get_wallet_factory()
        wallet = await factory.create_wallet_from_db(db, wallet_id)
        
        # Add balance
        result = await wallet.add_balance(
            asset=request.asset,
            amount=Decimal(str(request.amount)),
            is_cash=request.is_cash
        )
        
        # Sync balance to user_wallet after adding
        try:
            await service.sync_wallet_balance(
                db=db,
                user_wallet_id=wallet_id,
                user_id=str(current_user["_id"])
            )
        except Exception as sync_error:
            logger.warning(f"Failed to sync balance after adding funds: {sync_error}")
            # Don't fail the request if sync fails - balance was still added to demo wallet
        
        logger.info(
            f"User {current_user['email']} added {request.amount} {request.asset} "
            f"to demo wallet {wallet_id}"
        )
        
        return AddBalanceResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add balance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== ERROR HANDLERS ====================
# Note: Exception handlers are registered at the app level in main.py
# Individual routes handle exceptions with try/except blocks
