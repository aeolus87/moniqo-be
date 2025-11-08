"""
Tests for Plans module.

Test scenarios for subscription plan CRUD operations.
"""

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase


class TestPlanCreation:
    """Tests for plan creation."""
    
    @pytest.mark.asyncio
    async def test_create_plan_with_valid_data_returns_201(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating plan with valid data returns 201."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Pro Plan",
            "description": "Professional tier with advanced features",
            "price": 29.99,
            "features": [
                {
                    "resource": "api_calls",
                    "title": "Unlimited API Calls",
                    "description": "No limits on API requests"
                },
                {
                    "resource": "agents",
                    "title": "5 AI Agents",
                    "description": "Deploy up to 5 AI agents"
                }
            ],
            "limits": [
                {
                    "resource": "trades_per_day",
                    "title": "Daily Trades",
                    "description": "Maximum trades per day",
                    "value": 100
                }
            ]
        }
        
        response = await test_client.post("/api/v1/plans", json=plan_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        
        # Validate response structure
        assert data["status_code"] == 201
        assert data["message"] == "Plan created successfully"
        assert data["data"] is not None
        assert data["error"] is None
        
        # Validate plan data
        assert data["data"]["name"] == "Pro Plan"
        assert data["data"]["description"] == "Professional tier with advanced features"
        assert data["data"]["price"] == 29.99
        assert len(data["data"]["features"]) == 2
        assert len(data["data"]["limits"]) == 1
        assert "_id" in data["data"]
        assert "created_at" in data["data"]
        assert "updated_at" in data["data"]
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Pro Plan"})
    
    @pytest.mark.asyncio
    async def test_create_free_plan_with_zero_price_returns_201(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating free plan with price 0 returns 201."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Free Plan",
            "description": "Free tier with basic features",
            "price": 0.0,
            "features": [
                {
                    "resource": "agents",
                    "title": "1 AI Agent",
                    "description": "Deploy 1 AI agent"
                }
            ],
            "limits": [
                {
                    "resource": "trades_per_day",
                    "title": "Daily Trades",
                    "description": "Maximum trades per day",
                    "value": 10
                }
            ]
        }
        
        response = await test_client.post("/api/v1/plans", json=plan_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["price"] == 0.0
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Free Plan"})
    
    @pytest.mark.asyncio
    async def test_create_duplicate_plan_returns_400(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating duplicate plan returns 400."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Enterprise",
            "description": "Enterprise tier",
            "price": 99.99,
            "features": [],
            "limits": []
        }
        
        # Create first time
        await test_client.post("/api/v1/plans", json=plan_data, headers=headers)
        
        # Try to create duplicate
        response = await test_client.post("/api/v1/plans", json=plan_data, headers=headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["error"]["message"].lower()
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Enterprise"})
    
    @pytest.mark.asyncio
    async def test_create_plan_without_auth_returns_401(
        self,
        test_client: AsyncClient
    ):
        """Test creating plan without authentication returns 401."""
        plan_data = {
            "name": "Test Plan",
            "description": "Test",
            "price": 10.0,
            "features": [],
            "limits": []
        }
        
        response = await test_client.post("/api/v1/plans", json=plan_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_plan_with_missing_fields_returns_422(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test creating plan with missing required fields returns 422."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Incomplete Plan"
            # Missing description, price, features, limits
        }
        
        response = await test_client.post("/api/v1/plans", json=plan_data, headers=headers)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_plan_with_negative_price_returns_422(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test creating plan with negative price returns 422."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Invalid Plan",
            "description": "Invalid price",
            "price": -10.0,
            "features": [],
            "limits": []
        }
        
        response = await test_client.post("/api/v1/plans", json=plan_data, headers=headers)
        
        assert response.status_code == 422


class TestPlanRetrieval:
    """Tests for plan retrieval."""
    
    @pytest.mark.asyncio
    async def test_list_plans_returns_paginated_results(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test listing plans returns paginated results (accessible to regular users)."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # List plans (regular users should be able to see plans)
        response = await test_client.get("/api/v1/plans?limit=10&offset=0", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data["status_code"] == 200
        assert data["message"] == "Plans retrieved successfully"
        assert data["data"] is not None
        assert data["error"] is None
        
        # Validate paginated response
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "limit" in data["data"]
        assert "offset" in data["data"]
        assert "has_more" in data["data"]
        assert isinstance(data["data"]["items"], list)
    
    @pytest.mark.asyncio
    async def test_get_plan_by_id_returns_plan(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test getting plan by ID returns plan data."""
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        plan_data = {
            "name": "Starter Plan",
            "description": "Starter tier",
            "price": 9.99,
            "features": [],
            "limits": []
        }
        
        # Create plan
        create_response = await test_client.post("/api/v1/plans", json=plan_data, headers=admin_headers)
        plan_id = create_response.json()["data"]["_id"]
        
        # Get plan (as regular user)
        response = await test_client.get(f"/api/v1/plans/{plan_id}", headers=user_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Starter Plan"
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Starter Plan"})
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_plan_returns_404(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test getting non-existent plan returns 404."""
        headers = {"Authorization": f"Bearer {user_token}"}
        fake_id = "507f1f77bcf86cd799439011"
        
        response = await test_client.get(f"/api/v1/plans/{fake_id}", headers=headers)
        
        assert response.status_code == 404
        data = response.json()
        
        # Validate error response structure
        assert data["status_code"] == 404
        assert data["data"] is None
        assert data["error"] is not None
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"


class TestPlanUpdate:
    """Tests for plan updates."""
    
    @pytest.mark.asyncio
    async def test_update_plan_with_valid_data_returns_updated_plan(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test updating plan with valid data returns updated plan."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Basic Plan",
            "description": "Basic tier",
            "price": 19.99,
            "features": [],
            "limits": []
        }
        
        # Create plan
        create_response = await test_client.post("/api/v1/plans", json=plan_data, headers=headers)
        plan_id = create_response.json()["data"]["_id"]
        
        # Update plan
        update_data = {
            "price": 24.99,
            "description": "Basic tier with updated pricing"
        }
        response = await test_client.put(f"/api/v1/plans/{plan_id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["price"] == 24.99
        assert data["data"]["description"] == "Basic tier with updated pricing"
        assert data["data"]["name"] == "Basic Plan"  # Unchanged
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Basic Plan"})
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_plan_returns_404(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test updating non-existent plan returns 404."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        fake_id = "507f1f77bcf86cd799439011"
        update_data = {
            "price": 99.99
        }
        
        response = await test_client.put(f"/api/v1/plans/{fake_id}", json=update_data, headers=headers)
        
        assert response.status_code == 404


class TestPlanDeletion:
    """Tests for plan deletion (soft delete)."""
    
    @pytest.mark.asyncio
    async def test_delete_plan_marks_as_deleted(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test deleting plan marks it as deleted."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Temp Plan",
            "description": "Temporary plan",
            "price": 5.0,
            "features": [],
            "limits": []
        }
        
        # Create plan
        create_response = await test_client.post("/api/v1/plans", json=plan_data, headers=headers)
        plan_id = create_response.json()["data"]["_id"]
        
        # Delete plan
        response = await test_client.delete(f"/api/v1/plans/{plan_id}", headers=headers)
        
        assert response.status_code == 200
        
        # Verify soft delete in database
        from bson import ObjectId
        deleted_plan = await test_db.plans.find_one({"_id": ObjectId(plan_id)})
        assert deleted_plan is not None
        assert deleted_plan["is_deleted"] is True
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Temp Plan"})
    
    @pytest.mark.asyncio
    async def test_deleted_plans_not_returned_in_list(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test that deleted plans are not returned in list."""
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        plan_data = {
            "name": "Deleted Plan",
            "description": "Will be deleted",
            "price": 15.0,
            "features": [],
            "limits": []
        }
        
        # Create plan
        create_response = await test_client.post("/api/v1/plans", json=plan_data, headers=admin_headers)
        plan_id = create_response.json()["data"]["_id"]
        
        # Delete plan
        await test_client.delete(f"/api/v1/plans/{plan_id}", headers=admin_headers)
        
        # List plans
        response = await test_client.get("/api/v1/plans", headers=user_headers)
        data = response.json()
        
        # Deleted plan should not be in list
        plan_ids = [p["_id"] for p in data["data"]["items"]]
        assert plan_id not in plan_ids
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Deleted Plan"})

