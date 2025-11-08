"""
Tests for Roles module.

Test scenarios for role CRUD operations and permission assignment.
"""

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase


class TestRoleCreation:
    """Tests for role creation."""
    
    @pytest.mark.asyncio
    async def test_create_role_with_valid_data_returns_201(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating role with valid data returns 201."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        # Create some permissions first (or get existing ones)
        perm1_data = {"resource": "users", "action": "read", "description": "Read users"}
        perm2_data = {"resource": "users", "action": "write", "description": "Write users"}
        
        perm1_response = await test_client.post("/api/v1/permissions", json=perm1_data, headers=headers)
        perm2_response = await test_client.post("/api/v1/permissions", json=perm2_data, headers=headers)
        
        # Handle case where permissions already exist (400 response)
        if perm1_response.status_code == 201:
            perm1_id = perm1_response.json()["data"]["_id"]
        else:
            # Permission already exists, get it from database
            existing_perm = await test_db.permissions.find_one({"resource": "users", "action": "read", "is_deleted": False})
            perm1_id = str(existing_perm["_id"])
        
        if perm2_response.status_code == 201:
            perm2_id = perm2_response.json()["data"]["_id"]
        else:
            # Permission already exists, get it from database
            existing_perm = await test_db.permissions.find_one({"resource": "users", "action": "write", "is_deleted": False})
            perm2_id = str(existing_perm["_id"])
        
        # Create role with permissions
        role_data = {
            "name": "Content Manager",
            "description": "Can manage content",
            "permissions": [perm1_id, perm2_id]
        }
        
        response = await test_client.post("/api/v1/roles", json=role_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status_code"] == 201
        assert data["data"]["name"] == "Content Manager"
        assert len(data["data"]["permissions"]) == 2
        assert "created_at" in data["data"]
        
        # Cleanup (only delete the role, not permissions as they may be used by other tests)
        await test_db.roles.delete_many({"name": "Content Manager"})
    
    @pytest.mark.asyncio
    async def test_create_role_without_permissions_returns_201(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating role without permissions returns 201."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        role_data = {
            "name": "Viewer",
            "description": "Can only view",
            "permissions": []
        }
        
        response = await test_client.post("/api/v1/roles", json=role_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["name"] == "Viewer"
        assert data["data"]["permissions"] == []
        
        # Cleanup
        await test_db.roles.delete_many({"name": "Viewer"})
    
    @pytest.mark.asyncio
    async def test_create_duplicate_role_returns_400(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating duplicate role returns 400."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        role_data = {
            "name": "Moderator",
            "description": "Can moderate content",
            "permissions": []
        }
        
        # Create first time
        await test_client.post("/api/v1/roles", json=role_data, headers=headers)
        
        # Try to create duplicate
        response = await test_client.post("/api/v1/roles", json=role_data, headers=headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["error"]["message"].lower()
        
        # Cleanup
        await test_db.roles.delete_many({"name": "Moderator"})
    
    @pytest.mark.asyncio
    async def test_create_role_without_auth_returns_401(
        self,
        test_client: AsyncClient
    ):
        """Test creating role without authentication returns 401."""
        role_data = {
            "name": "Test Role",
            "description": "Test",
            "permissions": []
        }
        
        response = await test_client.post("/api/v1/roles", json=role_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_role_with_missing_fields_returns_422(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test creating role with missing required fields returns 422."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        role_data = {
            "name": "Incomplete Role"
            # Missing "description" and "permissions"
        }
        
        response = await test_client.post("/api/v1/roles", json=role_data, headers=headers)
        
        assert response.status_code == 422


class TestRoleRetrieval:
    """Tests for role retrieval."""
    
    @pytest.mark.asyncio
    async def test_list_roles_returns_paginated_results(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test listing roles returns paginated results."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        # Create test roles
        test_roles = [
            {"name": "Test Role 1", "description": "Test 1", "permissions": []},
            {"name": "Test Role 2", "description": "Test 2", "permissions": []},
        ]
        
        for role in test_roles:
            await test_client.post("/api/v1/roles", json=role, headers=headers)
        
        # List roles
        response = await test_client.get("/api/v1/roles?limit=10&offset=0", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert isinstance(data["data"]["items"], list)
        
        # Cleanup
        await test_db.roles.delete_many({"name": {"$regex": "^Test Role"}})
    
    @pytest.mark.asyncio
    async def test_get_role_by_id_returns_role(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test getting role by ID returns role data."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        role_data = {
            "name": "Project Manager",
            "description": "Manages projects",
            "permissions": []
        }
        
        # Create role
        create_response = await test_client.post("/api/v1/roles", json=role_data, headers=headers)
        role_id = create_response.json()["data"]["_id"]
        
        # Get role
        response = await test_client.get(f"/api/v1/roles/{role_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Project Manager"
        
        # Cleanup
        await test_db.roles.delete_many({"name": "Project Manager"})
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_role_returns_404(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test getting non-existent role returns 404."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        fake_id = "507f1f77bcf86cd799439011"
        
        response = await test_client.get(f"/api/v1/roles/{fake_id}", headers=headers)
        
        assert response.status_code == 404


class TestRoleUpdate:
    """Tests for role updates."""
    
    @pytest.mark.asyncio
    async def test_update_role_with_valid_data_returns_updated_role(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test updating role with valid data returns updated role."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        role_data = {
            "name": "Support Agent",
            "description": "Handles support tickets",
            "permissions": []
        }
        
        # Create role
        create_response = await test_client.post("/api/v1/roles", json=role_data, headers=headers)
        role_id = create_response.json()["data"]["_id"]
        
        # Update role
        update_data = {
            "description": "Handles support tickets and escalations"
        }
        response = await test_client.put(f"/api/v1/roles/{role_id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["description"] == "Handles support tickets and escalations"
        assert data["data"]["name"] == "Support Agent"  # Unchanged
        
        # Cleanup
        await test_db.roles.delete_many({"name": "Support Agent"})
    
    @pytest.mark.asyncio
    async def test_update_role_permissions_updates_role(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test updating role permissions updates role."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        # Create permission
        perm_data = {"resource": "reports", "action": "read", "description": "Read reports"}
        perm_response = await test_client.post("/api/v1/permissions", json=perm_data, headers=headers)
        perm_id = perm_response.json()["data"]["_id"]
        
        # Create role without permissions
        role_data = {
            "name": "Analyst",
            "description": "Data analyst",
            "permissions": []
        }
        create_response = await test_client.post("/api/v1/roles", json=role_data, headers=headers)
        role_id = create_response.json()["data"]["_id"]
        
        # Update role with permissions
        update_data = {
            "permissions": [perm_id]
        }
        response = await test_client.put(f"/api/v1/roles/{role_id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["permissions"]) == 1
        
        # Cleanup
        await test_db.roles.delete_many({"name": "Analyst"})
        await test_db.permissions.delete_many({"resource": "reports"})
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_role_returns_404(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test updating non-existent role returns 404."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        fake_id = "507f1f77bcf86cd799439011"
        update_data = {
            "description": "Updated description"
        }
        
        response = await test_client.put(f"/api/v1/roles/{fake_id}", json=update_data, headers=headers)
        
        assert response.status_code == 404


class TestRoleDeletion:
    """Tests for role deletion (soft delete)."""
    
    @pytest.mark.asyncio
    async def test_delete_role_marks_as_deleted(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test deleting role marks it as deleted."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        role_data = {
            "name": "Temp Role",
            "description": "Temporary role",
            "permissions": []
        }
        
        # Create role
        create_response = await test_client.post("/api/v1/roles", json=role_data, headers=headers)
        role_id = create_response.json()["data"]["_id"]
        
        # Delete role
        response = await test_client.delete(f"/api/v1/roles/{role_id}", headers=headers)
        
        assert response.status_code == 200
        
        # Verify soft delete in database
        from bson import ObjectId
        deleted_role = await test_db.roles.find_one({"_id": ObjectId(role_id)})
        assert deleted_role is not None
        assert deleted_role["is_deleted"] is True
        
        # Cleanup
        await test_db.roles.delete_many({"name": "Temp Role"})
    
    @pytest.mark.asyncio
    async def test_deleted_roles_not_returned_in_list(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test that deleted roles are not returned in list."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        role_data = {
            "name": "Deleted Role",
            "description": "Will be deleted",
            "permissions": []
        }
        
        # Create role
        create_response = await test_client.post("/api/v1/roles", json=role_data, headers=headers)
        role_id = create_response.json()["data"]["_id"]
        
        # Delete role
        await test_client.delete(f"/api/v1/roles/{role_id}", headers=headers)
        
        # List roles
        response = await test_client.get("/api/v1/roles", headers=headers)
        data = response.json()
        
        # Deleted role should not be in list
        role_ids = [r["_id"] for r in data["data"]["items"]]
        assert role_id not in role_ids
        
        # Cleanup
        await test_db.roles.delete_many({"name": "Deleted Role"})

