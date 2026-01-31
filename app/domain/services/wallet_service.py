"""
Wallet Service

Business logic for wallet management.
Handles both shared collections (wallet definitions) and mode-specific collections (user wallets).
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId

from app.domain.models.wallet import WalletDefinition, IntegrationType, WalletStatus
from app.domain.models.user_wallet import UserWallet, UserWalletStatus
from app.modules.user_wallets.repository import UserWalletRepository
from app.core.database import db_provider
from app.core.context import TradingMode
from app.utils.encryption import get_encryption_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WalletService:
    """
    Wallet Service
    
    Handles wallet business logic:
    - Wallet definitions (shared collection)
    - User wallet instances (mode-specific)
    - Connection testing
    - Balance syncing
    """
    
    def __init__(self, user_wallet_repo: UserWalletRepository):
        """
        Initialize wallet service.
        
        Args:
            user_wallet_repo: User wallet repository instance
        """
        self.user_wallet_repo = user_wallet_repo
    
    async def get_wallet_definitions(
        self,
        is_active: Optional[bool] = None,
        integration_type: Optional[str] = None
    ) -> List[WalletDefinition]:
        """
        Get wallet provider definitions.
        
        Note: Wallet definitions are shared between real/demo databases.
        We use the demo database to access the shared collection.
        
        Args:
            is_active: Filter by active status (optional)
            integration_type: Filter by integration type (optional)
            
        Returns:
            List of wallet definitions
        """
        # Use demo database for shared collection
        db = db_provider.get_db_for_mode(TradingMode.DEMO)
        
        query: Dict[str, Any] = {"deleted_at": None}
        
        if is_active is not None:
            query["is_active"] = is_active
        
        if integration_type:
            query["integration_type"] = integration_type.lower()
        
        wallets = await db.wallets.find(query).sort("name", 1).to_list(length=100)
        
        # Convert to domain models
        definitions = []
        for wallet in wallets:
            # Convert ObjectId to string
            wallet_id = wallet.pop("_id")
            wallet["id"] = str(wallet_id)
            
            # Ensure required fields with defaults
            wallet.setdefault("required_credentials", [])
            wallet.setdefault("supported_symbols", [])
            wallet.setdefault("supported_order_types", ["market", "limit"])
            wallet.setdefault("supports_margin", False)
            wallet.setdefault("supports_futures", False)
            wallet.setdefault("description", None)
            wallet.setdefault("logo_url", None)
            wallet.setdefault("min_trade_amount", None)
            wallet.setdefault("max_leverage", None)
            wallet.setdefault("docs_url", None)
            wallet.setdefault("api_version", None)
            
            definitions.append(WalletDefinition(**wallet))
        
        logger.debug(f"Found {len(definitions)} wallet definitions")
        
        return definitions
    
    async def get_wallet_definition(self, wallet_id: str) -> Optional[WalletDefinition]:
        """
        Get single wallet definition.
        
        Args:
            wallet_id: Wallet definition ID
            
        Returns:
            Wallet definition or None if not found
        """
        # Use demo database for shared collection
        db = db_provider.get_db_for_mode(TradingMode.DEMO)
        
        wallet = await db.wallets.find_one({
            "_id": ObjectId(wallet_id),
            "deleted_at": None
        })
        
        if not wallet:
            return None
        
        wallet_id = wallet.pop("_id")
        wallet["id"] = str(wallet_id)
        
        # Ensure required fields with defaults
        wallet.setdefault("required_credentials", [])
        wallet.setdefault("supported_symbols", [])
        wallet.setdefault("supported_order_types", ["market", "limit"])
        wallet.setdefault("supports_margin", False)
        wallet.setdefault("supports_futures", False)
        wallet.setdefault("description", None)
        wallet.setdefault("logo_url", None)
        wallet.setdefault("min_trade_amount", None)
        wallet.setdefault("max_leverage", None)
        wallet.setdefault("docs_url", None)
        wallet.setdefault("api_version", None)
        
        return WalletDefinition(**wallet)
    
    async def create_user_wallet(
        self,
        user_id: str,
        wallet_provider_id: str,
        custom_name: str,
        credentials: Dict[str, str],
        risk_limits: Optional[Dict[str, float]] = None,
        use_testnet: bool = False
    ) -> UserWallet:
        """
        Create user wallet connection.
        
        Args:
            user_id: User ID
            wallet_provider_id: Wallet provider ID
            custom_name: User's custom name
            credentials: Plain credentials (will be encrypted)
            risk_limits: Risk limits (optional)
            use_testnet: Use testnet/demo network
            
        Returns:
            Created user wallet
            
        Raises:
            ValueError: If validation fails
        """
        # Validate wallet provider exists (check shared collection)
        db_shared = db_provider.get_db_for_mode(TradingMode.DEMO)
        provider = await db_shared.wallets.find_one({
            "_id": ObjectId(wallet_provider_id),
            "deleted_at": None
        })
        
        if not provider:
            raise ValueError(f"Wallet provider {wallet_provider_id} not found")
        
        if not provider.get("is_active", False):
            raise ValueError(f"Wallet provider {provider['name']} is not active")
        
        # Check custom_name uniqueness for user (check mode-specific collection)
        existing = await self.user_wallet_repo.find_by_user(user_id)
        for existing_wallet in existing:
            if existing_wallet.custom_name == custom_name:
                raise ValueError(f"You already have a wallet named '{custom_name}'")
        
        # Encrypt credentials
        encryption = get_encryption_service()
        encrypted_credentials = encryption.encrypt_credentials(credentials)
        
        # Create user wallet domain model
        user_wallet = UserWallet(
            user_id=user_id,
            wallet_provider_id=wallet_provider_id,
            custom_name=custom_name,
            is_active=True,
            use_testnet=use_testnet,
            credentials=encrypted_credentials,
            connection_status=UserWalletStatus.DISCONNECTED,
            risk_limits=risk_limits or {
                "max_position_size_usd": 1000.00,
                "daily_loss_limit": 100.00,
                "stop_loss_default_percent": 0.02
            },
        )
        
        # Save via repository (automatically routes to correct DB)
        user_wallet = await self.user_wallet_repo.save(user_wallet)
        
        logger.info(
            f"Created user wallet: user={user_id}, provider={provider['name']}, "
            f"name={custom_name}"
        )
        
        return user_wallet
    
    async def get_user_wallet(self, wallet_id: str) -> Optional[UserWallet]:
        """
        Get user wallet by ID.
        
        Args:
            wallet_id: User wallet ID
            
        Returns:
            UserWallet or None if not found
        """
        return await self.user_wallet_repo.find_by_id(wallet_id)
    
    async def get_user_wallets(
        self,
        user_id: str,
        is_active: Optional[bool] = None
    ) -> List[UserWallet]:
        """
        Get user wallets for a user.
        
        Args:
            user_id: User ID
            is_active: Optional active status filter
            
        Returns:
            List of user wallets
        """
        return await self.user_wallet_repo.find_by_user(user_id, is_active=is_active)
    
    async def update_user_wallet(
        self,
        wallet_id: str,
        custom_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        risk_limits: Optional[Dict[str, Any]] = None
    ) -> UserWallet:
        """
        Update user wallet.
        
        Args:
            wallet_id: User wallet ID
            custom_name: New custom name (optional)
            is_active: New active status (optional)
            risk_limits: New risk limits (optional)
            
        Returns:
            Updated user wallet
            
        Raises:
            ValueError: If wallet not found
        """
        user_wallet = await self.user_wallet_repo.find_by_id(wallet_id)
        if not user_wallet:
            raise ValueError(f"User wallet not found: {wallet_id}")
        
        if custom_name is not None:
            user_wallet.custom_name = custom_name
        if is_active is not None:
            user_wallet.is_active = is_active
        if risk_limits is not None:
            user_wallet.risk_limits = risk_limits
        
        user_wallet.updated_at = datetime.now(timezone.utc)
        
        user_wallet = await self.user_wallet_repo.save(user_wallet)
        
        logger.info(f"Updated user wallet {wallet_id}")
        
        return user_wallet
    
    async def delete_user_wallet(self, wallet_id: str) -> bool:
        """
        Delete (soft delete) a user wallet.
        
        Args:
            wallet_id: User wallet ID
            
        Returns:
            True if wallet was deleted
            
        Raises:
            ValueError: If wallet not found
        """
        user_wallet = await self.user_wallet_repo.find_by_id(wallet_id)
        if not user_wallet:
            raise ValueError(f"User wallet not found: {wallet_id}")
        
        return await self.user_wallet_repo.delete_one(wallet_id)
    
    async def test_connection(self, wallet_id: str) -> Dict[str, Any]:
        """
        Test wallet connection.
        
        Args:
            wallet_id: User wallet ID
            
        Returns:
            Connection test result
            
        Raises:
            ValueError: If wallet not found
        """
        from app.integrations.wallets.factory import WalletFactory
        
        user_wallet = await self.user_wallet_repo.find_by_id(wallet_id)
        if not user_wallet:
            raise ValueError(f"User wallet not found: {wallet_id}")
        
        # Get correct database based on context
        db = db_provider.get_db()
        
        # Create wallet instance and test connection
        factory = WalletFactory()
        wallet = await factory.create_wallet_from_db(
            db=db,
            user_wallet_id=str(user_wallet.id)
        )
        
        try:
            # Test connection
            await wallet.get_balance("USDT")  # Try to get balance
            
            # Update connection status
            user_wallet.connection_status = UserWalletStatus.CONNECTED
            user_wallet.last_connection_test = datetime.now(timezone.utc)
            user_wallet.last_connection_error = None
            await self.user_wallet_repo.save(user_wallet)
            
            return {
                "success": True,
                "message": "Connection successful",
                "status": "connected"
            }
        except Exception as e:
            # Update connection status
            user_wallet.connection_status = UserWalletStatus.ERROR
            user_wallet.last_connection_error = str(e)
            await self.user_wallet_repo.save(user_wallet)
            
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "status": "error",
                "error": str(e)
            }
    
    async def sync_balance(self, wallet_id: str) -> Dict[str, Any]:
        """
        Sync balance from exchange.
        
        Args:
            wallet_id: User wallet ID
            
        Returns:
            Sync result with balance snapshot
            
        Raises:
            ValueError: If wallet not found
        """
        from app.integrations.wallets.factory import WalletFactory
        
        user_wallet = await self.user_wallet_repo.find_by_id(wallet_id)
        if not user_wallet:
            raise ValueError(f"User wallet not found: {wallet_id}")
        
        # Get correct database based on context
        db = db_provider.get_db()
        
        # Create wallet instance and sync balance
        factory = WalletFactory()
        wallet = await factory.create_wallet_from_db(
            db=db,
            user_wallet_id=str(user_wallet.id)
        )
        
        try:
            # Get all balances
            balances = await wallet.get_all_balances()
            
            # Update user wallet balance
            user_wallet.balance = balances
            user_wallet.balance_last_synced = datetime.now(timezone.utc)
            await self.user_wallet_repo.save(user_wallet)
            
            return {
                "success": True,
                "balance": balances,
                "synced_at": user_wallet.balance_last_synced.isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to sync balance for wallet {wallet_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
