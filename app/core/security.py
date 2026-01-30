"""
Security utilities for authentication.

Provides JWT token management and password hashing using bcrypt.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.core.config import settings
from app.shared.exceptions import TokenExpiredError, InvalidTokenError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
        
    Example:
        >>> hash_password("MyPassword123!")
        "$2b$12$..."
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        bool: True if password matches, False otherwise
        
    Example:
        >>> hashed = hash_password("MyPassword123!")
        >>> verify_password("MyPassword123!", hashed)
        True
        >>> verify_password("WrongPassword", hashed)
        False
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token (typically {"sub": user_id})
        expires_delta: Token expiration time (optional, defaults to ACCESS_TOKEN_EXPIRE_MINUTES)
        
    Returns:
        str: Encoded JWT token
        
    Example:
        >>> token = create_access_token({"sub": "user_id_123"})
        >>> print(token)
        "eyJhbGciOiJIUzI1NiIs..."
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at
        "type": "access"
    })
    
    # Encode JWT
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Data to encode in the token (typically {"sub": user_id})
        expires_delta: Token expiration time (optional, defaults to REFRESH_TOKEN_EXPIRE_DAYS)
        
    Returns:
        str: Encoded JWT token
        
    Example:
        >>> token = create_refresh_token({"sub": "user_id_123"})
        >>> print(token)
        "eyJhbGciOiJIUzI1NiIs..."
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at
        "type": "refresh"
    })
    
    # Encode JWT
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        Dict[str, Any]: Decoded token payload
        
    Raises:
        TokenExpiredError: If token has expired
        InvalidTokenError: If token is invalid or type doesn't match
        
    Example:
        >>> token = create_access_token({"sub": "user_id_123"})
        >>> payload = verify_token(token)
        >>> print(payload["sub"])
        "user_id_123"
    """
    try:
        # Decode JWT
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Check token type
        if payload.get("type") != token_type:
            logger.warning(f"Invalid token type: expected {token_type}, got {payload.get('type')}")
            raise InvalidTokenError(f"Invalid token type: expected {token_type}")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise TokenExpiredError("Token has expired")
        
    except JWTError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise InvalidTokenError(f"Invalid token: {str(e)}")


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token without verification.
    
    Useful for extracting payload when verification is not needed.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Dict[str, Any]: Decoded token payload or None if invalid
        
    Example:
        >>> token = create_access_token({"sub": "user_id_123"})
        >>> payload = decode_token(token)
        >>> print(payload["sub"])
        "user_id_123"
    """
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        return payload
    except Exception as e:
        logger.error(f"Error decoding token: {str(e)}")
        return None


def extract_token_payload(token: str) -> Dict[str, Any]:
    """
    Extract and verify token payload.
    
    Convenience function that verifies token and returns payload.
    
    Args:
        token: JWT token
        
    Returns:
        Dict[str, Any]: Token payload
        
    Raises:
        TokenExpiredError: If token has expired
        InvalidTokenError: If token is invalid
    """
    return verify_token(token)


def create_email_verification_token(email: str) -> str:
    """
    Create a token for email verification.
    
    Args:
        email: Email address to verify
        
    Returns:
        str: JWT token for email verification
        
    Example:
        >>> token = create_email_verification_token("user@example.com")
        >>> print(token)
        "eyJhbGciOiJIUzI1NiIs..."
    """
    # Email verification tokens expire in 24 hours
    expires_delta = timedelta(hours=24)
    data = {"sub": email, "purpose": "email_verification"}
    
    return create_access_token(data, expires_delta)


def verify_email_verification_token(token: str) -> str:
    """
    Verify email verification token and extract email.
    
    Args:
        token: JWT token for email verification
        
    Returns:
        str: Email address from token
        
    Raises:
        TokenExpiredError: If token has expired
        InvalidTokenError: If token is invalid or purpose doesn't match
    """
    payload = verify_token(token, token_type="access")
    
    # Check purpose
    if payload.get("purpose") != "email_verification":
        raise InvalidTokenError("Invalid token purpose")
    
    email = payload.get("sub")
    if not email:
        raise InvalidTokenError("Email not found in token")
    
    return email


def create_password_reset_token(email: str) -> str:
    """
    Create a token for password reset.
    
    Args:
        email: Email address for password reset
        
    Returns:
        str: JWT token for password reset
        
    Example:
        >>> token = create_password_reset_token("user@example.com")
        >>> print(token)
        "eyJhbGciOiJIUzI1NiIs..."
    """
    # Password reset tokens expire in 1 hour
    expires_delta = timedelta(hours=1)
    data = {"sub": email, "purpose": "password_reset"}
    
    return create_access_token(data, expires_delta)


def verify_password_reset_token(token: str) -> str:
    """
    Verify password reset token and extract email.
    
    Args:
        token: JWT token for password reset
        
    Returns:
        str: Email address from token
        
    Raises:
        TokenExpiredError: If token has expired
        InvalidTokenError: If token is invalid or purpose doesn't match
    """
    payload = verify_token(token, token_type="access")
    
    # Check purpose
    if payload.get("purpose") != "password_reset":
        raise InvalidTokenError("Invalid token purpose")
    
    email = payload.get("sub")
    if not email:
        raise InvalidTokenError("Email not found in token")
    
    return email

