"""
Wallets module service layer.

Business logic for wallet definition operations.
"""

from typing import List, Optional, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.exceptions import ValidationError, NotFoundError
from app.modules.wallets import models as wallet_models
from app.modules.wallets.schemas import (
    CreateWalletDefinitionRequest,
    UpdateWalletDefinitionRequest,
    WalletDefinitionResponse
)
from app.utils.cache import CacheManager
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Cache manager for wallets
cache = CacheManager("wallets")


async def create_wallet_definition(
    db: AsyncIOMotorDatabase,
    wallet_data: CreateWalletDefinitionRequest,
    created_by_user_id: ObjectId
) -> WalletDefinitionResponse:
    """
    Create a new wallet definition.
    
    Args:
        db: Database instance
        wallet_data: Wallet creation data
        created_by_user_id: ID of user creating the wallet
        
    Returns:
        WalletDefinitionResponse: Created wallet definition
        
    Raises:
        ValidationError: If slug already exists or validation fails
    """
    # Check if slug already exists
    slug_exists = await wallet_models.check_slug_exists(db, wallet_data.slug)
    if slug_exists:
        raise ValidationError(f"Wallet with slug '{wallet_data.slug}' already exists")
    
    # Convert Pydantic model to dict
    wallet_dict = wallet_data.model_dump()
    
    try:
        # Create wallet
        wallet = await wallet_models.create_wallet(db, wallet_dict)
        
        # Invalidate cache (non-critical, don't fail if Redis is unavailable)
        try:
            await cache.invalidate_all()
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {str(e)}")
        
        # Convert to response
        return WalletDefinitionResponse(
            id=str(wallet["_id"]),
            name=wallet["name"],
            slug=wallet["slug"],
            type=wallet["type"],
            description=wallet["description"],
            logo=wallet.get("logo"),
            auth_fields=wallet["auth_fields"],
            features=wallet["features"],
            api_config=wallet["api_config"],
            is_active=wallet["is_active"],
            order=wallet["order"],
            created_at=wallet["created_at"].isoformat(),
            updated_at=wallet["updated_at"].isoformat()
        )
    except Exception as e:
        logger.error(f"Error creating wallet definition: {str(e)}")
        raise


async def get_wallet_definition(
    db: AsyncIOMotorDatabase,
    slug: str
) -> WalletDefinitionResponse:
    """
    Get wallet definition by slug.
    
    Args:
        db: Database instance
        slug: Wallet slug
        
    Returns:
        WalletDefinitionResponse: Wallet definition
        
    Raises:
        NotFoundError: If wallet not found
    """
    # Try cache first
    cached = await cache.get("definition", slug=slug)
    if cached:
        return WalletDefinitionResponse(**cached)
    
    # Get from database
    try:
        wallet = await wallet_models.find_wallet_by_slug(db, slug, include_inactive=False)
    except Exception as e:
        # If database error occurs, re-raise as database error (not NotFoundError)
        logger.error(f"Database error finding wallet: {str(e)}")
        raise
    
    if not wallet:
        raise NotFoundError(f"Wallet with slug '{slug}' not found")
    
    # Convert to response
    response = WalletDefinitionResponse(
        id=str(wallet["_id"]),
        name=wallet["name"],
        slug=wallet["slug"],
        type=wallet["type"],
        description=wallet["description"],
        logo=wallet.get("logo"),
        auth_fields=wallet["auth_fields"],
        features=wallet["features"],
        api_config=wallet["api_config"],
        is_active=wallet["is_active"],
        order=wallet["order"],
        created_at=wallet["created_at"].isoformat(),
        updated_at=wallet["updated_at"].isoformat()
    )
    
    # Cache response
    await cache.set("definition", response.model_dump(), slug=slug)
    
    return response


