"""
Test suite for user_wallets module.

Tests user wallet instance CRUD operations, symbol validation, AI state initialization, pause/resume.
"""

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId


class TestUserWalletsOperations:
    """Test user wallet operations."""
    
    @pytest.mark.asyncio
    async def test_create_user_wallet_with_valid_data_returns_201(
        self,
        test_client: AsyncClient,
        user_token: str,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating user wallet with valid data."""
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create wallet and credentials first
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test",
            "auth_fields": [
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "string",
                    "required": True,
                    "encrypted": False,
                    "placeholder": "Enter key",
                    "help_text": "Key"
                }
            ],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
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
        
        wallet_response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=admin_headers
        )
        wallet_id = wallet_response.json()["data"]["id"]
        
        credentials_data = {
            "wallet_id": wallet_id,
            "name": "My Account",
            "credentials": {"api_key": "test_key"},
            "environment": "testnet"
        }
        
        cred_response = await test_client.post(
            "/api/v1/wallets/credentials",
            json=credentials_data,
            headers=user_headers
        )
        credential_id = cred_response.json()["data"]["id"]
        
        # Create user wallet
        user_wallet_data = {
            "credential_id": credential_id,
            "name": "My Trading Wallet",
            "user_limits": {
                "max_total_risk": 1000.0,
                "allowed_symbols": ["BTC/USDT", "ETH/USDT"],
                "trading_mode": "moderate"
            }
        }
        
        response = await test_client.post(
            "/api/v1/wallets",
            json=user_wallet_data,
            headers=user_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status_code"] == 201
        assert data["data"] is not None
        assert data["data"]["name"] == "My Trading Wallet"
        assert data["data"]["user_limits"]["max_total_risk"] == 1000.0
        # Check AI managed state is initialized
        assert "ai_managed_state" in data["data"]
        assert data["data"]["ai_managed_state"]["current_risk"] == 0.0
    
    @pytest.mark.asyncio
    async def test_create_user_wallet_validates_symbols_against_wallet_features(
        self,
        test_client: AsyncClient,
        user_token: str,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test that allowed_symbols must be subset of wallet supported_assets."""
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create wallet with limited supported assets
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test",
            "auth_fields": [
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "string",
                    "required": True,
                    "encrypted": False,
                    "placeholder": "Enter key",
                    "help_text": "Key"
                }
            ],
            "features": {
                "spot": True,
                "futures": False,
                "perpetuals": False,
                "leverage": {"min": 1, "max": 125},
                "supported_assets": ["BTC", "ETH"]  # Only BTC and ETH
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
        
        wallet_response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=admin_headers
        )
        wallet_id = wallet_response.json()["data"]["id"]
        
        credentials_data = {
            "wallet_id": wallet_id,
            "name": "My Account",
            "credentials": {"api_key": "test_key"},
            "environment": "testnet"
        }
        
        cred_response = await test_client.post(
            "/api/v1/wallets/credentials",
            json=credentials_data,
            headers=user_headers
        )
        credential_id = cred_response.json()["data"]["id"]
        
        # Try to create wallet with unsupported symbol
        user_wallet_data = {
            "credential_id": credential_id,
            "name": "My Wallet",
            "user_limits": {
                "max_total_risk": 1000.0,
                "allowed_symbols": ["SOL/USDT"],  # SOL not in supported_assets
                "trading_mode": "moderate"
            }
        }
        
        response = await test_client.post(
            "/api/v1/wallets",
            json=user_wallet_data,
            headers=user_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["status_code"] == 400
    
    @pytest.mark.asyncio
    async def test_list_user_wallets_returns_200(
        self,
        test_client: AsyncClient,
        user_token: str,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test listing user wallets returns 200."""
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create wallet, credentials, and user_wallet
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test",
            "auth_fields": [
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "string",
                    "required": True,
                    "encrypted": False,
                    "placeholder": "Enter key",
                    "help_text": "Key"
                }
            ],
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
        
        wallet_response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=admin_headers
        )
        wallet_id = wallet_response.json()["data"]["id"]
        
        credentials_data = {
            "wallet_id": wallet_id,
            "name": "My Account",
            "credentials": {"api_key": "test_key"},
            "environment": "testnet"
        }
        
        cred_response = await test_client.post(
            "/api/v1/wallets/credentials",
            json=credentials_data,
            headers=user_headers
        )
        credential_id = cred_response.json()["data"]["id"]
        
        user_wallet_data = {
            "credential_id": credential_id,
            "name": "My Wallet",
            "user_limits": {
                "max_total_risk": 1000.0,
                "allowed_symbols": None,
                "trading_mode": "moderate"
            }
        }
        
        await test_client.post(
            "/api/v1/wallets",
            json=user_wallet_data,
            headers=user_headers
        )
        
        # List wallets
        response = await test_client.get(
            "/api/v1/wallets",
            headers=user_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        items = data["data"].get("items", data["data"]) if isinstance(data["data"], dict) else data["data"]
        assert len(items) >= 1
    
    @pytest.mark.asyncio
    async def test_pause_user_wallet_returns_200(
        self,
        test_client: AsyncClient,
        user_token: str,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test pausing user wallet returns 200."""
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create wallet, credentials, and user_wallet
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test",
            "auth_fields": [
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "string",
                    "required": True,
                    "encrypted": False,
                    "placeholder": "Enter key",
                    "help_text": "Key"
                }
            ],
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
        
        wallet_response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=admin_headers
        )
        wallet_id = wallet_response.json()["data"]["id"]
        
        credentials_data = {
            "wallet_id": wallet_id,
            "name": "My Account",
            "credentials": {"api_key": "test_key"},
            "environment": "testnet"
        }
        
        cred_response = await test_client.post(
            "/api/v1/wallets/credentials",
            json=credentials_data,
            headers=user_headers
        )
        credential_id = cred_response.json()["data"]["id"]
        
        user_wallet_data = {
            "credential_id": credential_id,
            "name": "My Wallet",
            "user_limits": {
                "max_total_risk": 1000.0,
                "allowed_symbols": None,
                "trading_mode": "moderate"
            }
        }
        
        create_response = await test_client.post(
            "/api/v1/wallets",
            json=user_wallet_data,
            headers=user_headers
        )
        wallet_instance_id = create_response.json()["data"]["id"]
        
        # Pause wallet
        response = await test_client.patch(
            f"/api/v1/wallets/{wallet_instance_id}/pause",
            headers=user_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["data"]["status"] == "user_paused"
    
    @pytest.mark.asyncio
    async def test_resume_user_wallet_returns_200(
        self,
        test_client: AsyncClient,
        user_token: str,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test resuming user wallet returns 200."""
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create wallet, credentials, and user_wallet
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test",
            "auth_fields": [
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "string",
                    "required": True,
                    "encrypted": False,
                    "placeholder": "Enter key",
                    "help_text": "Key"
                }
            ],
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
        
        wallet_response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=admin_headers
        )
        wallet_id = wallet_response.json()["data"]["id"]
        
        credentials_data = {
            "wallet_id": wallet_id,
            "name": "My Account",
            "credentials": {"api_key": "test_key"},
            "environment": "testnet"
        }
        
        cred_response = await test_client.post(
            "/api/v1/wallets/credentials",
            json=credentials_data,
            headers=user_headers
        )
        credential_id = cred_response.json()["data"]["id"]
        
        user_wallet_data = {
            "credential_id": credential_id,
            "name": "My Wallet",
            "user_limits": {
                "max_total_risk": 1000.0,
                "allowed_symbols": None,
                "trading_mode": "moderate"
            }
        }
        
        create_response = await test_client.post(
            "/api/v1/wallets",
            json=user_wallet_data,
            headers=user_headers
        )
        wallet_instance_id = create_response.json()["data"]["id"]
        
        # Pause first
        await test_client.patch(
            f"/api/v1/wallets/{wallet_instance_id}/pause",
            headers=user_headers
        )
        
        # Resume wallet
        response = await test_client.patch(
            f"/api/v1/wallets/{wallet_instance_id}/resume",
            headers=user_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status_code"] == 200
        assert data["data"]["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_create_user_wallet_with_invalid_credential_id_returns_404(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test creating user wallet with non-existent credential_id fails."""
        headers = {"Authorization": f"Bearer {user_token}"}
        user_wallet_data = {
            "credential_id": str(ObjectId()),  # Non-existent credential
            "name": "My Wallet",
            "user_limits": {
                "max_total_risk": 1000.0,
                "allowed_symbols": None,
                "trading_mode": "moderate"
            }
        }
        
        response = await test_client.post(
            "/api/v1/wallets",
            json=user_wallet_data,
            headers=headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_user_wallet_without_auth_returns_401(
        self,
        test_client: AsyncClient,
        user_token: str,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating user wallet without authentication fails."""
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create wallet and credentials
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test",
            "auth_fields": [
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "string",
                    "required": True,
                    "encrypted": False,
                    "placeholder": "Enter key",
                    "help_text": "Key"
                }
            ],
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
        
        wallet_response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=admin_headers
        )
        wallet_id = wallet_response.json()["data"]["id"]
        
        credentials_data = {
            "wallet_id": wallet_id,
            "name": "My Account",
            "credentials": {"api_key": "test"},
            "environment": "testnet"
        }
        
        cred_response = await test_client.post(
            "/api/v1/wallets/credentials",
            json=credentials_data,
            headers=user_headers
        )
        credential_id = cred_response.json()["data"]["id"]
        
        user_wallet_data = {
            "credential_id": credential_id,
            "name": "My Wallet",
            "user_limits": {
                "max_total_risk": 1000.0,
                "allowed_symbols": None,
                "trading_mode": "moderate"
            }
        }
        
        response = await test_client.post(
            "/api/v1/wallets",
            json=user_wallet_data
            # No headers
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_user_wallet_with_invalid_user_limits_returns_400(
        self,
        test_client: AsyncClient,
        user_token: str,
        superuser_token: str,
        test_db: AsyncIOMotorDatabase
    ):
        """Test creating user wallet with invalid user_limits fails."""
        admin_headers = {"Authorization": f"Bearer {superuser_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create wallet and credentials
        wallet_data = {
            "name": "Binance",
            "slug": "binance",
            "type": "cex",
            "description": "Test",
            "auth_fields": [
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "string",
                    "required": True,
                    "encrypted": False,
                    "placeholder": "Enter key",
                    "help_text": "Key"
                }
            ],
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
        
        wallet_response = await test_client.post(
            "/api/v1/wallets/definitions",
            json=wallet_data,
            headers=admin_headers
        )
        wallet_id = wallet_response.json()["data"]["id"]
        
        credentials_data = {
            "wallet_id": wallet_id,
            "name": "My Account",
            "credentials": {"api_key": "test"},
            "environment": "testnet"
        }
        
        cred_response = await test_client.post(
            "/api/v1/wallets/credentials",
            json=credentials_data,
            headers=user_headers
        )
        credential_id = cred_response.json()["data"]["id"]
        
        # Invalid: negative max_total_risk
        user_wallet_data = {
            "credential_id": credential_id,
            "name": "My Wallet",
            "user_limits": {
                "max_total_risk": -100.0,  # Invalid negative value
                "allowed_symbols": None,
                "trading_mode": "moderate"
            }
        }
        
        response = await test_client.post(
            "/api/v1/wallets",
            json=user_wallet_data,
            headers=user_headers
        )
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_get_user_wallet_nonexistent_returns_404(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test getting non-existent user wallet returns 404."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        response = await test_client.get(
            f"/api/v1/wallets/{str(ObjectId())}",
            headers=headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_user_wallet_nonexistent_returns_404(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test updating non-existent user wallet returns 404."""
        headers = {"Authorization": f"Bearer {user_token}"}
        update_data = {"name": "Updated"}
        
        response = await test_client.patch(
            f"/api/v1/wallets/{str(ObjectId())}",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_user_wallet_nonexistent_returns_404(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test deleting non-existent user wallet returns 404."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        response = await test_client.delete(
            f"/api/v1/wallets/{str(ObjectId())}",
            headers=headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_pause_user_wallet_nonexistent_returns_404(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test pausing non-existent user wallet returns 404."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        response = await test_client.patch(
            f"/api/v1/wallets/{str(ObjectId())}/pause",
            headers=headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_resume_user_wallet_nonexistent_returns_404(
        self,
        test_client: AsyncClient,
        user_token: str
    ):
        """Test resuming non-existent user wallet returns 404."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        response = await test_client.patch(
            f"/api/v1/wallets/{str(ObjectId())}/resume",
            headers=headers
        )
        
        assert response.status_code == 404

