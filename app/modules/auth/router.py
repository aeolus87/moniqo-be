"""
Auth module router.

API endpoints for authentication operations.
"""

from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config.database import get_database
from app.core.responses import success_response, error_response
from app.core.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
    UnverifiedEmailError,
    InactiveAccountError,
    UserNotFoundError,
    TokenExpiredError,
    InvalidTokenError,
)
from app.modules.auth import service as auth_service
from app.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserResponse,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def error_json_response(status_code: int, message: str, error_code: str, error_message: str) -> JSONResponse:
    """Helper to create JSON error response with proper status code."""
    response = error_response(
        status_code=status_code,
        message=message,
        error_code=error_code,
        error_message=error_message
    )
    return JSONResponse(status_code=status_code, content=response)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_description="User registered successfully"
)
async def register(
    user_data: RegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Register a new user.
    
    Creates a new user account with the provided information.
    Email verification may be required depending on configuration.
    
    Args:
        user_data: User registration data
        db: Database instance
        
    Returns:
        Standardized response with user data
    """
    try:
        # Register user
        user = await auth_service.register_user(db, user_data)
        
        return success_response(
            status_code=status.HTTP_201_CREATED,
            message="User registered successfully",
            data=user
        )
        
    except DuplicateEmailError as e:
        logger.warning(f"Registration failed: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Registration failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Registration failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_description="Login successful"
)
async def login(
    login_data: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Authenticate user and return tokens.
    
    Validates credentials and returns access and refresh tokens.
    
    Args:
        login_data: Login credentials
        db: Database instance
        
    Returns:
        Standardized response with tokens
    """
    try:
        # Authenticate user
        tokens = await auth_service.login(db, login_data)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Login successful",
            data=tokens.model_dump()
        )
        
    except InvalidCredentialsError as e:
        logger.warning(f"Login failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Login failed",
            error_code=e.code,
            error_message=str(e)
        )
    except UnverifiedEmailError as e:
        logger.warning(f"Login failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Login failed",
            error_code=e.code,
            error_message=str(e)
        )
    except InactiveAccountError as e:
        logger.warning(f"Login failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Login failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Login failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    response_description="Token refreshed successfully"
)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Refresh access token.
    
    Generates a new access token using a valid refresh token.
    
    Args:
        refresh_data: Refresh token data
        db: Database instance
        
    Returns:
        Standardized response with new access token
    """
    try:
        # Refresh access token
        tokens = await auth_service.refresh_access_token(db, refresh_data.refresh_token)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Token refreshed successfully",
            data=tokens.model_dump()
        )
        
    except TokenExpiredError as e:
        logger.warning(f"Token refresh failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Token refresh failed",
            error_code=e.code,
            error_message=str(e)
        )
    except InvalidTokenError as e:
        logger.warning(f"Token refresh failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Token refresh failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Token refresh failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.get(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    response_description="Email verified successfully"
)
async def verify_email(
    token: str = Query(..., description="Email verification token"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Verify user email.
    
    Marks the user's email as verified using the provided token.
    
    Args:
        token: Email verification token
        db: Database instance
        
    Returns:
        Standardized response
    """
    try:
        # Verify email
        await auth_service.verify_email_with_token(db, token)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Email verified successfully",
            data=None
        )
        
    except TokenExpiredError as e:
        logger.warning(f"Email verification failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Email verification failed",
            error_code=e.code,
            error_message=str(e)
        )
    except InvalidTokenError as e:
        logger.warning(f"Email verification failed: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Email verification failed",
            error_code=e.code,
            error_message=str(e)
        )
    except UserNotFoundError as e:
        logger.warning(f"Email verification failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Email verification failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during email verification: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Email verification failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    response_description="Password reset email sent"
)
async def forgot_password(
    reset_request: ForgotPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Request password reset.
    
    Generates a password reset token and sends it via email.
    
    Args:
        reset_request: Forgot password request data
        db: Database instance
        
    Returns:
        Standardized response
    """
    try:
        # Request password reset
        reset_token = await auth_service.request_password_reset(db, reset_request.email)
        
        # TODO: Send reset email with token (Sprint 29-30)
        # For now, we'll return the token in response (NOT FOR PRODUCTION)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Password reset email sent",
            data={"token": reset_token}  # TODO: Remove in production
        )
        
    except UserNotFoundError as e:
        logger.warning(f"Password reset request failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Password reset request failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during password reset request: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Password reset request failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    response_description="Password reset successfully"
)
async def reset_password(
    reset_data: ResetPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Reset password.
    
    Resets the user's password using the provided token.
    
    Args:
        reset_data: Password reset data
        db: Database instance
        
    Returns:
        Standardized response
    """
    try:
        # Reset password
        await auth_service.reset_password(db, reset_data.token, reset_data.new_password)
        
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Password reset successfully",
            data=None
        )
        
    except TokenExpiredError as e:
        logger.warning(f"Password reset failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Password reset failed",
            error_code=e.code,
            error_message=str(e)
        )
    except InvalidTokenError as e:
        logger.warning(f"Password reset failed: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Password reset failed",
            error_code=e.code,
            error_message=str(e)
        )
    except UserNotFoundError as e:
        logger.warning(f"Password reset failed: {str(e)}")
        return error_json_response(
            status_code=e.status_code,
            message="Password reset failed",
            error_code=e.code,
            error_message=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during password reset: {str(e)}")
        return error_json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Password reset failed",
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An unexpected error occurred"
        )

