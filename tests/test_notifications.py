"""
Tests for Notifications module.

Test scenarios for user notification management.
"""

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase


class TestNotificationCreation:
    """Tests for creating notifications."""
    
    @pytest.mark.asyncio
    async def test_create_notification_with_valid_data_returns_201(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating notification with valid data returns 201."""
        headers = {"Authorization": f"Bearer {user_token}"}
        notification_data = {
            "type": "info",
            "title": "Welcome!",
            "message": "Welcome to the platform!",
            "metadata": {"source": "onboarding"}
        }
        
        response = await test_client.post("/api/v1/notifications", json=notification_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        
        # Validate response structure
        assert data["status_code"] == 201
        assert data["message"] == "Notification created successfully"
        assert data["data"] is not None
        assert data["error"] is None
        
        # Validate data fields
        assert data["data"]["type"] == "info"
        assert data["data"]["title"] == "Welcome!"
        assert data["data"]["message"] == "Welcome to the platform!"
        assert data["data"]["is_read"] is False
        assert data["data"]["read_at"] is None
        assert data["data"]["metadata"] == {"source": "onboarding"}
        assert "_id" in data["data"]
        assert "user_id" in data["data"]
        assert "created_at" in data["data"]
        assert "updated_at" in data["data"]
        
        # Cleanup
        await test_db.notifications.delete_many({"title": "Welcome!"})
    
    @pytest.mark.asyncio
    async def test_create_notification_without_metadata_returns_201(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating notification without metadata returns 201."""
        headers = {"Authorization": f"Bearer {user_token}"}
        notification_data = {
            "type": "success",
            "title": "Action Complete",
            "message": "Your action was completed successfully"
        }
        
        response = await test_client.post("/api/v1/notifications", json=notification_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        
        # Validate response structure
        assert data["status_code"] == 201
        assert data["message"] == "Notification created successfully"
        assert data["data"] is not None
        assert data["error"] is None
        
        # Validate data fields
        assert data["data"]["type"] == "success"
        assert data["data"]["title"] == "Action Complete"
        assert data["data"]["message"] == "Your action was completed successfully"
        assert data["data"]["metadata"] is None
        assert data["data"]["is_read"] is False
        assert "_id" in data["data"]
        assert "user_id" in data["data"]
        
        # Cleanup
        await test_db.notifications.delete_many({"title": "Action Complete"})
    
    @pytest.mark.asyncio
    async def test_create_notification_without_auth_returns_401(
        self,
        test_client: AsyncClient
    ):
        """Test creating notification without authentication returns 401."""
        notification_data = {
            "type": "info",
            "title": "Test",
            "message": "Test message"
        }
        
        response = await test_client.post("/api/v1/notifications", json=notification_data)
        
        assert response.status_code == 401
        # For 401/403/404 errors, we should check error structure
        data = response.json()
        assert "detail" in data or "error" in data  # FastAPI 401 returns "detail"
    
    @pytest.mark.asyncio
    async def test_create_notification_with_invalid_type_returns_422(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test creating notification with invalid type returns 422."""
        headers = {"Authorization": f"Bearer {user_token}"}
        notification_data = {
            "type": "invalid_type",
            "title": "Test",
            "message": "Test message"
        }
        
        response = await test_client.post("/api/v1/notifications", json=notification_data, headers=headers)
        
        assert response.status_code == 422


class TestNotificationRetrieval:
    """Tests for retrieving notifications."""
    
    @pytest.mark.asyncio
    async def test_list_notifications_returns_paginated_results(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test listing notifications returns paginated results."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        response = await test_client.get("/api/v1/notifications?limit=10&offset=0", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data["status_code"] == 200
        assert data["message"] == "Notifications retrieved successfully"
        assert data["data"] is not None
        assert data["error"] is None
        
        # Validate paginated response structure
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "limit" in data["data"]
        assert "offset" in data["data"]
        assert "has_more" in data["data"]
        assert isinstance(data["data"]["items"], list)
        assert data["data"]["limit"] == 10
        assert data["data"]["offset"] == 0
    
    @pytest.mark.asyncio
    async def test_get_notification_by_id_returns_notification(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test getting notification by ID returns notification data."""
        headers = {"Authorization": f"Bearer {user_token}"}
        notification_data = {
            "type": "warning",
            "title": "Warning Message",
            "message": "This is a warning"
        }
        
        # Create notification
        create_response = await test_client.post("/api/v1/notifications", json=notification_data, headers=headers)
        notification_id = create_response.json()["data"]["_id"]
        
        # Get notification
        response = await test_client.get(f"/api/v1/notifications/{notification_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data["status_code"] == 200
        assert data["message"] == "Notification retrieved successfully"
        assert data["data"] is not None
        assert data["error"] is None
        
        # Validate notification data
        assert data["data"]["_id"] == notification_id
        assert data["data"]["title"] == "Warning Message"
        assert data["data"]["type"] == "warning"
        assert data["data"]["is_read"] is False
        
        # Cleanup
        await test_db.notifications.delete_many({"_id": notification_id})
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_notification_returns_404(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test getting non-existent notification returns 404."""
        headers = {"Authorization": f"Bearer {user_token}"}
        fake_id = "507f1f77bcf86cd799439011"
        
        response = await test_client.get(f"/api/v1/notifications/{fake_id}", headers=headers)
        
        assert response.status_code == 404
        data = response.json()
        # Validate error response structure
        assert data["status_code"] == 404
        assert data["data"] is None
        assert data["error"] is not None
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_list_unread_notifications_filters_correctly(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test listing unread notifications filters correctly."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create notification
        notification_data = {
            "type": "info",
            "title": "Unread Test",
            "message": "This should be unread"
        }
        create_response = await test_client.post("/api/v1/notifications", json=notification_data, headers=headers)
        notification_id = create_response.json()["data"]["_id"]
        
        # List unread notifications
        response = await test_client.get("/api/v1/notifications?is_read=false", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        notification_ids = [n["_id"] for n in data["data"]["items"]]
        assert notification_id in notification_ids
        
        # Cleanup
        await test_db.notifications.delete_many({"_id": notification_id})
    
    @pytest.mark.asyncio
    async def test_list_notifications_by_type_filters_correctly(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test listing notifications by type filters correctly."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create error notification
        notification_data = {
            "type": "error",
            "title": "Error Test",
            "message": "This is an error"
        }
        create_response = await test_client.post("/api/v1/notifications", json=notification_data, headers=headers)
        notification_id = create_response.json()["data"]["_id"]
        
        # List error notifications
        response = await test_client.get("/api/v1/notifications?type=error", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        notification_ids = [n["_id"] for n in data["data"]["items"]]
        assert notification_id in notification_ids
        # All returned notifications should be of type "error"
        assert all(n["type"] == "error" for n in data["data"]["items"])
        
        # Cleanup
        await test_db.notifications.delete_many({"_id": notification_id})


class TestNotificationMarkAsRead:
    """Tests for marking notifications as read."""
    
    @pytest.mark.asyncio
    async def test_mark_notification_as_read_updates_status(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test marking notification as read updates status."""
        headers = {"Authorization": f"Bearer {user_token}"}
        notification_data = {
            "type": "info",
            "title": "Mark Read Test",
            "message": "Test marking as read"
        }
        
        # Create notification
        create_response = await test_client.post("/api/v1/notifications", json=notification_data, headers=headers)
        notification_id = create_response.json()["data"]["_id"]
        
        # Mark as read
        response = await test_client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data["status_code"] == 200
        assert data["message"] == "Notification marked as read"
        assert data["data"] is not None
        assert data["error"] is None
        
        # Validate notification was marked as read
        assert data["data"]["is_read"] is True
        assert data["data"]["read_at"] is not None
        assert data["data"]["_id"] == notification_id
        
        # Cleanup
        await test_db.notifications.delete_many({"_id": notification_id})
    
    @pytest.mark.asyncio
    async def test_mark_all_notifications_as_read_updates_all(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test marking all notifications as read updates all unread notifications."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create multiple notifications
        for i in range(3):
            notification_data = {
                "type": "info",
                "title": f"Bulk Read Test {i}",
                "message": f"Test message {i}"
            }
            await test_client.post("/api/v1/notifications", json=notification_data, headers=headers)
        
        # Mark all as read
        response = await test_client.post("/api/v1/notifications/read-all", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data["status_code"] == 200
        assert data["message"] == "All notifications marked as read"
        assert data["data"] is not None
        assert data["error"] is None
        
        # Validate result
        assert "marked_count" in data["data"]
        assert isinstance(data["data"]["marked_count"], int)
        
        # Cleanup
        await test_db.notifications.delete_many({"title": {"$regex": "Bulk Read Test"}})


class TestNotificationDeletion:
    """Tests for deleting notifications."""
    
    @pytest.mark.asyncio
    async def test_delete_notification_marks_as_deleted(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test deleting notification marks it as deleted."""
        headers = {"Authorization": f"Bearer {user_token}"}
        notification_data = {
            "type": "info",
            "title": "Delete Test",
            "message": "This will be deleted"
        }
        
        # Create notification
        create_response = await test_client.post("/api/v1/notifications", json=notification_data, headers=headers)
        notification_id = create_response.json()["data"]["_id"]
        
        # Delete notification
        response = await test_client.delete(f"/api/v1/notifications/{notification_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data["status_code"] == 200
        assert data["message"] == "Notification deleted successfully"
        assert data["data"] is not None
        assert data["error"] is None
        
        # Verify soft delete in database
        from bson import ObjectId
        deleted_notification = await test_db.notifications.find_one({"_id": ObjectId(notification_id)})
        assert deleted_notification is not None
        assert deleted_notification["is_deleted"] is True
        
        # Cleanup
        await test_db.notifications.delete_many({"_id": ObjectId(notification_id)})
    
    @pytest.mark.asyncio
    async def test_deleted_notifications_not_returned_in_list(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test that deleted notifications are not returned in list."""
        headers = {"Authorization": f"Bearer {user_token}"}
        notification_data = {
            "type": "info",
            "title": "Deleted List Test",
            "message": "This should not appear"
        }
        
        # Create notification
        create_response = await test_client.post("/api/v1/notifications", json=notification_data, headers=headers)
        notification_id = create_response.json()["data"]["_id"]
        
        # Delete notification
        await test_client.delete(f"/api/v1/notifications/{notification_id}", headers=headers)
        
        # List notifications
        response = await test_client.get("/api/v1/notifications", headers=headers)
        data = response.json()
        
        # Deleted notification should not be in list
        notification_ids = [n["_id"] for n in data["data"]["items"]]
        assert notification_id not in notification_ids
        
        # Cleanup
        from bson import ObjectId
        await test_db.notifications.delete_many({"_id": ObjectId(notification_id)})


class TestNotificationUnreadCount:
    """Tests for getting unread notification count."""
    
    @pytest.mark.asyncio
    async def test_get_unread_count_returns_count(
        self,
        test_client: AsyncClient,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test getting unread count returns correct count."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create notifications
        for i in range(5):
            notification_data = {
                "type": "info",
                "title": f"Unread Count Test {i}",
                "message": f"Message {i}"
            }
            await test_client.post("/api/v1/notifications", json=notification_data, headers=headers)
        
        # Get unread count
        response = await test_client.get("/api/v1/notifications/unread-count", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data["status_code"] == 200
        assert data["message"] == "Unread count retrieved successfully"
        assert data["data"] is not None
        assert data["error"] is None
        
        # Validate unread count
        assert "unread_count" in data["data"]
        assert isinstance(data["data"]["unread_count"], int)
        assert data["data"]["unread_count"] >= 5
        
        # Cleanup
        await test_db.notifications.delete_many({"title": {"$regex": "Unread Count Test"}})

