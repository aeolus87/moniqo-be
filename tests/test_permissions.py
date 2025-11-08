"""
Tests for Permissions module.

Test scenarios for permission CRUD operations and validation.
"""

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase


class TestPermissionCreation:
    """Tests for permission creation."""
    
    @pytest.mark.asyncio
    async def test_create_permission_with_valid_data_returns_201(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating permission with valid data returns 201."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        permission_data = {
            "resource": "agents",
            "action": "read",
            "description": "Read agents"
        }
        
        response = await test_client.post("/api/v1/permissions", json=permission_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status_code"] == 201
        assert data["data"]["resource"] == "agents"
        assert data["data"]["action"] == "read"
        assert "created_at" in data["data"]
        
        # Cleanup
        await test_db.permissions.delete_many({"resource": "agents", "action": "read"})
    
    @pytest.mark.asyncio
    async def test_create_duplicate_permission_returns_400(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating duplicate permission returns 400."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        permission_data = {
            "resource": "agents",
            "action": "write",
            "description": "Write agents"
        }
        
        # Create first time
        await test_client.post("/api/v1/permissions", json=permission_data, headers=headers)
        
        # Try to create duplicate
        response = await test_client.post("/api/v1/permissions", json=permission_data, headers=headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["error"]["message"].lower()
        
        # Cleanup
        await test_db.permissions.delete_many({"resource": "agents", "action": "write"})
    
    @pytest.mark.asyncio
    async def test_create_permission_without_auth_returns_401(
        self,
        test_client: AsyncClient
    ):
        """Test creating permission without authentication returns 401."""
        permission_data = {
            "resource": "agents",
            "action": "read",
            "description": "Read agents"
        }
        
        response = await test_client.post("/api/v1/permissions", json=permission_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_permission_with_missing_fields_returns_422(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test creating permission with missing required fields returns 422."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        permission_data = {
            "resource": "agents"
            # Missing "action" and "description"
        }
        
        response = await test_client.post("/api/v1/permissions", json=permission_data, headers=headers)
        
        assert response.status_code == 422


class TestPermissionRetrieval:
    """Tests for permission retrieval."""
    
    @pytest.mark.asyncio
    async def test_list_permissions_returns_paginated_results(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test listing permissions returns paginated results."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        # Create test permissions
        test_permissions = [
            {"resource": "test_resource", "action": "read", "description": "Test read"},
            {"resource": "test_resource", "action": "write", "description": "Test write"},
        ]
        
        for perm in test_permissions:
            await test_client.post("/api/v1/permissions", json=perm, headers=headers)
        
        # List permissions
        response = await test_client.get("/api/v1/permissions?limit=10&offset=0", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert isinstance(data["data"]["items"], list)
        
        # Cleanup
        await test_db.permissions.delete_many({"resource": "test_resource"})
    
    @pytest.mark.asyncio
    async def test_get_permission_by_id_returns_permission(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test getting permission by ID returns permission data."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        permission_data = {
            "resource": "flows",
            "action": "execute",
            "description": "Execute flows"
        }
        
        # Create permission
        create_response = await test_client.post("/api/v1/permissions", json=permission_data, headers=headers)
        permission_id = create_response.json()["data"]["_id"]
        
        # Get permission
        response = await test_client.get(f"/api/v1/permissions/{permission_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["resource"] == "flows"
        assert data["data"]["action"] == "execute"
        
        # Cleanup
        await test_db.permissions.delete_many({"resource": "flows", "action": "execute"})
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_permission_returns_404(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test getting non-existent permission returns 404."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        fake_id = "507f1f77bcf86cd799439011"
        
        response = await test_client.get(f"/api/v1/permissions/{fake_id}", headers=headers)
        
        assert response.status_code == 404


class TestPermissionUpdate:
    """Tests for permission updates."""
    
    @pytest.mark.asyncio
    async def test_update_permission_with_valid_data_returns_updated_permission(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test updating permission with valid data returns updated permission."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        permission_data = {
            "resource": "trades",
            "action": "view",
            "description": "View trades"
        }
        
        # Create permission
        create_response = await test_client.post("/api/v1/permissions", json=permission_data, headers=headers)
        permission_id = create_response.json()["data"]["_id"]
        
        # Update permission
        update_data = {
            "description": "View all trades (updated)"
        }
        response = await test_client.put(f"/api/v1/permissions/{permission_id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["description"] == "View all trades (updated)"
        assert data["data"]["resource"] == "trades"  # Unchanged
        
        # Cleanup
        await test_db.permissions.delete_many({"resource": "trades", "action": "view"})
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_permission_returns_404(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test updating non-existent permission returns 404."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        fake_id = "507f1f77bcf86cd799439011"
        update_data = {
            "description": "Updated description"
        }
        
        response = await test_client.put(f"/api/v1/permissions/{fake_id}", json=update_data, headers=headers)
        
        assert response.status_code == 404


class TestPermissionDeletion:
    """Tests for permission deletion (soft delete)."""
    
    @pytest.mark.asyncio
    async def test_delete_permission_marks_as_deleted(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test deleting permission marks it as deleted."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        permission_data = {
            "resource": "wallets",
            "action": "connect",
            "description": "Connect wallet"
        }
        
        # Create permission
        create_response = await test_client.post("/api/v1/permissions", json=permission_data, headers=headers)
        permission_id = create_response.json()["data"]["_id"]
        
        # Delete permission
        response = await test_client.delete(f"/api/v1/permissions/{permission_id}", headers=headers)
        
        assert response.status_code == 200
        
        # Verify soft delete in database
        from bson import ObjectId
        deleted_permission = await test_db.permissions.find_one({"_id": ObjectId(permission_id)})
        assert deleted_permission is not None
        assert deleted_permission["is_deleted"] is True
        
        # Cleanup
        await test_db.permissions.delete_many({"resource": "wallets", "action": "connect"})
    
    @pytest.mark.asyncio
    async def test_deleted_permissions_not_returned_in_list(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test that deleted permissions are not returned in list."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        permission_data = {
            "resource": "settings",
            "action": "modify",
            "description": "Modify settings"
        }
        
        # Create permission
        create_response = await test_client.post("/api/v1/permissions", json=permission_data, headers=headers)
        permission_id = create_response.json()["data"]["_id"]
        
        # Delete permission
        await test_client.delete(f"/api/v1/permissions/{permission_id}", headers=headers)
        
        # List permissions
        response = await test_client.get("/api/v1/permissions", headers=headers)
        data = response.json()
        
        # Deleted permission should not be in list
        permission_ids = [p["_id"] for p in data["data"]["items"]]
        assert permission_id not in permission_ids
        
        # Cleanup
        await test_db.permissions.delete_many({"resource": "settings", "action": "modify"})

