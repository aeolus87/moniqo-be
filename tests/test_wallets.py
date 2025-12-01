"""
Test suite for wallets module.

Tests wallet definition CRUD operations, filtering, and admin functionalities.
"""

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId


class TestWalletDefinitions:
    """Test wallet definition operations."""
    
    @pytest.mark.asyncio
    async def test_create_wallet_definition_with_valid_data_returns_201(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test creating wallet definition with valid data as admin."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Leading cryptocurrency exchange",
            "auth_fields": [
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "string",
                    "required": True,
                    "encrypted": False,
                    "placeholder": "Enter your API key",
                    "help_text": "Find this in your account settings"
                }
            ],
            "features": {
                "spot": True,
                "futures": True,
                "perpetuals": True,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC", "ETH", "USDT"]
            },
            "api_config": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            },
            "is_active": True,
            "order": 1
        }
        
        response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status_code"] == 201
        assert data["data"] is not None
        assert data["data"]["name"] == "Binance"
        assert data["data"]["slug"] == "binance"
        assert data["data"]["type"] == "cex"
    
    @pytest.mark.asyncio
    async def test_create_wallet_definition_with_duplicate_slug_returns_400(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating wallet with duplicate slug fails."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        # Create first wallet
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Leading cryptocurrency exchange",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC"]
            },
            "api_config": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            },
            "is_active": True,
            "order": 1
        }
        
        await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=headers
        )
        
        # Try to create duplicate
        response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["status_code"] == 400
        assert "duplicate" in data["error"]["message"].lower() or "already exists" in data["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_create_wallet_definition_without_auth_returns_401(
        self,
        test_client: AsyncClient
    ):
        """Test creating wallet without authentication fails."""
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC"]
            },
            "api_config": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            },
            "is_active": True,
            "order": 1
        }
        
        response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_wallet_definition_as_user_returns_403(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test creating wallet as regular user fails."""
        headers = {"Authorization": f"Bearer {user_token}"}
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC"]
            },
            "api_config": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            },
            "is_active": True,
            "order": 1
        }
        
        response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=headers
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_list_wallet_definitions_returns_200(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test listing wallet definitions returns 200."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        # Create a test wallet
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test exchange",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC"]
            },
            "api_config": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            },
            "is_active": True,
            "order": 1
        }
        
        await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=headers
        )
        
        # List wallets (public endpoint, no auth needed)
        response = await test_client.get("/api/v1/wallets/definitions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "items" in data["data"] or isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_list_wallet_definitions_filters_by_type(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test listing wallets filters by type."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        # Create CEX wallet
        cex_wallet = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "CEX exchange",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC"]
            },
            "api_config": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            },
            "is_active": True,
            "order": 1
        }
        
        # Create DEX wallet
        dex_wallet = {
            "name": "Uniswap",
            "slug": "uniswap",
            "type": "dex",
            "description": "DEX exchange",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 1},
                "supported_assets": ["ETH"]
            },
            "api_config": {
                "base_url": "https://api.uniswap.org",
                "testnet_url": "https://testnet.uniswap.org",
                "websocket_url": "wss://api.uniswap.org/ws",
                "rate_limit": 100
            },
            "is_active": True,
            "order": 2
        }
        
        await test_client.post("/api/v1/wallets/definitions", json=cex_wallet, headers=headers)
        await test_client.post("/api/v1/wallets/definitions", json=dex_wallet, headers=headers)
        
        # Filter by type=cex
        response = await test_client.get("/api/v1/wallets/definitions?type=cex")
        
        assert response.status_code == 200
        data = response.json()
        items = data["data"].get("items", data["data"]) if isinstance(data["data"], dict) else data["data"]
        assert all(wallet["type"] == "cex" for wallet in items)
    
    @pytest.mark.asyncio
    async def test_list_wallet_definitions_filters_by_is_active(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test listing wallets filters by is_active."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        # Create active wallet
        active_wallet = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Active exchange",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC"]
            },
            "api_config": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            },
            "is_active": True,
            "order": 1
        }
        
        # Create inactive wallet
        inactive_wallet = {
            "name": "OldExchange",
            "slug": "oldexchange",
            "type": "cex",
            "description": "Inactive exchange",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 10},
                "supported_assets": ["BTC"]
            },
            "api_config": {
                "base_url": "https://api.oldexchange.com",
                "testnet_url": "https://testnet.oldexchange.com",
                "websocket_url": "wss://api.oldexchange.com/ws",
                "rate_limit": 100
            },
            "is_active": False,
            "order": 2
        }
        
        await test_client.post("/api/v1/wallets/definitions", json=active_wallet, headers=headers)
        await test_client.post("/api/v1/wallets/definitions", json=inactive_wallet, headers=headers)
        
        # Filter by is_active=true
        response = await test_client.get("/api/v1/wallets/definitions?is_active=true")
        
        assert response.status_code == 200
        data = response.json()
        items = data["data"].get("items", data["data"]) if isinstance(data["data"], dict) else data["data"]
        assert all(wallet["is_active"] is True for wallet in items)
    
    @pytest.mark.asyncio
    async def test_get_wallet_definition_by_slug_returns_200(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test getting wallet by slug returns 200."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test exchange",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC"]
            },
            "api_config": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            },
            "is_active": True,
            "order": 1
        }
        
        await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=headers
        )
        
        # Get wallet by slug (public endpoint)
        response = await test_client.get("/api/v1/wallets/definitions/binance")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["data"]["slug"] == "binance"
        assert data["data"]["name"] == "Binance"
    
    @pytest.mark.asyncio
    async def test_get_wallet_definition_invalid_slug_returns_404(
        self,
        test_client: AsyncClient
    ):
        """Test getting wallet with invalid slug returns 404."""
        response = await test_client.get("/api/v1/wallets/definitions/invalid-slug")
        
        assert response.status_code == 404
        data = response.json()
        assert data["status_code"] == 404
    
    @pytest.mark.asyncio
    async def test_update_wallet_definition_as_admin_returns_200(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test updating wallet definition as admin returns 200."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        # Create wallet
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Original description",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC"]
            },
            "api_config": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            },
            "is_active": True,
            "order": 1
        }
        
        create_response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=headers
        )
        
        # Update wallet
        update_data = {
            "description": "Updated description"
        }
        
        response = await test_client.patch(
            "/api/v1/wallets/definitions/binance",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["data"]["description"] == "Updated description"
    
    @pytest.mark.asyncio
    async def test_update_wallet_definition_as_user_returns_403(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        user_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test updating wallet as regular user fails."""
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create wallet as admin
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC"]
            },
            "api_config": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            },
            "is_active": True,
            "order": 1
        }
        
        await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=admin_headers
        )
        
        # Try to update as user
        update_data = {"description": "Hacked"}
        response = await test_client.patch(
            "/api/v1/wallets/definitions/binance",
            json=update_data,
            headers=user_headers
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_delete_wallet_definition_as_admin_returns_200(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test deleting wallet definition as admin returns 200."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        # Create wallet
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC"]
            },
            "api_config": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            },
            "is_active": True,
            "order": 1
        }
        
        await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=headers
        )
        
        # Delete wallet
        response = await test_client.delete(
            "/api/v1/wallets/definitions/binance",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
    
    @pytest.mark.asyncio
    async def test_delete_wallet_definition_soft_deletes(
        self,
        test_client: AsyncClient,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test deleting wallet soft deletes (sets is_active=False)."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        # Create wallet
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test",
            "auth_fields": [],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC"]
            },
            "api_config": {
                "base_url": "https://api.binance.com",
                "testnet_url": "https://testnet.binance.vision",
                "websocket_url": "wss://stream.binance.com:9443",
                "rate_limit": 1200
            },
            "is_active": True,
            "order": 1
        }
        
        await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=headers
        )
        
        # Delete wallet
        await test_client.delete(
            "/api/v1/wallets/definitions/binance",
            headers=headers
        )
        
        # Verify wallet still exists but is_active=False
        wallet = await test_db.wallets.find_one({"slug": "binance"})
        assert wallet is not None
        assert wallet["is_active"] is False
        
        # Verify it's not returned in active list
        response = await test_client.get("/api/v1/wallets/definitions?is_active=true")
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert "data" in data
        if data["data"] and isinstance(data["data"], dict) and "items" in data["data"]:
            items = data["data"]["items"]
        elif isinstance(data["data"], list):
            items = data["data"]
        else:
            items = []
        assert not any(w["slug"] == "binance" for w in items)
    
    @pytest.mark.asyncio
    async def test_create_wallet_definition_with_missing_required_fields_returns_422(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test creating wallet without required fields fails."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        wallet_data = {
            "name": "Binance",
            # Missing slug, type, features, api_config
        }
        
        response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=headers
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_update_wallet_definition_nonexistent_returns_404(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test updating non-existent wallet returns 404."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        update_data = {"description": "Updated"}
        
        response = await test_client.patch(
            "/api/v1/wallets/definitions/nonexistent-slug",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_wallet_definition_nonexistent_returns_404(
        self,
        test_client: AsyncClient,
        superuser_token: str
    ):
        """Test deleting non-existent wallet returns 404."""
        headers = {"Authorization": f"Bearer {superuser_token}"}
        
        response = await test_client.delete(
            "/api/v1/wallets/definitions/nonexistent-slug",
            headers=headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_wallet_definitions_with_invalid_filter_returns_200(
        self,
        test_client: AsyncClient
    ):
        """Test listing with invalid filter values still returns 200 (filters ignored)."""
        # Invalid type value
        response = await test_client.get("/api/v1/wallets/definitions?type=invalid_type")
        assert response.status_code == 200
        
        # Invalid is_active value
        response = await test_client.get("/api/v1/wallets/definitions?is_active=maybe")
        assert response.status_code == 200

