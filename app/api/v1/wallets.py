"""
Wallet Management Router

FastAPI endpoints for wallet management using clean architecture.
Router → Service → Repository → Database
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user
from app.modules.wallets.service import WalletService
from app.modules.user_wallets.repository import (
    UserWalletRepository,
    get_user_wallet_repository,
)
from app.modules.user_wallets.schemas import (
    WalletDefinitionResponse,
    WalletDefinitionListResponse,
    CreateUserWalletRequest,
    UpdateUserWalletRequest,
    UserWalletResponse,
    UserWalletListResponse,
    ConnectionTestResponse,
    SyncBalanceResponse,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/wallets", tags=["wallets"])


def _wallet_definition_to_response(wallet_def) -> WalletDefinitionResponse:
    """Convert WalletDefinition domain model to response schema."""
    return WalletDefinitionResponse(
        id=str(wallet_def.id) if wallet_def.id else "",
        name=wallet_def.name,
        slug=wallet_def.slug,
        description=wallet_def.description,
        logo_url=wallet_def.logo_url,
        integration_type=wallet_def.integration_type.value,
        is_demo=wallet_def.is_demo,
        is_active=wallet_def.is_active,
        required_credentials=wallet_def.required_credentials,
        supported_symbols=wallet_def.supported_symbols,
        supported_order_types=wallet_def.supported_order_types,
        supports_margin=wallet_def.supports_margin,
        supports_futures=wallet_def.supports_futures,
        created_at=wallet_def.created_at,
        updated_at=wallet_def.updated_at,
    )


def _user_wallet_to_response(user_wallet, wallet_provider_name: Optional[str] = None) -> UserWalletResponse:
    """Convert UserWallet domain model to response schema."""
    # Remove credentials from response (security)
    response_data = {
        "id": str(user_wallet.id) if user_wallet.id else "",
        "user_id": str(user_wallet.user_id),
        "wallet_provider_id": str(user_wallet.wallet_provider_id),
        "wallet_provider_name": wallet_provider_name or "",
        "custom_name": user_wallet.custom_name,
        "is_active": user_wallet.is_active,
        "use_testnet": user_wallet.use_testnet,
        "connection_status": user_wallet.connection_status.value,
        "last_connection_test": user_wallet.last_connection_test,
        "last_connection_error": user_wallet.last_connection_error,
        "balance": user_wallet.balance,
        "balance_last_synced": user_wallet.balance_last_synced,
        "risk_limits": user_wallet.risk_limits,
        "total_trades": user_wallet.total_trades,
        "total_pnl": user_wallet.total_pnl,
        "last_trade_at": user_wallet.last_trade_at,
        "created_at": user_wallet.created_at,
        "updated_at": user_wallet.updated_at,
    }
    return UserWalletResponse(**response_data)


# ==================== WALLET DEFINITIONS ====================

@router.get("/definitions", response_model=WalletDefinitionListResponse)
async def list_wallet_definitions(
    current_user: dict = Depends(get_current_user),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    integration_type: Optional[str] = Query(None, description="Filter by integration type"),
    repo: UserWalletRepository = Depends(get_user_wallet_repository),
):
    """Get list of wallet providers."""
    service = WalletService(user_wallet_repo=repo)
    
    definitions = await service.get_wallet_definitions(
        is_active=is_active,
        integration_type=integration_type
    )
    
    return WalletDefinitionListResponse(
        wallets=[_wallet_definition_to_response(d) for d in definitions],
        total=len(definitions)
    )


@router.get("/definitions/{wallet_id}", response_model=WalletDefinitionResponse)
async def get_wallet_definition(
    wallet_id: str,
    current_user: dict = Depends(get_current_user),
    repo: UserWalletRepository = Depends(get_user_wallet_repository),
):
    """Get single wallet provider details."""
    service = WalletService(user_wallet_repo=repo)
    
    wallet_def = await service.get_wallet_definition(wallet_id)
    
    if not wallet_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet provider {wallet_id} not found"
        )
    
    return _wallet_definition_to_response(wallet_def)


# ==================== USER WALLETS ====================

@router.get("/", response_model=UserWalletListResponse)
async def list_user_wallets(
    current_user: dict = Depends(get_current_user),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    repo: UserWalletRepository = Depends(get_user_wallet_repository),
):
    """Get list of user's wallet connections."""
    service = WalletService(user_wallet_repo=repo)
    
    wallets = await service.get_user_wallets(
        user_id=str(current_user["_id"]),
        is_active=is_active
    )
    
    # Get wallet provider names
    wallet_responses = []
    for wallet in wallets:
        wallet_def = await service.get_wallet_definition(str(wallet.wallet_provider_id))
        provider_name = wallet_def.name if wallet_def else ""
        wallet_responses.append(_user_wallet_to_response(wallet, provider_name))
    
    return UserWalletListResponse(
        wallets=wallet_responses,
        total=len(wallet_responses)
    )


