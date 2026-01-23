"""
BinanceWallet - Binance Exchange Integration

Complete Binance API integration with:
- REST API for trading operations
- HMAC-SHA256 authentication
- Rate limit management
- All order types (market, limit, stop-loss, take-profit)
- Balance management
- Symbol validation

Supports both Testnet and Production environments.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import hmac
import hashlib
import time
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import aiohttp

from app.integrations.wallets.base import (
    BaseWallet,
    OrderSide,
    OrderType,
    OrderStatus,
    TimeInForce,
    WalletError,
    WalletConnectionError,
    InsufficientFundsError,
    InvalidOrderError,
    OrderNotFoundError,
    SymbolNotSupportedError,
    RateLimitError,
    AuthenticationError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BinanceWallet(BaseWallet):
    """
    Binance Exchange Integration
    
    Full-featured Binance API client for trading operations.
    
    Features:
    - REST API integration
    - HMAC-SHA256 signed requests
    - Rate limit management
    - All order types
    - Testnet support
    
    Usage:
        wallet = BinanceWallet(
            wallet_id="binance-wallet-001",
            user_wallet_id="user_wallet_123",
            credentials={
                "api_key": "your_api_key",
                "api_secret": "your_api_secret"
            },
            testnet=True  # Use testnet for testing
        )
        
        # Check balance
        balance = await wallet.get_balance("USDT")
        
        # Place order
        result = await wallet.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.001")
        )
    """
    
    # API Endpoints
    BASE_URL_PROD = "https://api.binance.com"
    BASE_URL_TESTNET = "https://testnet.binance.vision"
    
    # Rate limits (requests per minute)
    RATE_LIMIT_ORDERS = 1200  # Order operations
    RATE_LIMIT_RAW = 6100     # Raw requests
    
    def __init__(
        self,
        wallet_id: str,
        user_wallet_id: str,
        credentials: Dict[str, str],
        testnet: bool = False,
        **kwargs
    ):
        """
        Initialize Binance wallet.
        
        Args:
            wallet_id: Wallet provider ID
            user_wallet_id: User wallet instance ID
            credentials: Dict with "api_key" and "api_secret"
            testnet: Use Binance Testnet (default: False)
        """
        super().__init__(wallet_id, user_wallet_id, credentials, **kwargs)
        
        # Configuration
        self.testnet = testnet
        self.base_url = self.BASE_URL_TESTNET if testnet else self.BASE_URL_PROD
        
        # Credentials
        self.api_key = credentials.get("api_key", "")
        self.api_secret = credentials.get("api_secret", "")
        
        if not self.api_key or not self.api_secret:
            raise AuthenticationError(
                "Binance API key and secret are required"
            )
        
        # HTTP session (will be created on demand)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting (simple implementation)
        self._request_timestamps: List[float] = []
        
        # Symbol info cache
        self._symbol_info_cache: Dict[str, Dict] = {}
        
        logger.info(
            f"Initialized BinanceWallet: "
            f"testnet={testnet}, wallet_id={wallet_id}"
        )
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "X-MBX-APIKEY": self.api_key,
                    "Content-Type": "application/json"
                }
            )
        return self.session
    
    async def _close_session(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Generate HMAC SHA256 signature for Binance API.
        
        Args:
            params: Request parameters
            
        Returns:
            Hex signature string
        """
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        signed: bool = False,
        **params
    ) -> Dict[str, Any]:
        """
        Make API request to Binance.
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            signed: Whether request needs signature
            **params: Request parameters
            
        Returns:
            Response JSON
            
        Raises:
            WalletConnectionError: Connection failed
            AuthenticationError: Invalid credentials
            RateLimitError: Rate limit exceeded
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        # Add timestamp for signed requests
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._generate_signature(params)
        
        try:
            # Make request
            if method == "GET":
                async with session.get(url, params=params) as response:
                    return await self._handle_response(response)
            elif method == "POST":
                async with session.post(url, params=params) as response:
                    return await self._handle_response(response)
            elif method == "DELETE":
                async with session.delete(url, params=params) as response:
                    return await self._handle_response(response)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        
        except aiohttp.ClientError as e:
            logger.error(f"Binance API request failed: {str(e)}")
            raise WalletConnectionError(
                f"Failed to connect to Binance: {str(e)}"
            )
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """
        Handle API response and errors.
        
        Args:
            response: HTTP response
            
        Returns:
            Response JSON
            
        Raises:
            AuthenticationError: Invalid API key
            RateLimitError: Rate limit exceeded
            WalletError: Other API errors
        """
        try:
            data = await response.json()
        except Exception:
            data = {"msg": await response.text()}
        
        # Check for errors
        if response.status == 200:
            return data
        
        error_code = data.get("code", response.status)
        error_msg = data.get("msg", "Unknown error")
        
        # Handle specific error codes
        if response.status == 401 or error_code == -2015:
            raise AuthenticationError(
                f"Binance authentication failed: {error_msg}"
            )
        
        if response.status == 429 or error_code == -1003:
            raise RateLimitError(
                f"Binance rate limit exceeded: {error_msg}"
            )
        
        if error_code == -2010:
            raise InsufficientFundsError(
                f"Insufficient balance: {error_msg}"
            )
        
        if error_code == -1121:
            raise InvalidOrderError(
                f"Invalid symbol: {error_msg}"
            )
        
        # LOT_SIZE filter failure - quantity precision issue
        if error_code == -1013:
            raise InvalidOrderError(
                f"LOT_SIZE filter failure: {error_msg}. "
                f"This usually means the quantity precision doesn't match the symbol's stepSize. "
                f"Consider fetching stepSize from /api/v3/exchangeInfo and rounding accordingly."
            )
        
        # Generic error
        logger.error(f"Binance API error: {error_code} - {error_msg}")
        raise WalletError(f"Binance API error: {error_msg}")
    
    # ==================== BALANCE OPERATIONS ====================
    
    async def get_balance(self, asset: str) -> Decimal:
        """Get balance for specific asset"""
        balances = await self.get_all_balances()
        return balances.get(asset, Decimal("0"))
    
    async def get_all_balances(self) -> Dict[str, Decimal]:
        """Get all non-zero balances"""
        try:
            response = await self._request(
                "GET",
                "/api/v3/account",
                signed=True
            )
            
            balances = {}
            for balance in response.get("balances", []):
                asset = balance["asset"]
                free = Decimal(balance["free"])
                
                if free > 0:
                    balances[asset] = free
            
            return balances
        
        except Exception as e:
            logger.error(f"Failed to get balances: {str(e)}")
            raise
    
    # ==================== ORDER OPERATIONS ====================
    
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
        """Place order on Binance"""
        # Format symbol
        binance_symbol = self.format_symbol(symbol)
        
        # Build order parameters
        params = {
            "symbol": binance_symbol,
            "side": side.value.upper(),
            "quantity": str(quantity)
        }
        
        # Map order type
        if order_type == OrderType.MARKET:
            params["type"] = "MARKET"
        elif order_type == OrderType.LIMIT:
            if price is None:
                raise InvalidOrderError("Limit orders require a price")
            params["type"] = "LIMIT"
            params["price"] = str(price)
            params["timeInForce"] = time_in_force.value
        elif order_type == OrderType.STOP_LOSS:
            if stop_price is None:
                raise InvalidOrderError("Stop loss orders require a stop price")
            params["type"] = "STOP_LOSS_LIMIT"
            params["stopPrice"] = str(stop_price)
            params["price"] = str(price or stop_price)
            params["timeInForce"] = time_in_force.value
        elif order_type == OrderType.TAKE_PROFIT:
            if stop_price is None:
                raise InvalidOrderError("Take profit orders require a stop price")
            params["type"] = "TAKE_PROFIT_LIMIT"
            params["stopPrice"] = str(stop_price)
            params["price"] = str(price or stop_price)
            params["timeInForce"] = time_in_force.value
        else:
            raise InvalidOrderError(f"Unsupported order type: {order_type}")
        
        try:
            response = await self._request(
                "POST",
                "/api/v3/order",
                signed=True,
                **params
            )
            
            # Parse response
            return {
                "success": True,
                "order_id": str(response["orderId"]),
                "client_order_id": response.get("clientOrderId", ""),
                "status": self._map_order_status(response["status"]),
                "filled_quantity": Decimal(response.get("executedQty", "0")),
                "average_price": self._calculate_average_price(response) if response.get("fills") else None,
                "timestamp": datetime.fromtimestamp(
                    response["transactTime"] / 1000,
                    tz=timezone.utc
                )
            }
        
        except Exception as e:
            logger.error(f"Failed to place order: {str(e)}")
            raise
    
    def _map_order_status(self, binance_status: str) -> OrderStatus:
        """Map Binance order status to our enum"""
        status_map = {
            "NEW": OrderStatus.OPEN,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "PENDING_CANCEL": OrderStatus.CANCELLING,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.EXPIRED
        }
        return status_map.get(binance_status, OrderStatus.OPEN)
    
    def _calculate_average_price(self, order_response: Dict) -> Optional[Decimal]:
        """Calculate weighted average fill price"""
        fills = order_response.get("fills", [])
        if not fills:
            return None
        
        total_qty = Decimal("0")
        total_value = Decimal("0")
        
        for fill in fills:
            qty = Decimal(fill["qty"])
            price = Decimal(fill["price"])
            total_qty += qty
            total_value += qty * price
        
        if total_qty == 0:
            return None
        
        return total_value / total_qty
    
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel open order"""
        binance_symbol = self.format_symbol(symbol)
        
        try:
            response = await self._request(
                "DELETE",
                "/api/v3/order",
                signed=True,
                symbol=binance_symbol,
                orderId=order_id
            )
            
            return {
                "success": True,
                "order_id": str(response["orderId"]),
                "status": OrderStatus.CANCELLED,
                "message": "Order cancelled successfully"
            }
        
        except Exception as e:
            if "Unknown order" in str(e):
                raise OrderNotFoundError(f"Order {order_id} not found")
            logger.error(f"Failed to cancel order: {str(e)}")
            raise
    
    async def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order status"""
        binance_symbol = self.format_symbol(symbol)
        
        try:
            response = await self._request(
                "GET",
                "/api/v3/order",
                signed=True,
                symbol=binance_symbol,
                orderId=order_id
            )
            
            return {
                "order_id": str(response["orderId"]),
                "status": self._map_order_status(response["status"]),
                "symbol": symbol,
                "side": OrderSide(response["side"].lower()),
                "type": OrderType(response["type"].lower().replace("_", "-")),
                "quantity": Decimal(response["origQty"]),
                "filled_quantity": Decimal(response["executedQty"]),
                "remaining_quantity": Decimal(response["origQty"]) - Decimal(response["executedQty"]),
                "average_price": Decimal(response["price"]) if response.get("price") != "0.00000000" else None,
                "created_at": datetime.fromtimestamp(
                    response["time"] / 1000,
                    tz=timezone.utc
                ),
                "updated_at": datetime.fromtimestamp(
                    response["updateTime"] / 1000,
                    tz=timezone.utc
                )
            }
        
        except Exception as e:
            if "Unknown order" in str(e):
                raise OrderNotFoundError(f"Order {order_id} not found")
            logger.error(f"Failed to get order status: {str(e)}")
            raise
    
    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position (Binance spot doesn't have positions).
        Returns None for spot trading.
        """
        return None
    
    # ==================== MARKET DATA ====================
    
    async def get_market_price(self, symbol: str) -> Decimal:
        """Get current market price"""
        binance_symbol = self.format_symbol(symbol)
        
        try:
            response = await self._request(
                "GET",
                "/api/v3/ticker/price",
                symbol=binance_symbol
            )
            
            return Decimal(response["price"])
        
        except Exception as e:
            logger.error(f"Failed to get market price: {str(e)}")
            raise SymbolNotSupportedError(
                f"Failed to get price for {symbol}: {str(e)}"
            )
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get 24h ticker data"""
        binance_symbol = self.format_symbol(symbol)
        
        try:
            response = await self._request(
                "GET",
                "/api/v3/ticker/24hr",
                symbol=binance_symbol
            )
            
            return {
                "symbol": symbol,
                "bid": Decimal(response["bidPrice"]),
                "ask": Decimal(response["askPrice"]),
                "last": Decimal(response["lastPrice"]),
                "high_24h": Decimal(response["highPrice"]),
                "low_24h": Decimal(response["lowPrice"]),
                "volume_24h": Decimal(response["volume"]),
                "change_24h_percent": Decimal(response["priceChangePercent"]),
                "timestamp": datetime.now(timezone.utc)
            }
        
        except Exception as e:
            logger.error(f"Failed to get ticker: {str(e)}")
            raise
    
    # ==================== SYMBOL FORMATTING ====================
    
    def format_symbol(self, symbol: str) -> str:
        """
        Convert universal format to Binance format.
        BTC/USDT → BTCUSDT
        """
        return symbol.replace("/", "")
    
    def parse_symbol(self, exchange_symbol: str) -> str:
        """
        Convert Binance format to universal format.
        BTCUSDT → BTC/USDT
        
        Note: This is tricky as Binance doesn't use separators.
        We assume most symbols end with USDT, BUSD, or BTC.
        """
        for quote in ["USDT", "BUSD", "BTC", "ETH", "BNB"]:
            if exchange_symbol.endswith(quote):
                base = exchange_symbol[:-len(quote)]
                return f"{base}/{quote}"
        
        # Fallback: can't parse
        return exchange_symbol
    
    def format_price(self, symbol: str, price: Decimal) -> Decimal:
        """Format price to exchange precision"""
        # TODO: Get actual precision from symbol info
        # For now, use 2 decimals for most pairs
        return price.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    
    def format_quantity(self, symbol: str, quantity: Decimal) -> Decimal:
        """
        Format quantity to exchange precision using floor rounding.
        
        Currently uses 8 decimal places (safe for BTC, ETH, and most major pairs).
        
        Future Enhancement:
        - Some coins (e.g., SHIB, low-sats pairs) have specific LOT_SIZE requirements
        - If you encounter APIError(code=-1013): Filter failure: LOT_SIZE, implement:
          1. Fetch stepSize from /api/v3/exchangeInfo endpoint
          2. Parse LOT_SIZE filter: filters[filterType="LOT_SIZE"]["stepSize"]
          3. Round quantity: (quantity // stepSize) * stepSize
          4. Cache symbol info in self._symbol_info_cache for performance
        
        Example future implementation:
            if symbol not in self._symbol_info_cache:
                info = await self.get_exchange_info(symbol)
                lot_size = info["symbols"][0]["filters"]["LOT_SIZE"]["stepSize"]
                self._symbol_info_cache[symbol] = {"stepSize": Decimal(lot_size)}
            
            step_size = self._symbol_info_cache[symbol]["stepSize"]
            return (quantity // step_size) * step_size
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            quantity: Quantity to format
            
        Returns:
            Decimal: Floor-rounded quantity (8 decimal precision)
        """
        # For now, use 8 decimals (crypto standard) - safe for BTC, ETH, and most pairs
        # TODO: Fetch actual stepSize from exchangeInfo for coins with special LOT_SIZE requirements
        return quantity.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    
    # ==================== CONNECTION & INFO ====================
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Binance"""
        try:
            start_time = time.time()
            
            # Test ping
            await self._request("GET", "/api/v3/ping")
            
            # Test authenticated endpoint
            await self._request("GET", "/api/v3/account", signed=True)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                "success": True,
                "latency_ms": latency_ms,
                "server_time": datetime.now(timezone.utc),
                "message": f"Connected to Binance ({'Testnet' if self.testnet else 'Production'})"
            }
        
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            raise
    
    async def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get exchange trading rules"""
        try:
            params = {}
            if symbol:
                params["symbol"] = self.format_symbol(symbol)
            
            response = await self._request(
                "GET",
                "/api/v3/exchangeInfo",
                **params
            )
            
            return {
                "symbols": response.get("symbols", []),
                "rate_limits": response.get("rateLimits", []),
                "server_time": datetime.fromtimestamp(
                    response["serverTime"] / 1000,
                    tz=timezone.utc
                )
            }
        
        except Exception as e:
            logger.error(f"Failed to get exchange info: {str(e)}")
            raise
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()

