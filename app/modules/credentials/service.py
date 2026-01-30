"""
Credentials module service layer.

Business logic for credential operations.
"""

from typing import List, Optional, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.shared.exceptions import ValidationError, NotFoundError
from app.modules.credentials import models as credential_models
from app.modules.credentials.encryption import encrypt_credentials, decrypt_credentials
from app.modules.credentials.schemas import (
    CreateCredentialsRequest,
    UpdateCredentialsRequest,
    CredentialsResponse,
    ConnectionTestResponse
)
from app.modules.wallets import models as wallet_models
from app.utils.cache import CacheManager
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Cache manager for credentials
cache = CacheManager("credentials")


async def create_user_credentials(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    credentials_data: CreateCredentialsRequest
) -> CredentialsResponse:
    """
    Create new user credentials.
    
    Args:
        db: Database instance
        user_id: User ID
        credentials_data: Credentials creation data
        
    Returns:
        CredentialsResponse: Created credentials
        
    Raises:
        NotFoundError: If wallet not found
        ValidationError: If validation fails
    """
    # Get wallet definition
    wallet = await wallet_models.find_wallet_by_id(db, ObjectId(credentials_data.wallet_id))
    if not wallet:
        raise NotFoundError(f"Wallet with ID '{credentials_data.wallet_id}' not found")
    
    # Validate credentials against wallet auth_fields
    auth_fields = wallet.get("auth_fields", [])
    required_fields = [field["key"] for field in auth_fields if field.get("required", False)]
    
    # Check all required fields are provided
    missing_fields = [field for field in required_fields if field not in credentials_data.credentials]
    if missing_fields:
        raise ValidationError(f"Missing required credential fields: {', '.join(missing_fields)}")
    
    # Encrypt credentials based on wallet auth_fields
    encrypted_creds = encrypt_credentials(credentials_data.credentials, auth_fields)
    
    # Create credentials record
    credential_dict = {
        "user_id": user_id,
        "wallet_id": ObjectId(credentials_data.wallet_id),
        "name": credentials_data.name,
        "credentials": encrypted_creds,
        "environment": credentials_data.environment
    }
    
    try:
        credential = await credential_models.create_credentials(db, credential_dict)
        
        # Invalidate cache (non-critical, don't fail if Redis is unavailable)
        try:
            await cache.invalidate_all()
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {str(e)}")
        
        # Convert to response (without secrets)
        return CredentialsResponse(
            id=str(credential["_id"]),
            wallet_id=str(credential["wallet_id"]),
            name=credential["name"],
            is_connected=credential.get("is_connected", False),
            last_verified_at=credential.get("last_verified_at").isoformat() if credential.get("last_verified_at") else None,
            connection_error=credential.get("connection_error"),
            environment=credential["environment"],
            is_active=credential["is_active"],
            created_at=credential["created_at"].isoformat(),
            updated_at=credential["updated_at"].isoformat()
        )
    except Exception as e:
        logger.error(f"Error creating credentials: {str(e)}")
        raise


async def get_user_credentials(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    credentials_id: str
) -> CredentialsResponse:
    """
    Get user credentials by ID.
    
    Args:
        db: Database instance
        user_id: User ID
        credentials_id: Credentials ID
        
    Returns:
        CredentialsResponse: Credentials data
        
    Raises:
        NotFoundError: If credentials not found
    """
    credential = await credential_models.find_credentials_by_id(
        db,
        ObjectId(credentials_id),
        user_id=user_id
    )
    
    if not credential:
        raise NotFoundError(f"Credentials with ID '{credentials_id}' not found")
    
    return CredentialsResponse(
        id=str(credential["_id"]),
        wallet_id=str(credential["wallet_id"]),
        name=credential["name"],
        is_connected=credential.get("is_connected", False),
        last_verified_at=credential.get("last_verified_at").isoformat() if credential.get("last_verified_at") else None,
        connection_error=credential.get("connection_error"),
        environment=credential["environment"],
        is_active=credential["is_active"],
        created_at=credential["created_at"].isoformat(),
        updated_at=credential["updated_at"].isoformat()
    )


async def list_user_credentials(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    filters: Dict[str, Any],
    limit: int = 100,
    offset: int = 0
) -> tuple[List[CredentialsResponse], int]:
    """
    List user credentials with filtering and pagination.
    
    Args:
        db: Database instance
        user_id: User ID
        filters: Filter dictionary (wallet_id, is_active)
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        tuple: (List of credentials, total count)
    """
    wallet_id = filters.get("wallet_id")
    is_active = filters.get("is_active")
    
    # Convert is_active string to bool if needed
    if isinstance(is_active, str):
        is_active = is_active.lower() == "true"
    
    # Convert wallet_id to ObjectId if provided and valid
    wallet_obj_id = None
    if wallet_id:
        try:
            wallet_obj_id = ObjectId(wallet_id)
        except Exception:
            raise ValidationError(f"Invalid wallet_id: {wallet_id}")
    
    credentials, total = await credential_models.list_user_credentials(
        db,
        user_id,
        wallet_id=wallet_obj_id,
        is_active=is_active,
        limit=limit,
        offset=offset
    )
    
    # Convert to response models
    credential_responses = []
    for cred in credentials:
        credential_responses.append(
            CredentialsResponse(
                id=str(cred["_id"]),
                wallet_id=str(cred["wallet_id"]),
                name=cred["name"],
                is_connected=cred.get("is_connected", False),
                last_verified_at=cred.get("last_verified_at").isoformat() if cred.get("last_verified_at") else None,
                connection_error=cred.get("connection_error"),
                environment=cred["environment"],
                is_active=cred["is_active"],
                created_at=cred["created_at"].isoformat(),
                updated_at=cred["updated_at"].isoformat()
            )
        )
    
    return credential_responses, total