@router.post("/", response_model=UserWalletResponse, status_code=status.HTTP_201_CREATED)
async def create_user_wallet(
    request: CreateUserWalletRequest,
    current_user: dict = Depends(get_current_user),
    repo: UserWalletRepository = Depends(get_user_wallet_repository),
):
    """Create a new user wallet connection."""
    service = WalletService(user_wallet_repo=repo)
    
    try:
        user_wallet = await service.create_user_wallet(
            user_id=str(current_user["_id"]),
            wallet_provider_id=request.wallet_provider_id,
            custom_name=request.custom_name,
            credentials=request.credentials,
            risk_limits=request.risk_limits,
            use_testnet=request.use_testnet,
        )
        
        # Get wallet provider name
        wallet_def = await service.get_wallet_definition(str(user_wallet.wallet_provider_id))
        provider_name = wallet_def.name if wallet_def else ""
        
        return _user_wallet_to_response(user_wallet, provider_name)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create user wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user wallet"
        )


@router.get("/{wallet_id}", response_model=UserWalletResponse)
async def get_user_wallet(
    wallet_id: str,
    current_user: dict = Depends(get_current_user),
    repo: UserWalletRepository = Depends(get_user_wallet_repository),
):
    """Get user wallet by ID."""
    service = WalletService(user_wallet_repo=repo)
    
    user_wallet = await service.get_user_wallet(wallet_id)
    
    if not user_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User wallet not found"
        )
    
    # Verify ownership
    if str(user_wallet.user_id) != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get wallet provider name
    wallet_def = await service.get_wallet_definition(str(user_wallet.wallet_provider_id))
    provider_name = wallet_def.name if wallet_def else ""
    
    return _user_wallet_to_response(user_wallet, provider_name)


@router.patch("/{wallet_id}", response_model=UserWalletResponse)
async def update_user_wallet(
    wallet_id: str,
    request: UpdateUserWalletRequest,
    current_user: dict = Depends(get_current_user),
    repo: UserWalletRepository = Depends(get_user_wallet_repository),
):
    """Update user wallet."""
    service = WalletService(user_wallet_repo=repo)
    
    # Verify ownership
    user_wallet = await service.get_user_wallet(wallet_id)
    if not user_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User wallet not found"
        )
    
    if str(user_wallet.user_id) != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Handle credentials encryption if provided
    if request.credentials:
        from app.utils.encryption import get_encryption_service
        encryption = get_encryption_service()
        encrypted_credentials = encryption.encrypt_credentials(request.credentials)
        user_wallet.credentials = encrypted_credentials
    
    user_wallet = await service.update_user_wallet(
        wallet_id=wallet_id,
        custom_name=request.custom_name,
        is_active=request.is_active,
        risk_limits=request.risk_limits,
    )
    
    # Get wallet provider name
    wallet_def = await service.get_wallet_definition(str(user_wallet.wallet_provider_id))
    provider_name = wallet_def.name if wallet_def else ""
    
    return _user_wallet_to_response(user_wallet, provider_name)


@router.delete("/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_wallet(
    wallet_id: str,
    current_user: dict = Depends(get_current_user),
    repo: UserWalletRepository = Depends(get_user_wallet_repository),
):
    """Delete user wallet."""
    service = WalletService(user_wallet_repo=repo)
    
    # Verify ownership
    user_wallet = await service.get_user_wallet(wallet_id)
    if not user_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User wallet not found"
        )
    
    if str(user_wallet.user_id) != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    await service.delete_user_wallet(wallet_id)


@router.post("/{wallet_id}/test-connection", response_model=ConnectionTestResponse)
async def test_connection(
    wallet_id: str,
    current_user: dict = Depends(get_current_user),
    repo: UserWalletRepository = Depends(get_user_wallet_repository),
):
    """Test wallet connection."""
    service = WalletService(user_wallet_repo=repo)
    
    # Verify ownership
    user_wallet = await service.get_user_wallet(wallet_id)
    if not user_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User wallet not found"
        )
    
    if str(user_wallet.user_id) != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    result = await service.test_connection(wallet_id)
    
    return ConnectionTestResponse(
        success=result["success"],
        message=result["message"],
        status=result["status"],
        error=result.get("error"),
    )


@router.post("/{wallet_id}/sync-balance", response_model=SyncBalanceResponse)
async def sync_balance(
    wallet_id: str,
    current_user: dict = Depends(get_current_user),
    repo: UserWalletRepository = Depends(get_user_wallet_repository),
):
    """Sync balance from exchange."""
    service = WalletService(user_wallet_repo=repo)
    
    # Verify ownership
    user_wallet = await service.get_user_wallet(wallet_id)
    if not user_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User wallet not found"
        )
    
    if str(user_wallet.user_id) != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    result = await service.sync_balance(wallet_id)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to sync balance")
        )
    
    return SyncBalanceResponse(
        success=True,
        balance=result["balance"],
        synced_at=result["synced_at"],
    )
