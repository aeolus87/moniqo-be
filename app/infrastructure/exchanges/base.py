"""
BaseWallet - Abstract Wallet Interface

Defines the contract that all wallet implementations must follow.
This enables swapping between Demo, Binance, Coinbase, etc. without code changes.

Architecture Pattern: Strategy Pattern + Template Method

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


# ==================== ENUMS ====================

class OrderSide(str, Enum):
    """Order side (direction)"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LOSS_LIMIT = "stop_loss_limit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


class OrderStatus(str, Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


class TimeInForce(str, Enum):
    """Time in force for orders"""
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    GTD = "GTD"  # Good Till Date


# ==================== EXCEPTIONS ====================

class WalletError(Exception):
    """Base exception for wallet errors"""
    pass


class WalletConnectionError(WalletError):
    """Connection to wallet/exchange failed"""
    pass


class InsufficientFundsError(WalletError):
    """Not enough balance for operation"""
    pass


class InvalidOrderError(WalletError):
    """Order parameters are invalid"""
    pass


class OrderNotFoundError(WalletError):
    """Order does not exist"""
    pass


class SymbolNotSupportedError(WalletError):
    """Trading pair is not supported"""
    pass


class RateLimitError(WalletError):
    """API rate limit exceeded"""
    pass


class AuthenticationError(WalletError):
    """Authentication failed (invalid API keys)"""
    pass


# ==================== BASE WALLET ====================

class BaseWallet(ABC):
    """
    Abstract base class for all wallet implementations.
    
    All wallet providers (Demo, Binance, Coinbase, etc.) must implement
    these methods to ensure consistent behavior across the platform.
    
    Usage:
        class MyWallet(BaseWallet):
            async def get_balance(self, asset: str) -> Decimal:
                # Implementation here
                pass
                
            # ... implement other methods
    """
    
    def __init__(
        self,
        wallet_id: str,
        user_wallet_id: str,
        credentials: Dict[str, str],
        **kwargs
    ):
        """
        Initialize wallet instance.
        
        Args:
            wallet_id: Wallet provider ID (from wallets collection)
            user_wallet_id: User wallet instance ID
            credentials: Decrypted credentials dictionary
            **kwargs: Additional provider-specific configuration
        """
        self.wallet_id = wallet_id
        self.user_wallet_id = user_wallet_id
        self.credentials = credentials
        self.config = kwargs
    
    # ==================== CORE TRADING OPERATIONS ====================
    
    @abstractmethod
    async def get_balance(self, asset: str) -> Decimal:
        """
        Get balance for a specific asset.
        
        Args:
            asset: Asset symbol (e.g., "USDT", "BTC")
            
        Returns:
            Decimal: Available balance
            
        Raises:
            WalletConnectionError: If connection fails
            AuthenticationError: If credentials are invalid
            
        Example:
            balance = await wallet.get_balance("USDT")
            print(f"USDT Balance: {balance}")  # 1000.00
        """
        pass
    
    @abstractmethod
    async def get_all_balances(self) -> Dict[str, Decimal]:
        """
        Get all non-zero balances.
        
        Returns:
            Dict mapping asset symbols to balances
            
        Example:
            balances = await wallet.get_all_balances()
            # {"USDT": Decimal("1000.00"), "BTC": Decimal("0.5")}
        """
        pass
    
    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Place a trading order.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            side: "buy" or "sell"
            order_type: Order type (market, limit, stop_loss, etc.)
            quantity: Order quantity (base asset)
            price: Limit price (required for limit orders)
            stop_price: Stop trigger price (for stop orders)
            time_in_force: Order time in force
            **kwargs: Additional order parameters
            
        Returns:
            Dict containing:
                - success: bool
                - order_id: str (exchange order ID)
                - client_order_id: str
                - status: OrderStatus
                - filled_quantity: Decimal
                - average_price: Decimal (if filled)
                - timestamp: datetime
                
        Raises:
            InsufficientFundsError: Not enough balance
            InvalidOrderError: Invalid order parameters
            SymbolNotSupportedError: Symbol not available
            RateLimitError: Too many requests
            
        Example:
            result = await wallet.place_order(
                symbol="BTC/USDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.1")
            )
            print(result["order_id"])  # "binance_12345"
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Cancel an open order.
        
        Args:
            order_id: Exchange order ID
            symbol: Trading pair (some exchanges require this)
            
        Returns:
            Dict containing:
                - success: bool
                - order_id: str
                - status: OrderStatus (should be "cancelled")
                - message: str
                
        Raises:
            OrderNotFoundError: Order does not exist
            WalletError: Order cannot be cancelled (already filled, etc.)
            
        Example:
            result = await wallet.cancel_order("12345", "BTC/USDT")
            assert result["success"] is True
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Get current status of an order.
        
        Args:
            order_id: Exchange order ID
            symbol: Trading pair
            
        Returns:
            Dict containing:
                - order_id: str
                - status: OrderStatus
                - symbol: str
                - side: OrderSide
                - type: OrderType
                - quantity: Decimal
                - filled_quantity: Decimal
                - remaining_quantity: Decimal
                - average_price: Decimal (if any fills)
                - created_at: datetime
                - updated_at: datetime
                
        Raises:
            OrderNotFoundError: Order does not exist
            
        Example:
            status = await wallet.get_order_status("12345", "BTC/USDT")
            print(status["filled_quantity"])  # 0.05 BTC
        """
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current position for a symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Position dict or None if no position:
                - symbol: str
                - side: "long" or "short"
                - quantity: Decimal
                - entry_price: Decimal
                - current_price: Decimal
                - unrealized_pnl: Decimal
                - leverage: int
                
        Example:
            position = await wallet.get_position("BTC/USDT")
            if position:
                print(f"PnL: ${position['unrealized_pnl']}")
        """
        pass
    
    # ==================== MARKET DATA ====================
    
    @abstractmethod
    async def get_market_price(self, symbol: str) -> Decimal:
        """
        Get current market price for a symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            
        Returns:
            Decimal: Current market price
            
        Raises:
            SymbolNotSupportedError: Symbol not available
            WalletConnectionError: Connection failed
            
        Example:
            price = await wallet.get_market_price("BTC/USDT")
            print(f"BTC Price: ${price}")  # 50000.00
        """
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get 24h ticker data for a symbol.
        
        Returns:
            Dict containing:
                - symbol: str
                - bid: Decimal
                - ask: Decimal
                - last: Decimal
                - high_24h: Decimal
                - low_24h: Decimal
                - volume_24h: Decimal
                - change_24h_percent: Decimal
                - timestamp: datetime
        """
        pass
    
    # ==================== SYMBOL & FORMAT HANDLING ====================
    
    @abstractmethod
    def format_symbol(self, symbol: str) -> str:
        """
        Format symbol to exchange-specific format.
        
        Args:
            symbol: Universal format (e.g., "BTC/USDT")
            
        Returns:
            Exchange-specific format (e.g., "BTCUSDT" for Binance)
            
        Example:
            binance_symbol = wallet.format_symbol("BTC/USDT")
            # Returns: "BTCUSDT"
        """
        pass
    
    @abstractmethod
    def parse_symbol(self, exchange_symbol: str) -> str:
        """
        Parse exchange-specific symbol to universal format.
        
        Args:
            exchange_symbol: Exchange format (e.g., "BTCUSDT")
            
        Returns:
            Universal format (e.g., "BTC/USDT")
            
        Example:
            universal_symbol = wallet.parse_symbol("BTCUSDT")
            # Returns: "BTC/USDT"
        """
        pass
    
    @abstractmethod
    def format_price(self, symbol: str, price: Decimal) -> Decimal:
        """
        Format price to exchange's required precision.
        
        Args:
            symbol: Trading pair
            price: Raw price
            
        Returns:
            Decimal: Rounded to correct precision
            
        Example:
            formatted = wallet.format_price("BTC/USDT", Decimal("50000.123456"))
            # Returns: Decimal("50000.12")  (2 decimal places)
        """
        pass
    
    @abstractmethod
    def format_quantity(self, symbol: str, quantity: Decimal) -> Decimal:
        """
        Format quantity to exchange's required precision.
        
        Args:
            symbol: Trading pair
            quantity: Raw quantity
            
        Returns:
            Decimal: Rounded to correct precision
            
        Example:
            formatted = wallet.format_quantity("BTC/USDT", Decimal("0.123456"))
            # Returns: Decimal("0.123")  (3 decimal places)
        """
        pass
    
    # ==================== CONNECTION & HEALTH ====================
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to wallet/exchange.
        
        Returns:
            Dict containing:
                - success: bool
                - latency_ms: int (ping time)
                - server_time: datetime
                - message: str
                
        Raises:
            WalletConnectionError: Connection failed
            AuthenticationError: Invalid credentials
            
        Example:
            result = await wallet.test_connection()
            if result["success"]:
                print(f"Connected! Latency: {result['latency_ms']}ms")
        """
        pass
    
    @abstractmethod
    async def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get exchange trading rules and limits.
        
        Args:
            symbol: Specific symbol (optional, None = all symbols)
            
        Returns:
            Dict containing:
                - symbols: List of symbol info dicts
                - rate_limits: List of rate limit rules
                - server_time: datetime
                
        Example:
            info = await wallet.get_exchange_info("BTC/USDT")
            min_qty = info["symbols"][0]["min_quantity"]
        """
        pass
    
    # ==================== HISTORICAL DATA ====================
    
    async def get_historical_data(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get historical OHLCV data.
        
        Optional method - not all wallets may support this.
        Default implementation raises NotImplementedError.
        
        Args:
            symbol: Trading pair
            interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles
            
        Returns:
            List of candle dicts:
                - timestamp: datetime
                - open: Decimal
                - high: Decimal
                - low: Decimal
                - close: Decimal
                - volume: Decimal
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support historical data"
        )
    
    async def get_realtime_data(self, symbol: str) -> Dict[str, Any]:
        """
        Subscribe to real-time data stream.
        
        Optional method - most wallets will use WebSocket manager instead.
        Default implementation raises NotImplementedError.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support real-time data streaming. "
            "Use WebSocket manager instead."
        )
    
    # ==================== ACCOUNT INFO ====================
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information.
        
        Optional method - provides extended account details.
        
        Returns:
            Dict containing:
                - account_id: str
                - account_type: str (spot, margin, futures)
                - balances: Dict[str, Decimal]
                - permissions: List[str]
                - fees: Dict (maker/taker fees)
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support get_account_info"
        )
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open orders.
        
        Args:
            symbol: Filter by symbol (optional)
            
        Returns:
            List of order dicts (same format as get_order_status)
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support get_open_orders"
        )
    
    async def get_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get trade history.
        
        Args:
            symbol: Filter by symbol (optional)
            limit: Max number of trades
            
        Returns:
            List of trade dicts:
                - trade_id: str
                - order_id: str
                - symbol: str
                - side: OrderSide
                - price: Decimal
                - quantity: Decimal
                - fee: Decimal
                - fee_currency: str
                - timestamp: datetime
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support get_trade_history"
        )
    
    # ==================== UTILITY METHODS ====================
    
    def __repr__(self) -> str:
        """String representation"""
        return f"<{self.__class__.__name__} wallet_id={self.wallet_id}>"
    
    def get_wallet_type(self) -> str:
        """Get wallet type name"""
        return self.__class__.__name__

