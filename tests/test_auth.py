"""
Test suite for authentication module.

Tests registration, login, token refresh, email verification, and password reset.
"""

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from app.core.security import create_access_token, create_email_verification_token, create_password_reset_token


class TestRegistration:
    """Test user registration endpoints."""
    
    @pytest.mark.asyncio
    async def test_register_with_valid_data_returns_201(
        self,
        test_client: AsyncClient,
        mock_user_data: dict
    ):
        """Test successful user registration with valid data."""
        response = await test_client.post("/api/v1/auth/register", json=mock_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status_code"] == 201
        assert data["message"] == "User registered successfully"
        assert data["data"] is not None
        assert data["data"]["email"] == mock_user_data["email"].lower()
        assert "password" not in data["data"]
        assert data["error"] is None
    
    @pytest.mark.asyncio
    async def test_register_with_duplicate_email_returns_400(
        self,
        test_client: AsyncClient,
        mock_user_data: dict
    ):
        """Test registration with duplicate email fails."""
        # Register first user
        await test_client.post("/api/v1/auth/register", json=mock_user_data)
        
        # Try to register again with same email
        response = await test_client.post("/api/v1/auth/register", json=mock_user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["status_code"] == 400
        assert data["data"] is None
        assert data["error"] is not None
        assert data["error"]["code"] == "DUPLICATE_EMAIL"
    
    @pytest.mark.asyncio
    async def test_register_with_invalid_email_returns_422(
        self,
        test_client: AsyncClient,
        mock_user_data: dict
    ):
        """Test registration with invalid email format fails."""
        mock_user_data["email"] = "invalid-email"
        
        response = await test_client.post("/api/v1/auth/register", json=mock_user_data)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_with_weak_password_returns_422(
        self,
        test_client: AsyncClient,
        mock_user_data: dict
    ):
        """Test registration with weak password fails."""
        mock_user_data["password"] = "weak"
        
        response = await test_client.post("/api/v1/auth/register", json=mock_user_data)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_with_missing_required_fields_returns_422(
        self,
        test_client: AsyncClient
    ):
        """Test registration with missing required fields fails."""
        incomplete_data = {
            "email": "test@example.com"
            # Missing password, first_name, last_name, birthday
        }
        
        response = await test_client.post("/api/v1/auth/register", json=incomplete_data)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_with_invalid_birthday_returns_422(
        self,
        test_client: AsyncClient,
        mock_user_data: dict
    ):
        """Test registration with invalid birthday fails."""
        mock_user_data["birthday"] = {
            "day": 32,  # Invalid day
            "month": 13,  # Invalid month
            "year": 2030  # Future year
        }
        
        response = await test_client.post("/api/v1/auth/register", json=mock_user_data)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_with_underage_user_returns_422(
        self,
        test_client: AsyncClient,
        mock_user_data: dict
    ):
        """Test registration with user under 13 years old fails."""
        current_year = datetime.now().year
        mock_user_data["birthday"] = {
            "day": 1,
            "month": 1,
            "year": current_year - 10  # 10 years old
        }
        
        response = await test_client.post("/api/v1/auth/register", json=mock_user_data)
        
        assert response.status_code == 422


class TestLogin:
    """Test user login endpoints."""
    
    @pytest.mark.asyncio
    async def test_login_with_valid_credentials_returns_tokens(
        self,
        test_client: AsyncClient,
        verified_user: dict,
        mock_user_data: dict
    ):
        """Test successful login with valid credentials."""
        login_data = {
            "email": mock_user_data["email"],
            "password": mock_user_data["password"]
        }
        
        response = await test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["message"] == "Login successful"
        assert data["data"] is not None
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert data["error"] is None
    
    @pytest.mark.asyncio
    async def test_login_with_wrong_password_returns_401(
        self,
        test_client: AsyncClient,
        verified_user: dict,
        mock_user_data: dict
    ):
        """Test login with incorrect password fails."""
        login_data = {
            "email": mock_user_data["email"],
            "password": "WrongPassword123!"
        }
        
        response = await test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["status_code"] == 401
        assert data["data"] is None
        assert data["error"] is not None
        assert data["error"]["code"] == "INVALID_CREDENTIALS"
    
    @pytest.mark.asyncio
    async def test_login_with_nonexistent_email_returns_401(
        self,
        test_client: AsyncClient
    ):
        """Test login with non-existent email fails."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "TestPassword123!"
        }
        
        response = await test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["status_code"] == 401
        assert data["error"]["code"] == "INVALID_CREDENTIALS"
    
    @pytest.mark.asyncio
    async def test_login_with_unverified_email_returns_403(
        self,
        test_client: AsyncClient,
        registered_user: dict,
        mock_user_data: dict
    ):
        """Test login with unverified email fails."""
        login_data = {
            "email": mock_user_data["email"],
            "password": mock_user_data["password"]
        }
        
        response = await test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 403
        data = response.json()
        assert data["status_code"] == 403
        assert data["error"]["code"] == "UNVERIFIED_EMAIL"
    
    @pytest.mark.asyncio
    async def test_login_with_inactive_account_returns_403(
        self,
        test_client: AsyncClient,
        test_db: AsyncIOMotorDatabase,
        verified_user: dict,
        mock_user_data: dict
    ):
        """Test login with inactive account fails."""
        # Mark account as inactive
        await test_db["auth"].update_one(
            {"email": mock_user_data["email"].lower()},
            {"$set": {"is_active": False}}
        )
        
        login_data = {
            "email": mock_user_data["email"],
            "password": mock_user_data["password"]
        }
        
        response = await test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 403
        data = response.json()
        assert data["status_code"] == 403
        assert data["error"]["code"] == "INACTIVE_ACCOUNT"


class TestTokenRefresh:
    """Test token refresh endpoints."""
    
    @pytest.mark.asyncio
    async def test_refresh_token_with_valid_token_returns_new_access_token(
        self,
        test_client: AsyncClient,
        verified_user: dict,
        mock_user_data: dict
    ):
        """Test refreshing access token with valid refresh token."""
        # Login to get tokens
        login_data = {
            "email": mock_user_data["email"],
            "password": mock_user_data["password"]
        }
        login_response = await test_client.post("/api/v1/auth/login", json=login_data)
        refresh_token = login_response.json()["data"]["refresh_token"]
        
        # Refresh token
        refresh_data = {"refresh_token": refresh_token}
        response = await test_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["data"] is not None
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_refresh_token_with_expired_token_returns_401(
        self,
        test_client: AsyncClient,
        verified_user: dict
    ):
        """Test refreshing with expired token fails."""
        # Create expired token
        expired_token = create_access_token(
            {"sub": str(verified_user["data"]["id"])},
            expires_delta=timedelta(seconds=-1)
        )
        
        refresh_data = {"refresh_token": expired_token}
        response = await test_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "TOKEN_EXPIRED"
    
    @pytest.mark.asyncio
    async def test_refresh_token_with_invalid_token_returns_401(
        self,
        test_client: AsyncClient
    ):
        """Test refreshing with invalid token fails."""
        refresh_data = {"refresh_token": "invalid-token"}
        response = await test_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_TOKEN"


class TestEmailVerification:
    """Test email verification endpoints."""
    
    @pytest.mark.asyncio
    async def test_verify_email_with_valid_token_marks_verified(
        self,
        test_client: AsyncClient,
        test_db: AsyncIOMotorDatabase,
        registered_user: dict,
        mock_user_data: dict
    ):
        """Test email verification with valid token succeeds."""
        # Create verification token
        token = create_email_verification_token(mock_user_data["email"])
        
        # Verify email
        response = await test_client.get(f"/api/v1/auth/verify-email?token={token}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["message"] == "Email verified successfully"
        
        # Check database
        auth = await test_db["auth"].find_one({"email": mock_user_data["email"].lower()})
        assert auth["is_verified"] is True
    
    @pytest.mark.asyncio
    async def test_verify_email_with_invalid_token_returns_400(
        self,
        test_client: AsyncClient
    ):
        """Test email verification with invalid token fails."""
        response = await test_client.get("/api/v1/auth/verify-email?token=invalid-token")
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_TOKEN"
    
    @pytest.mark.asyncio
    async def test_verify_email_with_expired_token_returns_401(
        self,
        test_client: AsyncClient
    ):
        """Test email verification with expired token fails."""
        # Create expired token
        expired_token = create_access_token(
            {"sub": "test@example.com", "purpose": "email_verification"},
            expires_delta=timedelta(seconds=-1)
        )
        
        response = await test_client.get(f"/api/v1/auth/verify-email?token={expired_token}")
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "TOKEN_EXPIRED"


class TestPasswordReset:
    """Test password reset endpoints."""
    
    @pytest.mark.asyncio
    async def test_forgot_password_with_valid_email_sends_reset_link(
        self,
        test_client: AsyncClient,
        verified_user: dict,
        mock_user_data: dict
    ):
        """Test password reset request with valid email."""
        reset_data = {"email": mock_user_data["email"]}
        response = await test_client.post("/api/v1/auth/forgot-password", json=reset_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["message"] == "Password reset email sent"
    
    @pytest.mark.asyncio
    async def test_forgot_password_with_nonexistent_email_returns_404(
        self,
        test_client: AsyncClient
    ):
        """Test password reset request with non-existent email."""
        reset_data = {"email": "nonexistent@example.com"}
        response = await test_client.post("/api/v1/auth/forgot-password", json=reset_data)
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "USER_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_reset_password_with_valid_token_updates_password(
        self,
        test_client: AsyncClient,
        test_db: AsyncIOMotorDatabase,
        verified_user: dict,
        mock_user_data: dict
    ):
        """Test password reset with valid token succeeds."""
        # Create reset token
        token = create_password_reset_token(mock_user_data["email"])
        
        # Reset password
        new_password = "NewPassword123!"
        reset_data = {
            "token": token,
            "new_password": new_password
        }
        response = await test_client.post("/api/v1/auth/reset-password", json=reset_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["message"] == "Password reset successfully"
        
        # Try login with new password
        login_data = {
            "email": mock_user_data["email"],
            "password": new_password
        }
        login_response = await test_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_reset_password_with_invalid_token_returns_400(
        self,
        test_client: AsyncClient
    ):
        """Test password reset with invalid token fails."""
        reset_data = {
            "token": "invalid-token",
            "new_password": "NewPassword123!"
        }
        response = await test_client.post("/api/v1/auth/reset-password", json=reset_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_TOKEN"
    
    @pytest.mark.asyncio
    async def test_reset_password_with_weak_password_returns_422(
        self,
        test_client: AsyncClient,
        verified_user: dict,
        mock_user_data: dict
    ):
        """Test password reset with weak password fails."""
        token = create_password_reset_token(mock_user_data["email"])
        
        reset_data = {
            "token": token,
            "new_password": "weak"
        }
        response = await test_client.post("/api/v1/auth/reset-password", json=reset_data)
        
        assert response.status_code == 422

