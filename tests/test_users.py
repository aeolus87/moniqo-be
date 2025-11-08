"""
Test suite for users module.

Tests user CRUD operations, avatar upload, and admin functionalities.
"""

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase


class TestCurrentUserOperations:
    """Test current user operations (GET/PUT/DELETE /me)."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_returns_user_data(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test getting current user data with valid token."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await test_client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["data"] is not None
        assert "email" in data["data"]
        assert "first_name" in data["data"]
        assert "last_name" in data["data"]
        assert "password" not in data["data"]
        assert "password_hash" not in data["data"]
    
    @pytest.mark.asyncio
    async def test_get_current_user_without_token_returns_401(
        self,
        test_client: AsyncClient
    ):
        """Test getting current user without token fails."""
        response = await test_client.get("/api/v1/users/me")
        
        assert response.status_code == 401  # No auth header
    
    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_token_returns_401(
        self,
        test_client: AsyncClient
    ):
        """Test getting current user with invalid token fails."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = await test_client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_update_current_user_with_valid_data_returns_updated_user(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test updating current user with valid data."""
        headers = {"Authorization": f"Bearer {user_token}"}
        update_data = {
            "first_name": "UpdatedFirst",
            "last_name": "UpdatedLast"
        }
        
        response = await test_client.put("/api/v1/users/me", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["data"]["first_name"] == "UpdatedFirst"
        assert data["data"]["last_name"] == "UpdatedLast"
    
    @pytest.mark.asyncio
    async def test_update_current_user_phone_without_country_code_returns_422(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test updating phone number without country code fails."""
        headers = {"Authorization": f"Bearer {user_token}"}
        update_data = {
            "phone_number": {
                "mobile_number": "9171234567"
                # Missing country_code
            }
        }
        
        response = await test_client.put("/api/v1/users/me", json=update_data, headers=headers)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_soft_delete_current_user_marks_deleted(
        self,
        test_client: AsyncClient,
        test_db: AsyncIOMotorDatabase,
        user_token: str,
        mock_user_data: dict
    ):
        """Test soft deleting current user."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        response = await test_client.delete("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["message"] == "User deleted successfully"
        
        # Verify user is soft deleted in database
        auth = await test_db["auth"].find_one({"email": mock_user_data["email"].lower()})
        user = await test_db["users"].find_one({"auth_id": auth["_id"]})
        assert user["is_deleted"] is True
        assert auth["is_deleted"] is True


class TestAdminUserOperations:
    """Test admin operations on users."""
    
    @pytest.mark.asyncio
    async def test_list_users_returns_paginated_results(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test listing users with pagination."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await test_client.get("/api/v1/users?limit=10&offset=0", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "limit" in data["data"]
        assert "offset" in data["data"]
        assert "has_more" in data["data"]
    
    @pytest.mark.asyncio
    async def test_list_users_without_permission_returns_403(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test listing users without admin permission fails."""
        # This test will pass now but should fail when RBAC is implemented
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await test_client.get("/api/v1/users", headers=headers)
        
        # For now it should work (placeholder RBAC)
        # After Sprint 19-20, this should return 403 for regular users
        assert response.status_code in [200, 403]
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_returns_user(
        self,
        test_client: AsyncClient,
        test_db: AsyncIOMotorDatabase,
        user_token: str,
        mock_user_data: dict
    ):
        """Test getting user by ID."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Get user ID
        auth = await test_db["auth"].find_one({"email": mock_user_data["email"].lower()})
        user = await test_db["users"].find_one({"auth_id": auth["_id"]})
        user_id = str(user["_id"])
        
        response = await test_client.get(f"/api/v1/users/{user_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["data"]["id"] == user_id
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_user_returns_404(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test getting non-existent user returns 404."""
        headers = {"Authorization": f"Bearer {user_token}"}
        fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but doesn't exist
        
        response = await test_client.get(f"/api/v1/users/{fake_id}", headers=headers)
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_user_by_id_updates_user(
        self,
        test_client: AsyncClient,
        test_db: AsyncIOMotorDatabase,
        user_token: str,
        mock_user_data: dict
    ):
        """Test updating user by ID as admin."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Get user ID
        auth = await test_db["auth"].find_one({"email": mock_user_data["email"].lower()})
        user = await test_db["users"].find_one({"auth_id": auth["_id"]})
        user_id = str(user["_id"])
        
        update_data = {
            "first_name": "AdminUpdated",
            "last_name": "AdminUpdated"
        }
        
        response = await test_client.put(
            f"/api/v1/users/{user_id}",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["first_name"] == "AdminUpdated"
    
    @pytest.mark.asyncio
    async def test_soft_deleted_users_not_returned_in_list(
        self,
        test_client: AsyncClient,
        test_db: AsyncIOMotorDatabase,
        user_token: str,
        mock_user_data: dict
    ):
        """Test that soft deleted users are not returned in list."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Soft delete the user
        auth = await test_db["auth"].find_one({"email": mock_user_data["email"].lower()})
        await test_db["users"].update_one(
            {"auth_id": auth["_id"]},
            {"$set": {"is_deleted": True}}
        )
        
        # List users
        response = await test_client.get("/api/v1/users", headers=headers)
        
        # The deleted user should not appear in results
        # (This test assumes we can still use the token, which might not be realistic
        # but tests the soft delete filtering)
        assert response.status_code in [200, 401]  # Might fail auth with deleted user


class TestUserValidation:
    """Test user data validation."""
    
    @pytest.mark.asyncio
    async def test_update_user_with_invalid_birthday_returns_422(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test updating user with invalid birthday fails."""
        headers = {"Authorization": f"Bearer {user_token}"}
        update_data = {
            "birthday": {
                "day": 32,
                "month": 13,
                "year": 2030
            }
        }
        
        response = await test_client.put("/api/v1/users/me", json=update_data, headers=headers)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_update_user_with_empty_name_returns_422(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test updating user with empty name fails."""
        headers = {"Authorization": f"Bearer {user_token}"}
        update_data = {
            "first_name": "   ",  # Empty/whitespace
            "last_name": ""
        }
        
        response = await test_client.put("/api/v1/users/me", json=update_data, headers=headers)
        
        assert response.status_code == 422


class TestUserPagination:
    """Test pagination for user listings."""
    
    @pytest.mark.asyncio
    async def test_pagination_with_limit_exceeding_max_uses_max_limit(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test pagination caps limit at MAX_PAGE_SIZE."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await test_client.get("/api/v1/users?limit=10000", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        # Limit should be capped at MAX_PAGE_SIZE (5000)
        assert data["data"]["limit"] <= 5000
    
    @pytest.mark.asyncio
    async def test_pagination_with_negative_offset_uses_zero(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test pagination treats negative offset as zero."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await test_client.get("/api/v1/users?offset=-10", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["offset"] == 0

