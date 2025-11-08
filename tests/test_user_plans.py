"""
Tests for User_Plans module.

Test scenarios for user subscription management.
"""

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta


class TestSubscriptionCreation:
    """Tests for creating user subscriptions."""
    
    @pytest.mark.asyncio
    async def test_create_subscription_with_valid_data_returns_201(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase,
        superuser_token: str
    ):
        """Test creating subscription with valid data returns 201."""
        # Create a plan first
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Test Plan",
            "description": "Test plan for subscription",
            "price": 29.99,
            "features": [],
            "limits": []
        }
        plan_response = await test_client.post("/api/v1/plans", json=plan_data, headers=admin_headers)
        plan_id = plan_response.json()["data"]["_id"]
        
        # Create subscription as regular user
        headers = {"Authorization": f"Bearer {user_token}"}
        subscription_data = {
            "plan_id": plan_id,
            "billing_cycle": "monthly",
            "auto_renew": True,
            "payment_method": {
                "type": "card",
                "last4": "4242",
                "brand": "visa"
            }
        }
        
        response = await test_client.post("/api/v1/user-plans", json=subscription_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        
        # Validate response structure
        assert data["status_code"] == 201
        assert data["message"] == "Subscription created successfully"
        assert data["data"] is not None
        assert data["error"] is None
        
        # Validate subscription data
        assert data["data"]["plan_id"] == plan_id
        assert data["data"]["status"] == "active"
        assert data["data"]["billing_cycle"] == "monthly"
        assert data["data"]["auto_renew"] is True
        assert "_id" in data["data"]
        assert "user_id" in data["data"]
        assert "start_date" in data["data"]
        assert "end_date" in data["data"]
        assert "created_at" in data["data"]
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Test Plan"})
        await test_db.user_plans.delete_many({"plan_id": plan_id})
    
    @pytest.mark.asyncio
    async def test_create_subscription_with_invalid_plan_returns_404(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test creating subscription with invalid plan ID returns 404."""
        headers = {"Authorization": f"Bearer {user_token}"}
        subscription_data = {
            "plan_id": "507f1f77bcf86cd799439011",  # Non-existent plan
            "billing_cycle": "monthly",
            "auto_renew": True
        }
        
        response = await test_client.post("/api/v1/user-plans", json=subscription_data, headers=headers)
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_duplicate_active_subscription_returns_400(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase,
        superuser_token: str
    ):
        """Test creating duplicate active subscription returns 400."""
        # Create a plan
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Duplicate Test Plan",
            "description": "Test plan",
            "price": 19.99,
            "features": [],
            "limits": []
        }
        plan_response = await test_client.post("/api/v1/plans", json=plan_data, headers=admin_headers)
        plan_id = plan_response.json()["data"]["_id"]
        
        # Create first subscription
        headers = {"Authorization": f"Bearer {user_token}"}
        subscription_data = {
            "plan_id": plan_id,
            "billing_cycle": "monthly",
            "auto_renew": True
        }
        await test_client.post("/api/v1/user-plans", json=subscription_data, headers=headers)
        
        # Try to create duplicate
        response = await test_client.post("/api/v1/user-plans", json=subscription_data, headers=headers)
        
        assert response.status_code == 400
        data = response.json()
        
        # Validate error response structure
        assert data["status_code"] == 400
        assert data["data"] is None
        assert data["error"] is not None
        assert data["error"]["code"] == "DUPLICATE_RESOURCE"
        assert "already has an active subscription" in data["error"]["message"].lower()
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Duplicate Test Plan"})
        await test_db.user_plans.delete_many({"plan_id": plan_id})
    
    @pytest.mark.asyncio
    async def test_create_subscription_without_auth_returns_401(
        self,
        test_client: AsyncClient
    ):
        """Test creating subscription without authentication returns 401."""
        subscription_data = {
            "plan_id": "507f1f77bcf86cd799439011",
            "billing_cycle": "monthly",
            "auto_renew": True
        }
        
        response = await test_client.post("/api/v1/user-plans", json=subscription_data)
        
        assert response.status_code == 401


class TestSubscriptionRetrieval:
    """Tests for retrieving user subscriptions."""
    
    @pytest.mark.asyncio
    async def test_get_current_subscription_returns_active_subscription(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase,
        superuser_token: str
    ):
        """Test getting current subscription returns active subscription."""
        # Create plan and subscription
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Current Sub Plan",
            "description": "Test",
            "price": 9.99,
            "features": [],
            "limits": []
        }
        plan_response = await test_client.post("/api/v1/plans", json=plan_data, headers=admin_headers)
        plan_id = plan_response.json()["data"]["_id"]
        
        headers = {"Authorization": f"Bearer {user_token}"}
        subscription_data = {
            "plan_id": plan_id,
            "billing_cycle": "monthly",
            "auto_renew": True
        }
        await test_client.post("/api/v1/user-plans", json=subscription_data, headers=headers)
        
        # Get current subscription
        response = await test_client.get("/api/v1/user-plans/current", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["plan_id"] == plan_id
        assert data["data"]["status"] == "active"
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Current Sub Plan"})
        await test_db.user_plans.delete_many({"plan_id": plan_id})
    
    @pytest.mark.asyncio
    async def test_list_user_subscriptions_returns_paginated_results(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test listing user subscriptions returns paginated results."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        response = await test_client.get("/api/v1/user-plans?limit=10&offset=0", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data["status_code"] == 200
        assert data["message"] == "Subscriptions retrieved successfully"
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
    async def test_get_subscription_by_id_returns_subscription(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase,
        superuser_token: str
    ):
        """Test getting subscription by ID returns subscription data."""
        # Create plan and subscription
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Get By ID Plan",
            "description": "Test",
            "price": 14.99,
            "features": [],
            "limits": []
        }
        plan_response = await test_client.post("/api/v1/plans", json=plan_data, headers=admin_headers)
        plan_id = plan_response.json()["data"]["_id"]
        
        headers = {"Authorization": f"Bearer {user_token}"}
        subscription_data = {
            "plan_id": plan_id,
            "billing_cycle": "yearly",
            "auto_renew": False
        }
        create_response = await test_client.post("/api/v1/user-plans", json=subscription_data, headers=headers)
        subscription_id = create_response.json()["data"]["_id"]
        
        # Get subscription by ID
        response = await test_client.get(f"/api/v1/user-plans/{subscription_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["_id"] == subscription_id
        assert data["data"]["billing_cycle"] == "yearly"
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Get By ID Plan"})
        await test_db.user_plans.delete_many({"_id": subscription_id})


class TestSubscriptionUpdate:
    """Tests for updating user subscriptions."""
    
    @pytest.mark.asyncio
    async def test_update_subscription_auto_renew_returns_updated_subscription(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase,
        superuser_token: str
    ):
        """Test updating subscription auto_renew flag returns updated subscription."""
        # Create plan and subscription
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Update Auto Renew Plan",
            "description": "Test",
            "price": 24.99,
            "features": [],
            "limits": []
        }
        plan_response = await test_client.post("/api/v1/plans", json=plan_data, headers=admin_headers)
        plan_id = plan_response.json()["data"]["_id"]
        
        headers = {"Authorization": f"Bearer {user_token}"}
        subscription_data = {
            "plan_id": plan_id,
            "billing_cycle": "monthly",
            "auto_renew": True
        }
        create_response = await test_client.post("/api/v1/user-plans", json=subscription_data, headers=headers)
        subscription_id = create_response.json()["data"]["_id"]
        
        # Update auto_renew
        update_data = {"auto_renew": False}
        response = await test_client.put(f"/api/v1/user-plans/{subscription_id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["auto_renew"] is False
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Update Auto Renew Plan"})
        await test_db.user_plans.delete_many({"_id": subscription_id})
    
    @pytest.mark.asyncio
    async def test_update_payment_method_returns_updated_subscription(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase,
        superuser_token: str
    ):
        """Test updating payment method returns updated subscription."""
        # Create plan and subscription
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Update Payment Plan",
            "description": "Test",
            "price": 19.99,
            "features": [],
            "limits": []
        }
        plan_response = await test_client.post("/api/v1/plans", json=plan_data, headers=admin_headers)
        plan_id = plan_response.json()["data"]["_id"]
        
        headers = {"Authorization": f"Bearer {user_token}"}
        subscription_data = {
            "plan_id": plan_id,
            "billing_cycle": "monthly",
            "auto_renew": True,
            "payment_method": {
                "type": "card",
                "last4": "4242",
                "brand": "visa"
            }
        }
        create_response = await test_client.post("/api/v1/user-plans", json=subscription_data, headers=headers)
        subscription_id = create_response.json()["data"]["_id"]
        
        # Update payment method
        update_data = {
            "payment_method": {
                "type": "card",
                "last4": "5555",
                "brand": "mastercard"
            }
        }
        response = await test_client.put(f"/api/v1/user-plans/{subscription_id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["payment_method"]["last4"] == "5555"
        assert data["data"]["payment_method"]["brand"] == "mastercard"
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Update Payment Plan"})
        await test_db.user_plans.delete_many({"_id": subscription_id})


class TestSubscriptionCancellation:
    """Tests for cancelling subscriptions."""
    
    @pytest.mark.asyncio
    async def test_cancel_subscription_marks_as_cancelled(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase,
        superuser_token: str
    ):
        """Test cancelling subscription marks it as cancelled."""
        # Create plan and subscription
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Cancel Test Plan",
            "description": "Test",
            "price": 39.99,
            "features": [],
            "limits": []
        }
        plan_response = await test_client.post("/api/v1/plans", json=plan_data, headers=admin_headers)
        plan_id = plan_response.json()["data"]["_id"]
        
        headers = {"Authorization": f"Bearer {user_token}"}
        subscription_data = {
            "plan_id": plan_id,
            "billing_cycle": "monthly",
            "auto_renew": True
        }
        create_response = await test_client.post("/api/v1/user-plans", json=subscription_data, headers=headers)
        subscription_id = create_response.json()["data"]["_id"]
        
        # Cancel subscription
        response = await test_client.post(f"/api/v1/user-plans/{subscription_id}/cancel", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "cancelled"
        assert data["data"]["auto_renew"] is False
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Cancel Test Plan"})
        await test_db.user_plans.delete_many({"_id": subscription_id})
    
    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_subscription_returns_400(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase,
        superuser_token: str
    ):
        """Test cancelling already cancelled subscription returns 400."""
        # Create plan and subscription
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Double Cancel Plan",
            "description": "Test",
            "price": 29.99,
            "features": [],
            "limits": []
        }
        plan_response = await test_client.post("/api/v1/plans", json=plan_data, headers=admin_headers)
        plan_id = plan_response.json()["data"]["_id"]
        
        headers = {"Authorization": f"Bearer {user_token}"}
        subscription_data = {
            "plan_id": plan_id,
            "billing_cycle": "monthly",
            "auto_renew": True
        }
        create_response = await test_client.post("/api/v1/user-plans", json=subscription_data, headers=headers)
        subscription_id = create_response.json()["data"]["_id"]
        
        # Cancel first time
        await test_client.post(f"/api/v1/user-plans/{subscription_id}/cancel", headers=headers)
        
        # Try to cancel again
        response = await test_client.post(f"/api/v1/user-plans/{subscription_id}/cancel", headers=headers)
        
        assert response.status_code == 400
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Double Cancel Plan"})
        await test_db.user_plans.delete_many({"_id": subscription_id})


class TestSubscriptionRenewal:
    """Tests for subscription renewal."""
    
    @pytest.mark.asyncio
    async def test_renew_subscription_extends_end_date(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase,
        superuser_token: str
    ):
        """Test renewing subscription extends end_date."""
        # Create plan and subscription
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        plan_data = {
            "name": "Renew Test Plan",
            "description": "Test",
            "price": 49.99,
            "features": [],
            "limits": []
        }
        plan_response = await test_client.post("/api/v1/plans", json=plan_data, headers=admin_headers)
        plan_id = plan_response.json()["data"]["_id"]
        
        headers = {"Authorization": f"Bearer {user_token}"}
        subscription_data = {
            "plan_id": plan_id,
            "billing_cycle": "monthly",
            "auto_renew": False
        }
        create_response = await test_client.post("/api/v1/user-plans", json=subscription_data, headers=headers)
        subscription_id = create_response.json()["data"]["_id"]
        original_end_date = create_response.json()["data"]["end_date"]
        
        # Renew subscription
        response = await test_client.post(f"/api/v1/user-plans/{subscription_id}/renew", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["end_date"] > original_end_date
        assert data["data"]["status"] == "active"
        
        # Cleanup
        await test_db.plans.delete_many({"name": "Renew Test Plan"})
        await test_db.user_plans.delete_many({"_id": subscription_id})

