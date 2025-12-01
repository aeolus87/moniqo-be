"""
Wallet Factory

Factory pattern for creating wallet instances.
Handles wallet registration and instantiation based on provider type.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Dict, Type, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.integrations.wallets.base import BaseWallet
from app.integrations.wallets.demo_wallet import DemoWallet
from app.integrations.exchanges.binance_wallet import BinanceWallet
from app.utils.logger import get_logger
from app.utils.encryption import get_encryption_service

logger = get_logger(__name__)


class WalletFactoryError(Exception):
    """Wallet factory errors"""
    pass


class WalletNotRegisteredError(WalletFactoryError):
    """Wallet type not registered"""
    pass


class WalletFactory:
    """
    Wallet Factory
    
    Manages wallet implementation registration and instantiation.
    Uses Factory Pattern to abstract wallet creation.
    
    Usage:
        # Register wallet implementations
        factory = WalletFactory()
        factory.register("demo", DemoWallet)
        factory.register("binance", BinanceWallet)
        
        # Create wallet instance
        wallet = await factory.create_wallet(
            wallet_type="demo",
            wallet_id="demo-1",
            user_wallet_id="user_wallet_123",
            encrypted_credentials={...},
            **config
        )
    """
    
    def __init__(self):
        """Initialize factory"""
        self._wallets: Dict[str, Type[BaseWallet]] = {}
        self._register_default_wallets()
    
    def _register_default_wallets(self):
        """Register default wallet implementations"""
        self.register("demo", DemoWallet)
        self.register("simulation", DemoWallet)  # Alias
        
        # Real exchanges
        self.register("binance", BinanceWallet)
        self.register("binance-testnet", BinanceWallet)
        
        # Future: Register other wallets
        # self.register("coinbase", CoinbaseWallet)
        # self.register("kraken", KrakenWallet)
        
        logger.debug(f"Registered {len(self._wallets)} wallet types")
    
    def register(self, wallet_type: str, wallet_class: Type[BaseWallet]):
        """
        Register a wallet implementation.
        
        Args:
            wallet_type: Wallet type identifier (e.g., "binance", "demo")
            wallet_class: Wallet class (must inherit from BaseWallet)
            
        Raises:
            ValueError: If wallet_class doesn't inherit from BaseWallet
            
        Example:
            factory.register("binance", BinanceWallet)
        """
        if not issubclass(wallet_class, BaseWallet):
            raise ValueError(
                f"{wallet_class.__name__} must inherit from BaseWallet"
            )
        
        self._wallets[wallet_type.lower()] = wallet_class
        logger.info(f"Registered wallet type: {wallet_type} -> {wallet_class.__name__}")
    
    def unregister(self, wallet_type: str):
        """
        Unregister a wallet implementation.
        
        Args:
            wallet_type: Wallet type to remove
        """
        if wallet_type.lower() in self._wallets:
            del self._wallets[wallet_type.lower()]
            logger.info(f"Unregistered wallet type: {wallet_type}")
    
    def is_registered(self, wallet_type: str) -> bool:
        """
        Check if wallet type is registered.
        
        Args:
            wallet_type: Wallet type to check
            
        Returns:
            True if registered
        """
        return wallet_type.lower() in self._wallets
    
    def get_registered_types(self) -> list:
        """
        Get list of registered wallet types.
        
        Returns:
            List of wallet type strings
        """
        return list(self._wallets.keys())
    
    async def create_wallet(
        self,
        wallet_type: str,
        wallet_id: str,
        user_wallet_id: str,
        encrypted_credentials: Dict[str, str],
        **kwargs
    ) -> BaseWallet:
        """
        Create wallet instance.
        
        Args:
            wallet_type: Type of wallet (must be registered)
            wallet_id: Wallet provider ID
            user_wallet_id: User wallet instance ID
            encrypted_credentials: Encrypted credentials dict
            **kwargs: Additional wallet-specific configuration
            
        Returns:
            BaseWallet instance
            
        Raises:
            WalletNotRegisteredError: If wallet type not registered
            
        Example:
            wallet = await factory.create_wallet(
                wallet_type="demo",
                wallet_id="demo-wallet-001",
                user_wallet_id="user_wallet_123",
                encrypted_credentials={},
                initial_balance={"USDT": 10000}
            )
        """
        wallet_type_lower = wallet_type.lower()
        
        if wallet_type_lower not in self._wallets:
            raise WalletNotRegisteredError(
                f"Wallet type '{wallet_type}' is not registered. "
                f"Available types: {self.get_registered_types()}"
            )
        
        # Decrypt credentials
        encryption = get_encryption_service()
        decrypted_credentials = encryption.decrypt_credentials(encrypted_credentials)
        
        # Get wallet class
        wallet_class = self._wallets[wallet_type_lower]
        
        # Create instance
        wallet = wallet_class(
            wallet_id=wallet_id,
            user_wallet_id=user_wallet_id,
            credentials=decrypted_credentials,
            **kwargs
        )
        
        logger.info(
            f"Created {wallet_class.__name__} instance: "
            f"wallet_id={wallet_id}, user_wallet_id={user_wallet_id}"
        )
        
        return wallet
    
    async def create_wallet_from_db(
        self,
        db: AsyncIOMotorDatabase,
        user_wallet_id: str
    ) -> BaseWallet:
        """
        Create wallet instance from database record.
        
        Loads user_wallet and wallet_provider from database,
        then creates appropriate wallet instance.
        
        Args:
            db: MongoDB database instance
            user_wallet_id: User wallet ID
            
        Returns:
            BaseWallet instance
            
        Raises:
            ValueError: If user_wallet or wallet_provider not found
            WalletNotRegisteredError: If wallet type not registered
            
        Example:
            wallet = await factory.create_wallet_from_db(db, "user_wallet_123")
            balance = await wallet.get_balance("USDT")
        """
        from bson import ObjectId
        
        # Load user_wallet
        user_wallet = await db.user_wallets.find_one({
            "_id": ObjectId(user_wallet_id),
            "deleted_at": None
        })
        
        if not user_wallet:
            raise ValueError(f"User wallet {user_wallet_id} not found")
        
        # Load wallet_provider
        wallet_provider = await db.wallets.find_one({
            "_id": ObjectId(user_wallet["wallet_provider_id"]),
            "deleted_at": None
        })
        
        if not wallet_provider:
            raise ValueError(
                f"Wallet provider {user_wallet['wallet_provider_id']} not found"
            )
        
        # Determine wallet type from integration_type or slug
        wallet_type = wallet_provider.get("slug", wallet_provider.get("integration_type", "")).split("-")[0]
        
        # Create wallet
        wallet = await self.create_wallet(
            wallet_type=wallet_type,
            wallet_id=str(wallet_provider["_id"]),
            user_wallet_id=str(user_wallet["_id"]),
            encrypted_credentials=user_wallet.get("credentials", {}),
            # Pass additional config from wallet_provider
            **wallet_provider.get("config", {})
        )
        
        return wallet


# Global factory instance
_wallet_factory = None


def get_wallet_factory() -> WalletFactory:
    """
    Get global wallet factory instance (singleton).
    
    Returns:
        Shared WalletFactory instance
    """
    global _wallet_factory
    
    if _wallet_factory is None:
        _wallet_factory = WalletFactory()
    
    return _wallet_factory


# Convenience function
async def create_wallet_from_db(
    db: AsyncIOMotorDatabase,
    user_wallet_id: str
) -> BaseWallet:
    """
    Convenience function: Create wallet from database.
    
    Example:
        from app.integrations.wallets.factory import create_wallet_from_db
        
        wallet = await create_wallet_from_db(db, "user_wallet_123")
        balance = await wallet.get_balance("USDT")
    """
    factory = get_wallet_factory()
    return await factory.create_wallet_from_db(db, user_wallet_id)

