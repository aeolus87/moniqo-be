"""
Application settings using Pydantic Settings.

Loads configuration from environment variables with validation.
"""

from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings are loaded from .env file or environment variables.
    Uses Pydantic for validation and type checking.
    """
    
    # App Configuration
    APP_NAME: str = Field(default="AI Agent Trading Platform")
    APP_VERSION: str = Field(default="1.0.0")
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    
    # Server
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    # Database
    MONGODB_URL: str = Field(..., description="MongoDB connection string")
    MONGODB_DB_NAME: str = Field(..., description="MongoDB database name")
    
    # Redis
    REDIS_URL: str = Field(..., description="Redis connection string")
    REDIS_TTL_SECONDS: int = Field(default=86400)
    
    # JWT Authentication
    JWT_SECRET_KEY: str = Field(..., description="Secret key for JWT tokens")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    
    # Email Auto-Verification
    AUTO_VERIFY_EMAIL: bool = Field(default=False)
    
    # Superadmin
    SUPERADMIN_EMAIL: str = Field(..., description="Superadmin email")
    SUPERADMIN_PASSWORD: str = Field(..., description="Superadmin password")
    SUPERADMIN_FIRST_NAME: str = Field(default="Super")
    SUPERADMIN_LAST_NAME: str = Field(default="Admin")
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = Field(..., description="AWS access key")
    AWS_SECRET_ACCESS_KEY: str = Field(..., description="AWS secret key")
    AWS_REGION: str = Field(default="us-east-1")
    AWS_S3_BUCKET_NAME: str = Field(..., description="S3 bucket name")
    
    # File Upload Limits
    MAX_AVATAR_SIZE_MB: int = Field(default=5)
    ALLOWED_AVATAR_TYPES: List[str] = Field(default=["image/jpeg", "image/png", "image/gif"])
    
    # Resend Email
    RESEND_API_KEY: str = Field(..., description="Resend API key")
    FROM_EMAIL: str = Field(..., description="From email address")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=100)
    ADMIN_RATE_LIMIT_ENABLED: bool = Field(default=False)
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = Field(default=10)
    MAX_PAGE_SIZE: int = Field(default=5000)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE_PATH: str = Field(default="logs/app.log")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000", "http://localhost:5173"])
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        elif isinstance(v, list):
            return v
        return []
    
    @field_validator("ALLOWED_AVATAR_TYPES", mode="before")
    @classmethod
    def parse_allowed_avatar_types(cls, v) -> List[str]:
        """Parse allowed avatar types from comma-separated string or list."""
        if isinstance(v, str):
            return [mime_type.strip() for mime_type in v.split(",")]
        elif isinstance(v, list):
            return v
        return []
    
    @field_validator("MAX_AVATAR_SIZE_MB")
    @classmethod
    def validate_max_avatar_size(cls, v: int) -> int:
        """Validate max avatar size is positive."""
        if v <= 0:
            raise ValueError("MAX_AVATAR_SIZE_MB must be positive")
        return v
    
    @field_validator("RATE_LIMIT_PER_MINUTE")
    @classmethod
    def validate_rate_limit(cls, v: int) -> int:
        """Validate rate limit is positive."""
        if v <= 0:
            raise ValueError("RATE_LIMIT_PER_MINUTE must be positive")
        return v
    
    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_access_token_expire(cls, v: int) -> int:
        """Validate access token expiration is positive."""
        if v <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
        return v
    
    @field_validator("REFRESH_TOKEN_EXPIRE_DAYS")
    @classmethod
    def validate_refresh_token_expire(cls, v: int) -> int:
        """Validate refresh token expiration is positive."""
        if v <= 0:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be positive")
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Global settings instance
def get_settings() -> Settings:
    """Get settings instance (lazy loading)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

_settings: Settings | None = None

# Try to initialize settings on import
try:
    settings = Settings()
except Exception as e:
    # If .env file doesn't exist or required fields are missing,
    # settings will be None and should be initialized later
    print(f"Warning: Could not load settings: {str(e)}")
    print("Please create .env file with required configuration")
    settings = None  # type: ignore

