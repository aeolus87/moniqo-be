"""
Auth module service layer.

Business logic for authentication operations.
"""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    create_email_verification_token,
    verify_email_verification_token,
    create_password_reset_token,
    verify_password_reset_token,
)
from app.core.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
    UnverifiedEmailError,
    InactiveAccountError,
    UserNotFoundError,
    TokenExpiredError,
    InvalidTokenError,
)
from app.modules.auth import models as auth_models
from app.modules.auth.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def register_user(
    db: AsyncIOMotorDatabase,
    user_data: RegisterRequest
) -> dict:
    """
    Register a new user.
    
    Creates auth and user records, optionally auto-verifies email.
    
    Args:
        db: Database instance
        user_data: User registration data
        
    Returns:
        dict: Created user data with auth info
        
    Raises:
        DuplicateEmailError: If email already exists
    """
    # Check if email already exists
    existing_auth = await auth_models.find_auth_by_email(db, user_data.email)
    if existing_auth:
        logger.warning(f"Registration attempt with duplicate email: {user_data.email}")
        raise DuplicateEmailError(f"Email {user_data.email} is already registered")
    
    # Hash password
    password_hash = hash_password(user_data.password)
    
    # Auto-verify email if configured
    is_verified = settings.AUTO_VERIFY_EMAIL if settings else False
    
    # Create auth record
    auth_record = await auth_models.create_auth(
        db=db,
        email=user_data.email,
        password_hash=password_hash,
        is_verified=is_verified
    )
    
    # Create user record
    user_record = {
        "auth_id": auth_record["_id"],
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "birthday": {
            "day": user_data.birthday.day,
            "month": user_data.birthday.month,
            "year": user_data.birthday.year
        },
        "avatar_url": None,  # Will be set later or generated from first_name[0]
        "phone_number": {
            "country_code": user_data.phone_number.country_code if user_data.phone_number else None,
            "mobile_number": user_data.phone_number.mobile_number if user_data.phone_number else None
        } if user_data.phone_number else {"country_code": None, "mobile_number": None},
        "user_role": None,  # Will be set to default "User" role in router/service
        "created_at": auth_record["created_at"],
        "updated_at": auth_record["updated_at"],
        "is_deleted": False
    }
    
    result = await db["users"].insert_one(user_record)
    user_record["_id"] = result.inserted_id
    
    logger.info(f"User registered successfully: email={user_data.email}, user_id={result.inserted_id}")
    
    # Prepare response
    response_data = {
        "id": str(result.inserted_id),
        "email": user_data.email,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "is_verified": is_verified
    }
    
    return response_data


