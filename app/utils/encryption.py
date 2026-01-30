"""
Encryption Utilities

Secure encryption/decryption for sensitive data (API keys, secrets).
Uses Fernet (symmetric encryption) from cryptography library.

**CRITICAL SECURITY NOTES:**
- Encryption key MUST be in environment variables
- NEVER hardcode encryption key
- Key should be 32 url-safe base64-encoded bytes
- Use different keys for dev/staging/production
- Rotate keys periodically

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import os
import base64
from typing import Dict, Optional
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption errors"""
    pass


class EncryptionKeyError(EncryptionError):
    """Encryption key not configured or invalid"""
    pass


class DecryptionError(EncryptionError):
    """Failed to decrypt data (invalid key or corrupted data)"""
    pass


class CredentialEncryption:
    """
    Credential encryption/decryption service.
    
    Uses Fernet (symmetric encryption) from cryptography library.
    Fernet guarantees that a message encrypted cannot be
    manipulated or read without the key.
    
    Usage:
        # Initialize
        encryption = CredentialEncryption()
        
        # Encrypt credentials
        encrypted = encryption.encrypt_credentials({
            "api_key": "my_secret_key",
            "api_secret": "my_secret_value"
        })
        
        # Decrypt credentials
        decrypted = encryption.decrypt_credentials(encrypted)
        print(decrypted["api_key"])  # "my_secret_key"
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service.
        
        Args:
            encryption_key: Base64-encoded Fernet key (optional)
                           If not provided, loads from environment
        
        Raises:
            EncryptionKeyError: If key is invalid or not found
        """
        # Get encryption key
        if encryption_key is None:
            settings = get_settings()
            encryption_key = settings.ENCRYPTION_KEY
        
        if not encryption_key:
            raise EncryptionKeyError(
                "Encryption key not configured. "
                "Set ENCRYPTION_KEY in environment variables. "
                "Generate key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        # Validate and create Fernet instance
        try:
            self.fernet = Fernet(encryption_key.encode())
        except Exception as e:
            raise EncryptionKeyError(
                f"Invalid encryption key format: {str(e)}. "
                "Key must be 32 url-safe base64-encoded bytes. "
                "Generate new key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        logger.debug("Encryption service initialized")
    
    def encrypt_string(self, plaintext: str) -> str:
        """
        Encrypt a single string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
            
        Example:
            encrypted = encryption.encrypt_string("my_secret_api_key")
            # Returns: "gAAAAABf..."
        """
        if not plaintext:
            return ""
        
        try:
            encrypted_bytes = self.fernet.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise EncryptionError(f"Failed to encrypt data: {str(e)}")
    
    def decrypt_string(self, encrypted: str) -> str:
        """
        Decrypt a single string.
        
        Args:
            encrypted: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext
            
        Raises:
            DecryptionError: If decryption fails (wrong key or corrupted data)
            
        Example:
            decrypted = encryption.decrypt_string("gAAAAABf...")
            # Returns: "my_secret_api_key"
        """
        if not encrypted:
            return ""
        
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            logger.error("Decryption failed: Invalid token (wrong key or corrupted data)")
            raise DecryptionError(
                "Failed to decrypt data. The encryption key may be incorrect, "
                "or the data may be corrupted."
            )
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise DecryptionError(f"Failed to decrypt data: {str(e)}")
    
    def encrypt_credentials(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """
        Encrypt a dictionary of credentials.
        
        Args:
            credentials: Dict of credential key-value pairs
            
        Returns:
            Dict with same keys but encrypted values
            
        Example:
            plaintext = {
                "api_key": "abcdef123456",
                "api_secret": "secret_value_here"
            }
            
            encrypted = encryption.encrypt_credentials(plaintext)
            # Returns: {
            #     "api_key": "gAAAAABf...",
            #     "api_secret": "gAAAAABf..."
            # }
        """
        if not credentials:
            return {}
        
        encrypted = {}
        
        for key, value in credentials.items():
            if value:  # Only encrypt non-empty values
                try:
                    encrypted[key] = self.encrypt_string(value)
                except Exception as e:
                    logger.error(f"Failed to encrypt credential '{key}': {str(e)}")
                    raise EncryptionError(
                        f"Failed to encrypt credential '{key}': {str(e)}"
                    )
            else:
                encrypted[key] = value  # Keep empty strings as-is
        
        logger.debug(f"Encrypted {len(encrypted)} credentials")
        return encrypted
    
    def decrypt_credentials(self, encrypted_credentials: Dict[str, str]) -> Dict[str, str]:
        """
        Decrypt a dictionary of encrypted credentials.
        
        Args:
            encrypted_credentials: Dict with encrypted values
            
        Returns:
            Dict with same keys but decrypted values
            
        Raises:
            DecryptionError: If any decryption fails
            
        Example:
            encrypted = {
                "api_key": "gAAAAABf...",
                "api_secret": "gAAAAABf..."
            }
            
            decrypted = encryption.decrypt_credentials(encrypted)
            # Returns: {
            #     "api_key": "abcdef123456",
            #     "api_secret": "secret_value_here"
            # }
        """
        if not encrypted_credentials:
            return {}
        
        decrypted = {}
        
        for key, value in encrypted_credentials.items():
            if value:  # Only decrypt non-empty values
                try:
                    decrypted[key] = self.decrypt_string(value)
                except Exception as e:
                    logger.error(f"Failed to decrypt credential '{key}': {str(e)}")
                    raise DecryptionError(
                        f"Failed to decrypt credential '{key}'. "
                        "The encryption key may have changed, or the data is corrupted."
                    )
            else:
                decrypted[key] = value  # Keep empty strings as-is
        
        logger.debug(f"Decrypted {len(decrypted)} credentials")
        return decrypted
    
    def encrypt_dict_values(
        self,
        data: Dict[str, str],
        keys_to_encrypt: Optional[list] = None
    ) -> Dict[str, str]:
        """
        Encrypt specific keys in a dictionary.
        
        Args:
            data: Dictionary with mixed values
            keys_to_encrypt: List of keys to encrypt (None = encrypt all)
            
        Returns:
            Dict with specified keys encrypted, others unchanged
            
        Example:
            data = {
                "user_id": "12345",
                "api_key": "secret_key",
                "api_secret": "secret_value"
            }
            
            encrypted = encryption.encrypt_dict_values(
                data,
                keys_to_encrypt=["api_key", "api_secret"]
            )
            # Returns: {
            #     "user_id": "12345",  # unchanged
            #     "api_key": "gAAAAABf...",
            #     "api_secret": "gAAAAABf..."
            # }
        """
        if not data:
            return {}
        
        result = data.copy()
        
        # Determine which keys to encrypt
        if keys_to_encrypt is None:
            keys_to_encrypt = list(data.keys())
        
        # Encrypt specified keys
        for key in keys_to_encrypt:
            if key in result and result[key]:
                result[key] = self.encrypt_string(result[key])
        
        return result
    
    def decrypt_dict_values(
        self,
        data: Dict[str, str],
        keys_to_decrypt: Optional[list] = None
    ) -> Dict[str, str]:
        """
        Decrypt specific keys in a dictionary.
        
        Args:
            data: Dictionary with mixed values
            keys_to_decrypt: List of keys to decrypt (None = decrypt all)
            
        Returns:
            Dict with specified keys decrypted, others unchanged
        """
        if not data:
            return {}
        
        result = data.copy()
        
        # Determine which keys to decrypt
        if keys_to_decrypt is None:
            keys_to_decrypt = list(data.keys())
        
        # Decrypt specified keys
        for key in keys_to_decrypt:
            if key in result and result[key]:
                result[key] = self.decrypt_string(result[key])
        
        return result


# ==================== UTILITY FUNCTIONS ====================

def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        Base64-encoded 32-byte key
        
    Example:
        key = generate_encryption_key()
        print(f"New encryption key: {key}")
        # Add to .env: ENCRYPTION_KEY={key}
    """
    key = Fernet.generate_key()
    return key.decode()


def validate_encryption_key(key: str) -> bool:
    """
    Validate if an encryption key is valid.
    
    Args:
        key: Base64-encoded Fernet key
        
    Returns:
        True if valid, False otherwise
        
    Example:
        is_valid = validate_encryption_key(my_key)
        if not is_valid:
            print("Invalid key!")
    """
    try:
        Fernet(key.encode())
        return True
    except Exception:
        return False


def rotate_encryption(
    encrypted_data: Dict[str, str],
    old_key: str,
    new_key: str
) -> Dict[str, str]:
    """
    Rotate encryption keys.
    
    Decrypts data with old key, re-encrypts with new key.
    Use this when rotating encryption keys periodically.
    
    Args:
        encrypted_data: Dict encrypted with old key
        old_key: Old encryption key
        new_key: New encryption key
        
    Returns:
        Dict re-encrypted with new key
        
    Example:
        # Rotate keys for security
        old_key = os.getenv("OLD_ENCRYPTION_KEY")
        new_key = generate_encryption_key()
        
        user_wallets = db.user_wallets.find({})
        for wallet in user_wallets:
            wallet["credentials"] = rotate_encryption(
                wallet["credentials"],
                old_key,
                new_key
            )
            db.user_wallets.update_one(
                {"_id": wallet["_id"]},
                {"$set": {"credentials": wallet["credentials"]}}
            )
        
        # Update environment with new key
        print(f"New key: {new_key}")
    """
    # Decrypt with old key
    old_encryption = CredentialEncryption(old_key)
    decrypted = old_encryption.decrypt_credentials(encrypted_data)
    
    # Encrypt with new key
    new_encryption = CredentialEncryption(new_key)
    re_encrypted = new_encryption.encrypt_credentials(decrypted)
    
    return re_encrypted


# ==================== GLOBAL INSTANCE ====================

_encryption_service = None


def get_encryption_service() -> CredentialEncryption:
    """
    Get global encryption service instance (singleton).
    
    Returns:
        Shared CredentialEncryption instance
        
    Usage:
        encryption = get_encryption_service()
        encrypted = encryption.encrypt_string("my_secret")
    """
    global _encryption_service
    
    if _encryption_service is None:
        _encryption_service = CredentialEncryption()
    
    return _encryption_service


# ==================== CONVENIENCE FUNCTIONS ====================

def encrypt(data: str) -> str:
    """
    Convenience function: Encrypt a string.
    
    Example:
        from app.utils.encryption import encrypt, decrypt
        
        encrypted = encrypt("my_api_key")
        decrypted = decrypt(encrypted)
    """
    return get_encryption_service().encrypt_string(data)


def decrypt(data: str) -> str:
    """
    Convenience function: Decrypt a string.
    """
    return get_encryption_service().decrypt_string(data)


def encrypt_dict(data: Dict[str, str]) -> Dict[str, str]:
    """
    Convenience function: Encrypt dict values.
    """
    return get_encryption_service().encrypt_credentials(data)


def decrypt_dict(data: Dict[str, str]) -> Dict[str, str]:
    """
    Convenience function: Decrypt dict values.
    """
    return get_encryption_service().decrypt_credentials(data)


# ==================== CLI TOOL ====================

if __name__ == "__main__":
    """
    CLI tool for encryption key management.
    
    Usage:
        # Generate new key
        python -m app.utils.encryption generate
        
        # Test key
        python -m app.utils.encryption test YOUR_KEY_HERE
        
        # Encrypt string
        python -m app.utils.encryption encrypt "my_secret_value"
        
        # Decrypt string
        python -m app.utils.encryption decrypt "gAAAAABf..."
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m app.utils.encryption generate")
        print("  python -m app.utils.encryption test <key>")
        print("  python -m app.utils.encryption encrypt <plaintext>")
        print("  python -m app.utils.encryption decrypt <encrypted>")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "generate":
        key = generate_encryption_key()
        print(f"Generated encryption key:")
        print(key)
        print()
        print("Add to .env file:")
        print(f"ENCRYPTION_KEY={key}")
    
    elif command == "test":
        if len(sys.argv) < 3:
            print("Usage: python -m app.utils.encryption test <key>")
            sys.exit(1)
        
        key = sys.argv[2]
        is_valid = test_encryption_key(key)
        
        if is_valid:
            print("✅ Key is valid!")
        else:
            print("❌ Key is invalid!")
    
    elif command == "encrypt":
        if len(sys.argv) < 3:
            print("Usage: python -m app.utils.encryption encrypt <plaintext>")
            sys.exit(1)
        
        plaintext = sys.argv[2]
        encrypted = encrypt(plaintext)
        print(f"Encrypted: {encrypted}")
    
    elif command == "decrypt":
        if len(sys.argv) < 3:
            print("Usage: python -m app.utils.encryption decrypt <encrypted>")
            sys.exit(1)
        
        encrypted_text = sys.argv[2]
        
        try:
            decrypted = decrypt(encrypted_text)
            print(f"Decrypted: {decrypted}")
        except DecryptionError as e:
            print(f"❌ Decryption failed: {str(e)}")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

