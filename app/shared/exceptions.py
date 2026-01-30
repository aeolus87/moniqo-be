"""
Custom exception classes for the application.

All custom exceptions inherit from base AppException for consistent error handling.
"""

from typing import Optional


class AppException(Exception):
    """
    Base application exception.
    
    All custom exceptions should inherit from this class.
    
    Attributes:
        message: Error message
        code: Error code
        status_code: HTTP status code
    """
    
    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500
    ):
        """
        Initialize AppException.
        
        Args:
            message: Error message
            code: Error code
            status_code: HTTP status code
        """
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


# Authentication & Authorization Exceptions

class AuthenticationError(AppException):
    """Authentication failed."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, code="AUTHENTICATION_ERROR", status_code=401)


class InvalidCredentialsError(AppException):
    """Invalid email or password."""
    
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message=message, code="INVALID_CREDENTIALS", status_code=401)


class TokenExpiredError(AppException):
    """JWT token has expired."""
    
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message=message, code="TOKEN_EXPIRED", status_code=401)


class InvalidTokenError(AppException):
    """Invalid JWT token."""
    
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message=message, code="INVALID_TOKEN", status_code=401)


class UnverifiedEmailError(AppException):
    """Email is not verified."""
    
    def __init__(self, message: str = "Email is not verified"):
        super().__init__(message=message, code="UNVERIFIED_EMAIL", status_code=403)


class InactiveAccountError(AppException):
    """Account is inactive."""
    
    def __init__(self, message: str = "Account is inactive"):
        super().__init__(message=message, code="INACTIVE_ACCOUNT", status_code=403)


class PermissionDeniedError(AppException):
    """Permission denied."""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message=message, code="PERMISSION_DENIED", status_code=403)


class InsufficientPermissionsError(AppException):
    """User does not have required permissions."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, code="INSUFFICIENT_PERMISSIONS", status_code=403)


# Validation Exceptions

class ValidationError(AppException):
    """Validation error."""
    
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=422)


class DuplicateEmailError(AppException):
    """Email already exists."""
    
    def __init__(self, message: str = "Email already exists"):
        super().__init__(message=message, code="DUPLICATE_EMAIL", status_code=400)


class DuplicateResourceError(AppException):
    """Resource already exists."""
    
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message=message, code="DUPLICATE_RESOURCE", status_code=400)


class ResourceNotFoundError(AppException):
    """Resource not found."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, code="RESOURCE_NOT_FOUND", status_code=404)


class InvalidFileTypeError(AppException):
    """Invalid file type."""
    
    def __init__(self, message: str = "Invalid file type"):
        super().__init__(message=message, code="INVALID_FILE_TYPE", status_code=422)


class FileTooLargeError(AppException):
    """File size exceeds limit."""
    
    def __init__(self, message: str = "File size exceeds limit"):
        super().__init__(message=message, code="FILE_TOO_LARGE", status_code=413)


class WeakPasswordError(AppException):
    """Password is too weak."""
    
    def __init__(self, message: str = "Password is too weak"):
        super().__init__(message=message, code="WEAK_PASSWORD", status_code=422)


# Resource Exceptions

class NotFoundError(AppException):
    """Resource not found."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, code="NOT_FOUND", status_code=404)


class UserNotFoundError(AppException):
    """User not found."""
    
    def __init__(self, message: str = "User not found"):
        super().__init__(message=message, code="USER_NOT_FOUND", status_code=404)


class RoleNotFoundError(AppException):
    """Role not found."""
    
    def __init__(self, message: str = "Role not found"):
        super().__init__(message=message, code="ROLE_NOT_FOUND", status_code=404)


class PermissionNotFoundError(AppException):
    """Permission not found."""
    
    def __init__(self, message: str = "Permission not found"):
        super().__init__(message=message, code="PERMISSION_NOT_FOUND", status_code=404)


class PlanNotFoundError(AppException):
    """Plan not found."""
    
    def __init__(self, message: str = "Plan not found"):
        super().__init__(message=message, code="PLAN_NOT_FOUND", status_code=404)


# Rate Limiting

class RateLimitExceededError(AppException):
    """Rate limit exceeded."""
    
    def __init__(self, message: str = "Too many requests"):
        super().__init__(message=message, code="RATE_LIMIT_EXCEEDED", status_code=429)


# External Service Exceptions

class EmailServiceError(AppException):
    """Email service error."""
    
    def __init__(self, message: str = "Failed to send email"):
        super().__init__(message=message, code="EMAIL_SERVICE_ERROR", status_code=500)


class StorageServiceError(AppException):
    """Storage service error (S3)."""
    
    def __init__(self, message: str = "Storage service error"):
        super().__init__(message=message, code="STORAGE_SERVICE_ERROR", status_code=500)


# Database Exceptions

class DatabaseError(AppException):
    """Database error."""
    
    def __init__(self, message: str = "Database error"):
        super().__init__(message=message, code="DATABASE_ERROR", status_code=500)


class DatabaseAuthorizationError(AppException):
    """Database authorization error - user lacks required permissions."""
    
    def __init__(self, message: str = "Database authorization failed. Please check MongoDB user permissions."):
        super().__init__(
            message=message,
            code="DATABASE_AUTHORIZATION_ERROR",
            status_code=503
        )


# General Exceptions

class BadRequestError(AppException):
    """Bad request."""
    
    def __init__(self, message: str = "Bad request"):
        super().__init__(message=message, code="BAD_REQUEST", status_code=400)


class InternalServerError(AppException):
    """Internal server error."""
    
    def __init__(self, message: str = "Internal server error"):
        super().__init__(message=message, code="INTERNAL_SERVER_ERROR", status_code=500)