async def login(
    db: AsyncIOMotorDatabase,
    login_data: LoginRequest
) -> TokenResponse:
    """
    Authenticate user and return tokens.
    
    Args:
        db: Database instance
        login_data: Login credentials
        
    Returns:
        TokenResponse: Access and refresh tokens
        
    Raises:
        InvalidCredentialsError: If email or password is incorrect
        UnverifiedEmailError: If email is not verified
        InactiveAccountError: If account is inactive
    """
    # Find auth record
    auth = await auth_models.find_auth_by_email(db, login_data.email)
    
    if not auth:
        logger.warning(f"Login attempt with non-existent email: {login_data.email}")
        raise InvalidCredentialsError("Invalid email or password")
    
    # Verify password
    if not verify_password(login_data.password, auth["password_hash"]):
        logger.warning(f"Login attempt with incorrect password: {login_data.email}")
        raise InvalidCredentialsError("Invalid email or password")
    
    # Check if email is verified (skip if AUTO_VERIFY_EMAIL is True)
    auto_verify = settings.AUTO_VERIFY_EMAIL if settings else False
    if not auth["is_verified"] and not auto_verify:
        logger.warning(f"Login attempt with unverified email: {login_data.email}")
        raise UnverifiedEmailError("Please verify your email before logging in")
    
    # Check if account is active
    if not auth["is_active"]:
        logger.warning(f"Login attempt with inactive account: {login_data.email}")
        raise InactiveAccountError("Your account has been deactivated")
    
    # Get user record to include in token
    user = await db["users"].find_one({"auth_id": auth["_id"], "is_deleted": False})
    if not user:
        logger.error(f"User record not found for auth_id: {auth['_id']}")
        raise InvalidCredentialsError("Invalid email or password")
    
    # Create tokens
    token_data = {"sub": str(user["_id"]), "email": auth["email"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    logger.info(f"User logged in successfully: email={login_data.email}, user_id={user['_id']}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


async def refresh_access_token(
    db: AsyncIOMotorDatabase,
    refresh_token: str
) -> TokenResponse:
    """
    Generate new access token from refresh token.
    
    Args:
        db: Database instance
        refresh_token: Refresh token
        
    Returns:
        TokenResponse: New access token
        
    Raises:
        TokenExpiredError: If token is expired
        InvalidTokenError: If token is invalid
    """
    try:
        # Verify refresh token
        payload = verify_token(refresh_token, token_type="refresh")
        
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError("User ID not found in token")
        
        # Verify user still exists and is active
        user = await db["users"].find_one({"_id": ObjectId(user_id), "is_deleted": False})
        if not user:
            raise InvalidTokenError("User not found")
        
        auth = await auth_models.find_auth_by_id(db, user["auth_id"])
        if not auth or not auth["is_active"]:
            raise InvalidTokenError("Account is inactive")
        
        # Create new access token
        token_data = {"sub": user_id, "email": auth["email"]}
        access_token = create_access_token(token_data)
        
        logger.info(f"Access token refreshed: user_id={user_id}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,  # Return same refresh token
            token_type="bearer"
        )
        
    except TokenExpiredError:
        logger.warning("Token refresh attempt with expired token")
        raise
    except InvalidTokenError:
        logger.warning("Token refresh attempt with invalid token")
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise InvalidTokenError("Failed to refresh token")


async def verify_email_with_token(
    db: AsyncIOMotorDatabase,
    token: str
) -> bool:
    """
    Verify user email with token.
    
    Args:
        db: Database instance
        token: Email verification token
        
    Returns:
        bool: True if successful
        
    Raises:
        TokenExpiredError: If token is expired
        InvalidTokenError: If token is invalid
        UserNotFoundError: If user not found
    """
    try:
        # Verify token and extract email
        email = verify_email_verification_token(token)
        
        # Mark email as verified
        success = await auth_models.verify_email(db, email)
        
        if not success:
            raise UserNotFoundError(f"User with email {email} not found")
        
        logger.info(f"Email verified successfully: email={email}")
        return True
        
    except TokenExpiredError:
        logger.warning("Email verification attempt with expired token")
        raise
    except InvalidTokenError:
        logger.warning("Email verification attempt with invalid token")
        raise


async def request_password_reset(
    db: AsyncIOMotorDatabase,
    email: str
) -> str:
    """
    Generate password reset token.
    
    Args:
        db: Database instance
        email: User email
        
    Returns:
        str: Password reset token
        
    Raises:
        UserNotFoundError: If user not found
    """
    # Find auth record
    auth = await auth_models.find_auth_by_email(db, email)
    
    if not auth:
        logger.warning(f"Password reset requested for non-existent email: {email}")
        raise UserNotFoundError(f"User with email {email} not found")
    
    # Generate reset token
    reset_token = create_password_reset_token(email)
    
    logger.info(f"Password reset token generated: email={email}")
    
    return reset_token


async def reset_password(
    db: AsyncIOMotorDatabase,
    token: str,
    new_password: str
) -> bool:
    """
    Reset user password with token.
    
    Args:
        db: Database instance
        token: Password reset token
        new_password: New password
        
    Returns:
        bool: True if successful
        
    Raises:
        TokenExpiredError: If token is expired
        InvalidTokenError: If token is invalid
        UserNotFoundError: If user not found
    """
    try:
        # Verify token and extract email
        email = verify_password_reset_token(token)
        
        # Hash new password
        password_hash = hash_password(new_password)
        
        # Update password
        success = await auth_models.update_password(db, email, password_hash)
        
        if not success:
            raise UserNotFoundError(f"User with email {email} not found")
        
        logger.info(f"Password reset successfully: email={email}")
        return True
        
    except TokenExpiredError:
        logger.warning("Password reset attempt with expired token")
        raise
    except InvalidTokenError:
        logger.warning("Password reset attempt with invalid token")
        raise