async def update_user_credentials(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    credentials_id: str,
    update_data: UpdateCredentialsRequest
) -> CredentialsResponse:
    """
    Update user credentials.
    
    Args:
        db: Database instance
        user_id: User ID
        credentials_id: Credentials ID
        update_data: Update data
        
    Returns:
        CredentialsResponse: Updated credentials
        
    Raises:
        NotFoundError: If credentials not found
        ValidationError: If validation fails
    """
    # Get existing credentials
    existing = await credential_models.find_credentials_by_id(
        db,
        ObjectId(credentials_id),
        user_id=user_id
    )
    
    if not existing:
        raise NotFoundError(f"Credentials with ID '{credentials_id}' not found")
    
    # Convert Pydantic model to dict, excluding None values
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # If credentials are being updated, encrypt them
    if "credentials" in update_dict:
        # Get wallet to get auth_fields
        wallet = await wallet_models.find_wallet_by_id(db, existing["wallet_id"])
        if wallet:
            auth_fields = wallet.get("auth_fields", [])
            update_dict["credentials"] = encrypt_credentials(update_dict["credentials"], auth_fields)
    
    try:
        updated = await credential_models.update_credentials(
            db,
            ObjectId(credentials_id),
            user_id,
            update_dict
        )
        
        if not updated:
            raise NotFoundError(f"Credentials with ID '{credentials_id}' not found")
        
        # Invalidate cache (non-critical, don't fail if Redis is unavailable)
        try:
            await cache.invalidate_all()
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {str(e)}")
        
        return CredentialsResponse(
            id=str(updated["_id"]),
            wallet_id=str(updated["wallet_id"]),
            name=updated["name"],
            is_connected=updated.get("is_connected", False),
            last_verified_at=updated.get("last_verified_at").isoformat() if updated.get("last_verified_at") else None,
            connection_error=updated.get("connection_error"),
            environment=updated["environment"],
            is_active=updated["is_active"],
            created_at=updated["created_at"].isoformat(),
            updated_at=updated["updated_at"].isoformat()
        )
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error updating credentials: {str(e)}")
        raise


async def delete_user_credentials(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    credentials_id: str
) -> bool:
    """
    Delete user credentials (soft delete).
    
    Args:
        db: Database instance
        user_id: User ID
        credentials_id: Credentials ID
        
    Returns:
        bool: True if successful
        
    Raises:
        NotFoundError: If credentials not found
    """
    success = await credential_models.delete_credentials(
        db,
        ObjectId(credentials_id),
        user_id
    )
    
    if not success:
        raise NotFoundError(f"Credentials with ID '{credentials_id}' not found")
    
    # Invalidate cache (non-critical, don't fail if Redis is unavailable)
    try:
        await cache.invalidate_all()
    except Exception as e:
        logger.warning(f"Failed to invalidate cache: {str(e)}")
    
    return True


async def test_connection(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    credentials_id: str
) -> ConnectionTestResponse:
    """
    Test connection with credentials.
    
    Args:
        db: Database instance
        user_id: User ID
        credentials_id: Credentials ID
        
    Returns:
        ConnectionTestResponse: Test result
        
    Raises:
        NotFoundError: If credentials not found
    """
    from datetime import datetime
    
    # Get credentials
    credential = await credential_models.find_credentials_by_id(
        db,
        ObjectId(credentials_id),
        user_id=user_id
    )
    
    if not credential:
        raise NotFoundError(f"Credentials with ID '{credentials_id}' not found")
    
    # Get wallet to get auth_fields for decryption
    wallet = await wallet_models.find_wallet_by_id(db, credential["wallet_id"])
    if not wallet:
        raise NotFoundError(f"Wallet not found for credentials")
    
    # Decrypt credentials for testing
    auth_fields = wallet.get("auth_fields", [])
    decrypted_creds = decrypt_credentials(credential["credentials"], auth_fields)
    
    # TODO: Implement actual connection test with exchange API
    # For now, simulate a test
    try:
        # Simulate connection test
        # In real implementation, this would call the exchange API
        is_connected = True
        error_message = None
        
        # Update credentials with test result
        await credential_models.update_credentials(
            db,
            ObjectId(credentials_id),
            user_id,
            {
                "is_connected": is_connected,
                "last_verified_at": datetime.utcnow() if is_connected else None,
                "connection_error": error_message
            }
        )
        
        return ConnectionTestResponse(
            success=is_connected,
            message="Connection test successful" if is_connected else "Connection test failed",
            is_connected=is_connected,
            last_verified_at=datetime.utcnow().isoformat() if is_connected else None,
            connection_error=error_message
        )
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        error_message = str(e)
        
        # Update credentials with error
        await credential_models.update_credentials(
            db,
            ObjectId(credentials_id),
            user_id,
            {
                "is_connected": False,
                "connection_error": error_message
            }
        )
        
        return ConnectionTestResponse(
            success=False,
            message=f"Connection test failed: {error_message}",
            is_connected=False,
            last_verified_at=None,
            connection_error=error_message
        )
