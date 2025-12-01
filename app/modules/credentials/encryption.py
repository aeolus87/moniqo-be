"""
Credentials encryption utilities.

Handles encryption/decryption of sensitive credential data using Fernet.
"""

from cryptography.fernet import Fernet
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_fernet_key() -> bytes:
    """
    Get encryption key from settings.
    
    Returns:
        bytes: Fernet encryption key
        
    Raises:
        ValueError: If ENCRYPTION_KEY not set in environment
    """
    settings = get_settings()
    if not settings.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY not set in environment")
    return settings.ENCRYPTION_KEY.encode()


def encrypt_value(value: str) -> str:
    """
    Encrypt a single value.
    
    Args:
        value: Plain text value to encrypt
        
    Returns:
        str: Encrypted value (base64 encoded)
        
    Raises:
        ValueError: If encryption fails
    """
    try:
        f = Fernet(get_fernet_key())
        encrypted_bytes = f.encrypt(value.encode())
        return encrypted_bytes.decode()
    except Exception as e:
        logger.error(f"Failed to encrypt value: {str(e)}")
        raise ValueError(f"Encryption failed: {str(e)}")


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt a single value.
    
    Args:
        encrypted_value: Encrypted value (base64 encoded)
        
    Returns:
        str: Decrypted plain text value
        
    Raises:
        ValueError: If decryption fails
    """
    try:
        f = Fernet(get_fernet_key())
        decrypted_bytes = f.decrypt(encrypted_value.encode())
        return decrypted_bytes.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt value: {str(e)}")
        raise ValueError(f"Decryption failed: {str(e)}")


def encrypt_credentials(
    credentials: dict,
    auth_fields: list
) -> dict:
    """
    Encrypt credentials based on wallet auth_fields specification.
    
    Args:
        credentials: Raw credentials dict
        auth_fields: List of auth field definitions from wallet
        
    Returns:
        dict: Credentials with encrypted fields
        
    Raises:
        ValueError: If encryption fails
    """
    encrypted = {}
    
    # Create a lookup for auth_fields by key
    auth_field_map = {field["key"]: field for field in auth_fields}
    
    for key, value in credentials.items():
        if value is None:
            continue
        
        # Get auth field definition
        field_def = auth_field_map.get(key)
        
        if field_def and field_def.get("encrypted", False):
            # Encrypt this field
            encrypted[key] = encrypt_value(str(value))
        else:
            # Store as plain text
            encrypted[key] = value
    
    return encrypted


def decrypt_credentials(
    credentials: dict,
    auth_fields: list
) -> dict:
    """
    Decrypt credentials based on wallet auth_fields specification.
    
    Args:
        credentials: Encrypted credentials dict
        auth_fields: List of auth field definitions from wallet
        
    Returns:
        dict: Credentials with decrypted fields
        
    Raises:
        ValueError: If decryption fails
    """
    decrypted = {}
    
    # Create a lookup for auth_fields by key
    auth_field_map = {field["key"]: field for field in auth_fields}
    
    for key, value in credentials.items():
        if value is None:
            continue
        
        # Get auth field definition
        field_def = auth_field_map.get(key)
        
        if field_def and field_def.get("encrypted", False):
            # Decrypt this field
            try:
                decrypted[key] = decrypt_value(str(value))
            except Exception as e:
                logger.warning(f"Failed to decrypt field {key}: {str(e)}")
                # Keep encrypted value if decryption fails
                decrypted[key] = value
        else:
            # Keep as plain text
            decrypted[key] = value
    
    return decrypted