async def list_wallet_definitions(
    db: AsyncIOMotorDatabase,
    filters: Dict[str, Any],
    limit: int = 100,
    offset: int = 0
) -> tuple[List[WalletDefinitionResponse], int]:
    """
    List wallet definitions with filtering and pagination.
    
    Args:
        db: Database instance
        filters: Filter dictionary (type, is_active)
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        tuple: (List of wallet definitions, total count)
    """
    wallet_type = filters.get("type")
    is_active = filters.get("is_active")
    
    # Convert is_active string to bool if needed
    if isinstance(is_active, str):
        is_active = is_active.lower() == "true"
    elif is_active is None:
        is_active = None
    
    # Get wallets from database
    wallets, total = await wallet_models.list_wallets(
        db,
        wallet_type=wallet_type,
        is_active=is_active,
        limit=limit,
        offset=offset
    )
    
    # Convert to response models
    wallet_responses = []
    for wallet in wallets:
        wallet_responses.append(
            WalletDefinitionResponse(
                id=str(wallet["_id"]),
                name=wallet["name"],
                slug=wallet["slug"],
                type=wallet["type"],
                description=wallet["description"],
                logo=wallet.get("logo"),
                auth_fields=wallet["auth_fields"],
                features=wallet["features"],
                api_config=wallet["api_config"],
                is_active=wallet["is_active"],
                order=wallet["order"],
                created_at=wallet["created_at"].isoformat(),
                updated_at=wallet["updated_at"].isoformat()
            )
        )
    
    return wallet_responses, total


async def update_wallet_definition(
    db: AsyncIOMotorDatabase,
    slug: str,
    update_data: UpdateWalletDefinitionRequest
) -> WalletDefinitionResponse:
    """
    Update wallet definition.
    
    Args:
        db: Database instance
        slug: Wallet slug
        update_data: Update data
        
    Returns:
        WalletDefinitionResponse: Updated wallet definition
        
    Raises:
        NotFoundError: If wallet not found
        ValidationError: If validation fails
    """
    # Check if wallet exists
    existing_wallet = await wallet_models.find_wallet_by_slug(db, slug, include_inactive=True)
    if not existing_wallet:
        raise NotFoundError(f"Wallet with slug '{slug}' not found")
    
    # Convert Pydantic model to dict, excluding None values
    update_dict = update_data.model_dump(exclude_unset=True)
    
    try:
        # Update wallet
        updated_wallet = await wallet_models.update_wallet(db, slug, update_dict)
        
        if not updated_wallet:
            raise NotFoundError(f"Wallet with slug '{slug}' not found")
        
        # Invalidate cache (non-critical, don't fail if Redis is unavailable)
        try:
            await cache.invalidate_all()
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {str(e)}")
        
        # Convert to response
        return WalletDefinitionResponse(
            id=str(updated_wallet["_id"]),
            name=updated_wallet["name"],
            slug=updated_wallet["slug"],
            type=updated_wallet["type"],
            description=updated_wallet["description"],
            logo=updated_wallet.get("logo"),
            auth_fields=updated_wallet["auth_fields"],
            features=updated_wallet["features"],
            api_config=updated_wallet["api_config"],
            is_active=updated_wallet["is_active"],
            order=updated_wallet["order"],
            created_at=updated_wallet["created_at"].isoformat(),
            updated_at=updated_wallet["updated_at"].isoformat()
        )
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error updating wallet definition: {str(e)}")
        raise


async def delete_wallet_definition(
    db: AsyncIOMotorDatabase,
    slug: str
) -> bool:
    """
    Soft delete wallet definition (set is_active=False).
    
    Args:
        db: Database instance
        slug: Wallet slug
        
    Returns:
        bool: True if successful
        
    Raises:
        NotFoundError: If wallet not found
    """
    # Check if wallet exists
    existing_wallet = await wallet_models.find_wallet_by_slug(db, slug, include_inactive=True)
    if not existing_wallet:
        raise NotFoundError(f"Wallet with slug '{slug}' not found")
    
    try:
        # Soft delete wallet
        success = await wallet_models.soft_delete_wallet(db, slug)
        
        if not success:
            raise NotFoundError(f"Wallet with slug '{slug}' not found")
        
        # Invalidate cache (non-critical, don't fail if Redis is unavailable)
        try:
            await cache.invalidate_all()
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {str(e)}")
        
        return True
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error deleting wallet definition: {str(e)}")
        raise
