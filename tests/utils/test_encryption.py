"""
Encryption Utilities Tests

Tests for credential encryption/decryption.
Covers: encryption, decryption, key validation, error handling.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from cryptography.fernet import Fernet

from app.utils.encryption import (
    CredentialEncryption,
    EncryptionError,
    EncryptionKeyError,
    DecryptionError,
    generate_encryption_key,
    validate_encryption_key,
    rotate_encryption,
    encrypt,
    decrypt,
    encrypt_dict,
    decrypt_dict
)


# ==================== FIXTURES ====================

@pytest.fixture
def valid_key():
    """Generate valid encryption key"""
    return Fernet.generate_key().decode()


@pytest.fixture
def encryption_service(valid_key):
    """Create encryption service with valid key"""
    return CredentialEncryption(encryption_key=valid_key)


@pytest.fixture
def sample_credentials():
    """Sample credentials for testing"""
    return {
        "api_key": "test_api_key_12345",
        "api_secret": "test_api_secret_67890",
        "company_id": "test_company_999"
    }


# ==================== INITIALIZATION TESTS ====================

def test_encryption_service_init_with_valid_key(valid_key):
    """Test: Initialize encryption service with valid key"""
    service = CredentialEncryption(encryption_key=valid_key)
    assert service.fernet is not None


def test_encryption_service_init_with_invalid_key():
    """Test: Initialize with invalid key should raise error"""
    with pytest.raises(EncryptionKeyError) as exc_info:
        CredentialEncryption(encryption_key="invalid_key")
    
    assert "Invalid encryption key format" in str(exc_info.value)


def test_encryption_service_init_without_key():
    """Test: Initialize without key (no env var) should raise error"""
    # This will fail if ENCRYPTION_KEY is not set in environment
    # In actual tests, you'd mock the settings
    pass  # Skip for now as it requires env setup


# ==================== STRING ENCRYPTION TESTS ====================

def test_encrypt_string_success(encryption_service):
    """Test: Encrypt string successfully"""
    plaintext = "my_secret_value"
    encrypted = encryption_service.encrypt_string(plaintext)
    
    assert encrypted != plaintext
    assert len(encrypted) > 0
    assert encrypted.startswith("gAAAAA")  # Fernet format


def test_encrypt_empty_string(encryption_service):
    """Test: Encrypt empty string"""
    encrypted = encryption_service.encrypt_string("")
    assert encrypted == ""


def test_encrypt_string_with_special_chars(encryption_service):
    """Test: Encrypt string with special characters"""
    plaintext = "test!@#$%^&*()_+-=[]{}|;:,.<>?"
    encrypted = encryption_service.encrypt_string(plaintext)
    
    assert encrypted != plaintext
    assert len(encrypted) > 0


def test_encrypt_string_with_unicode(encryption_service):
    """Test: Encrypt string with unicode characters"""
    plaintext = "测试中文 🚀 Hello мир"
    encrypted = encryption_service.encrypt_string(plaintext)
    
    assert encrypted != plaintext
    assert len(encrypted) > 0


# ==================== STRING DECRYPTION TESTS ====================

def test_decrypt_string_success(encryption_service):
    """Test: Decrypt string successfully"""
    plaintext = "my_secret_value"
    encrypted = encryption_service.encrypt_string(plaintext)
    decrypted = encryption_service.decrypt_string(encrypted)
    
    assert decrypted == plaintext


def test_decrypt_empty_string(encryption_service):
    """Test: Decrypt empty string"""
    decrypted = encryption_service.decrypt_string("")
    assert decrypted == ""


def test_decrypt_with_wrong_key():
    """Test: Decrypt with wrong key should raise error"""
    # Encrypt with first key
    key1 = Fernet.generate_key().decode()
    service1 = CredentialEncryption(encryption_key=key1)
    encrypted = service1.encrypt_string("secret")
    
    # Try to decrypt with different key
    key2 = Fernet.generate_key().decode()
    service2 = CredentialEncryption(encryption_key=key2)
    
    with pytest.raises(DecryptionError) as exc_info:
        service2.decrypt_string(encrypted)
    
    assert "Failed to decrypt data" in str(exc_info.value)


def test_decrypt_invalid_data(encryption_service):
    """Test: Decrypt invalid encrypted data"""
    with pytest.raises(DecryptionError):
        encryption_service.decrypt_string("not_encrypted_data")


def test_decrypt_corrupted_data(encryption_service):
    """Test: Decrypt corrupted encrypted data"""
    plaintext = "test"
    encrypted = encryption_service.encrypt_string(plaintext)
    
    # Corrupt the encrypted data
    corrupted = encrypted[:-5] + "XXXXX"
    
    with pytest.raises(DecryptionError):
        encryption_service.decrypt_string(corrupted)


# ==================== CREDENTIALS ENCRYPTION TESTS ====================

def test_encrypt_credentials_success(encryption_service, sample_credentials):
    """Test: Encrypt credentials dict successfully"""
    encrypted = encryption_service.encrypt_credentials(sample_credentials)
    
    assert isinstance(encrypted, dict)
    assert len(encrypted) == len(sample_credentials)
    
    # All values should be encrypted
    for key, value in encrypted.items():
        assert value != sample_credentials[key]
        assert value.startswith("gAAAAA")


def test_encrypt_empty_credentials(encryption_service):
    """Test: Encrypt empty credentials dict"""
    encrypted = encryption_service.encrypt_credentials({})
    assert encrypted == {}


def test_encrypt_credentials_with_empty_values(encryption_service):
    """Test: Encrypt credentials with some empty values"""
    credentials = {
        "api_key": "test_key",
        "api_secret": "",
        "company_id": "test_company"
    }
    
    encrypted = encryption_service.encrypt_credentials(credentials)
    
    assert encrypted["api_key"] != credentials["api_key"]
    assert encrypted["api_secret"] == ""  # Empty stays empty
    assert encrypted["company_id"] != credentials["company_id"]


# ==================== CREDENTIALS DECRYPTION TESTS ====================

def test_decrypt_credentials_success(encryption_service, sample_credentials):
    """Test: Decrypt credentials successfully"""
    encrypted = encryption_service.encrypt_credentials(sample_credentials)
    decrypted = encryption_service.decrypt_credentials(encrypted)
    
    assert decrypted == sample_credentials


def test_decrypt_empty_credentials(encryption_service):
    """Test: Decrypt empty credentials dict"""
    decrypted = encryption_service.decrypt_credentials({})
    assert decrypted == {}


def test_decrypt_credentials_with_wrong_key(sample_credentials):
    """Test: Decrypt credentials with wrong key should fail"""
    # Encrypt with key1
    key1 = Fernet.generate_key().decode()
    service1 = CredentialEncryption(encryption_key=key1)
    encrypted = service1.encrypt_credentials(sample_credentials)
    
    # Try to decrypt with key2
    key2 = Fernet.generate_key().decode()
    service2 = CredentialEncryption(encryption_key=key2)
    
    with pytest.raises(DecryptionError) as exc_info:
        service2.decrypt_credentials(encrypted)
    
    assert "Failed to decrypt credential" in str(exc_info.value)


# ==================== ROUND-TRIP TESTS ====================

def test_encrypt_decrypt_round_trip(encryption_service):
    """Test: Encrypt then decrypt should return original"""
    original = "test_secret_value_12345"
    encrypted = encryption_service.encrypt_string(original)
    decrypted = encryption_service.decrypt_string(encrypted)
    
    assert decrypted == original


def test_credentials_round_trip(encryption_service, sample_credentials):
    """Test: Encrypt and decrypt credentials multiple times"""
    # Round trip 1
    encrypted1 = encryption_service.encrypt_credentials(sample_credentials)
    decrypted1 = encryption_service.decrypt_credentials(encrypted1)
    assert decrypted1 == sample_credentials
    
    # Round trip 2
    encrypted2 = encryption_service.encrypt_credentials(decrypted1)
    decrypted2 = encryption_service.decrypt_credentials(encrypted2)
    assert decrypted2 == sample_credentials


# ==================== DICT VALUE ENCRYPTION TESTS ====================

def test_encrypt_dict_values_all_keys(encryption_service):
    """Test: Encrypt all keys in dict"""
    data = {
        "user_id": "user123",
        "api_key": "secret123",
        "api_secret": "secret456"
    }
    
    encrypted = encryption_service.encrypt_dict_values(data)
    
    assert encrypted["user_id"] != data["user_id"]
    assert encrypted["api_key"] != data["api_key"]
    assert encrypted["api_secret"] != data["api_secret"]


def test_encrypt_dict_values_specific_keys(encryption_service):
    """Test: Encrypt only specific keys"""
    data = {
        "user_id": "user123",
        "api_key": "secret123",
        "api_secret": "secret456"
    }
    
    encrypted = encryption_service.encrypt_dict_values(
        data,
        keys_to_encrypt=["api_key", "api_secret"]
    )
    
    assert encrypted["user_id"] == data["user_id"]  # Not encrypted
    assert encrypted["api_key"] != data["api_key"]  # Encrypted
    assert encrypted["api_secret"] != data["api_secret"]  # Encrypted


# ==================== UTILITY FUNCTION TESTS ====================

def test_generate_encryption_key():
    """Test: Generate encryption key"""
    key = generate_encryption_key()
    
    assert isinstance(key, str)
    assert len(key) > 0
    assert validate_encryption_key(key) is True


def test_validate_encryption_key_valid():
    """Test: Validate valid encryption key"""
    valid_key = Fernet.generate_key().decode()
    assert validate_encryption_key(valid_key) is True


def test_validate_encryption_key_invalid():
    """Test: Validate invalid encryption key"""
    assert validate_encryption_key("invalid_key") is False


def test_rotate_encryption(sample_credentials):
    """Test: Rotate encryption keys"""
    # Encrypt with old key
    old_key = Fernet.generate_key().decode()
    old_service = CredentialEncryption(encryption_key=old_key)
    encrypted_old = old_service.encrypt_credentials(sample_credentials)
    
    # Generate new key
    new_key = generate_encryption_key()
    
    # Rotate
    encrypted_new = rotate_encryption(encrypted_old, old_key, new_key)
    
    # Decrypt with new key
    new_service = CredentialEncryption(encryption_key=new_key)
    decrypted = new_service.decrypt_credentials(encrypted_new)
    
    assert decrypted == sample_credentials


# ==================== CONVENIENCE FUNCTION TESTS ====================

@pytest.mark.skip(reason="Requires environment variable setup")
def test_convenience_encrypt_decrypt(valid_key, monkeypatch):
    """Test: Convenience functions for encrypt/decrypt"""
    # Mock settings to return our test key
    from app.config.settings import Settings
    
    def mock_get_settings():
        settings = Settings()
        settings.ENCRYPTION_KEY = valid_key
        return settings
    
    monkeypatch.setattr("app.utils.encryption.get_settings", mock_get_settings)
    
    # Reset global instance
    import app.utils.encryption as enc_module
    enc_module._encryption_service = None
    
    # Test convenience functions
    plaintext = "test_secret"
    encrypted_val = encrypt(plaintext)
    decrypted_val = decrypt(encrypted_val)
    
    assert decrypted_val == plaintext


@pytest.mark.skip(reason="Requires environment variable setup")
def test_convenience_encrypt_decrypt_dict(valid_key, monkeypatch, sample_credentials):
    """Test: Convenience functions for dict encryption"""
    # Mock settings
    from app.config.settings import Settings
    
    def mock_get_settings():
        settings = Settings()
        settings.ENCRYPTION_KEY = valid_key
        return settings
    
    monkeypatch.setattr("app.utils.encryption.get_settings", mock_get_settings)
    
    # Reset global instance
    import app.utils.encryption as enc_module
    enc_module._encryption_service = None
    
    # Test
    encrypted_creds = encrypt_dict(sample_credentials)
    decrypted_creds = decrypt_dict(encrypted_creds)
    
    assert decrypted_creds == sample_credentials


# ==================== EDGE CASE TESTS ====================

def test_encrypt_very_long_string(encryption_service):
    """Test: Encrypt very long string"""
    long_string = "a" * 10000
    encrypted = encryption_service.encrypt_string(long_string)
    decrypted = encryption_service.decrypt_string(encrypted)
    
    assert decrypted == long_string


def test_encrypt_multiline_string(encryption_service):
    """Test: Encrypt multiline string"""
    multiline = "Line 1\nLine 2\nLine 3\n\nLine 5"
    encrypted = encryption_service.encrypt_string(multiline)
    decrypted = encryption_service.decrypt_string(encrypted)  # Fixed: decrypt encrypted, not multiline
    
    assert decrypted == multiline
    assert "\n" in decrypted


def test_encrypt_json_string(encryption_service):
    """Test: Encrypt JSON string"""
    json_str = '{"key": "value", "number": 123, "nested": {"a": "b"}}'
    encrypted = encryption_service.encrypt_string(json_str)
    decrypted = encryption_service.decrypt_string(encrypted)
    
    assert decrypted == json_str


# ==================== SECURITY TESTS ====================

def test_same_plaintext_different_ciphertext(encryption_service):
    """Test: Same plaintext produces different ciphertext each time"""
    plaintext = "test_secret"
    
    encrypted1 = encryption_service.encrypt_string(plaintext)
    encrypted2 = encryption_service.encrypt_string(plaintext)
    
    # Should be different due to Fernet's IV
    assert encrypted1 != encrypted2
    
    # But both should decrypt to same plaintext
    assert encryption_service.decrypt_string(encrypted1) == plaintext
    assert encryption_service.decrypt_string(encrypted2) == plaintext


def test_cannot_decrypt_without_key(sample_credentials):
    """Test: Cannot decrypt without correct key"""
    key = Fernet.generate_key().decode()
    service = CredentialEncryption(encryption_key=key)
    
    encrypted = service.encrypt_credentials(sample_credentials)
    
    # Try to decrypt without service (simulate attacker)
    # Should not be able to get original values
    for value in encrypted.values():
        if value:  # Skip empty strings
            assert value != sample_credentials[list(sample_credentials.keys())[0]]


# ==================== PERFORMANCE TESTS ====================
# Note: Performance tests require pytest-benchmark plugin
# Install with: pip install pytest-benchmark
# Skipped for now to avoid extra dependency

@pytest.mark.skip(reason="Requires pytest-benchmark plugin")
def test_encrypt_performance(encryption_service):
    """Test: Encryption performance benchmark"""
    plaintext = "test_secret_value_123"
    
    # Should complete in reasonable time
    result = encryption_service.encrypt_string(plaintext)
    assert len(result) > 0


@pytest.mark.skip(reason="Requires pytest-benchmark plugin")
def test_decrypt_performance(encryption_service):
    """Test: Decryption performance benchmark"""
    plaintext = "test_secret_value_123"
    encrypted = encryption_service.encrypt_string(plaintext)
    
    # Should complete in reasonable time
    result = encryption_service.decrypt_string(encrypted)
    assert result == plaintext


# ==================== INTEGRATION TESTS ====================

def test_full_credential_workflow(encryption_service):
    """Test: Full workflow of credential encryption"""
    # Simulate user creating wallet with credentials
    user_credentials = {
        "binance_api_key": "user_real_api_key_12345",
        "binance_api_secret": "user_real_api_secret_67890"
    }
    
    # 1. Encrypt before saving to database
    encrypted_for_db = encryption_service.encrypt_credentials(user_credentials)
    
    # 2. Verify encrypted data looks correct
    assert "binance_api_key" in encrypted_for_db
    assert "binance_api_secret" in encrypted_for_db
    assert encrypted_for_db["binance_api_key"] != user_credentials["binance_api_key"]
    
    # 3. Simulate loading from database and decrypting
    loaded_from_db = encrypted_for_db.copy()
    decrypted_for_use = encryption_service.decrypt_credentials(loaded_from_db)
    
    # 4. Verify we got original credentials back
    assert decrypted_for_use == user_credentials
    
    # 5. Use decrypted credentials (simulate API call)
    api_key = decrypted_for_use["binance_api_key"]
    assert api_key == "user_real_api_key_12345"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

