"""
HyperliquidWallet - Hyperliquid Perpetual Futures Integration

Complete Hyperliquid API integration with:
- Perpetual futures trading (no spot)
- Leverage support (1-20x)
- Private key authentication
- Position-based trading
- On-chain transparency

Author: Moniqo Team
Last Updated: 2026-01-28
"""

import re
import time
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import aiohttp

from app.infrastructure.exchanges.base import (
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
from app.core.config import get_settings

logger = get_logger(__name__)


class HyperliquidWallet(BaseWallet):
    """
    Hyperliquid Perpetual Futures Integration
    
    Full-featured Hyperliquid API client for perpetual futures trading.
    
    Features:
    - Perpetual futures trading (no spot)
    - Leverage support (1-20x)
    - Private key authentication
    - Position-based trading
    - On-chain transparency
    
    Usage:
        wallet = HyperliquidWallet(
            wallet_id="hyperliquid-wallet-001",
            user_wallet_id="user_wallet_123",
            credentials={
                "private_key": "0x...",
                "wallet_address": "0x..."
            }
        )
        
        # Check balance
        balance = await wallet.get_balance("USDC")
        
        # Place leveraged order
        result = await wallet.place_order(
            symbol="BTC",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
            leverage=10  # 10x leverage
        )
    """
    
    # API Configuration
    BASE_URL = "https://api.hyperliquid.xyz"
    
    # Leverage limits
    MIN_LEVERAGE = 1
    MAX_LEVERAGE = 20
    
    def __init__(
        self,
        wallet_id: str,
        user_wallet_id: str,
        credentials: Dict[str, str],
        **kwargs
    ):
        """
        Initialize Hyperliquid wallet.
        
        Args:
            wallet_id: Wallet provider ID
            user_wallet_id: User wallet instance ID
            credentials: Dict with "private_key" and "wallet_address"
        """
        super().__init__(wallet_id, user_wallet_id, credentials, **kwargs)
        
        # Extract credentials
        self.private_key = credentials.get("private_key", "")
        self.wallet_address = credentials.get("wallet_address", "")
        
        if not self.private_key:
            raise AuthenticationError(
                "Hyperliquid private_key is required"
            )
        
        if not self.wallet_address:
            raise AuthenticationError(
                "Hyperliquid wallet_address is required"
            )
        
        # Validate private key format (0x... hex string, 66 chars)
        if not self._validate_private_key(self.private_key):
            raise AuthenticationError(
                "Invalid private key format. Must be 0x-prefixed hex string (66 characters)"
            )
        
        # Validate wallet address format (0x... hex string, 42 chars)
        if not self._validate_wallet_address(self.wallet_address):
            raise AuthenticationError(
                "Invalid wallet address format. Must be 0x-prefixed hex string (42 characters)"
            )
        
        # HTTP session (will be created on demand)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Hyperliquid SDK client (lazy initialization)
        self._sdk_client = None
        
        # Symbol info cache
        self._symbol_info_cache: Dict[str, Dict] = {}
        
        logger.info(
            f"Initialized HyperliquidWallet: "
            f"wallet_id={wallet_id}, address={self.wallet_address[:10]}..."
        )
    
    def _validate_private_key(self, private_key: str) -> bool:
        """Validate private key format"""
        if not isinstance(private_key, str):
            return False
        # Must be 0x-prefixed hex string, 66 characters total
        pattern = r'^0x[a-fA-F0-9]{64}$'
        return bool(re.match(pattern, private_key))
    
    def _validate_wallet_address(self, address: str) -> bool:
        """Validate wallet address format"""
        if not isinstance(address, str):
            return False
        # Must be 0x-prefixed hex string, 42 characters total
        pattern = r'^0x[a-fA-F0-9]{40}$'
        return bool(re.match(pattern, address))
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json"
                }
            )
        return self.session
    
    async def _close_session(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _get_sdk_client(self):
        """Get or create Hyperliquid SDK client"""
        if self._sdk_client is None:
            try:
                from hyperliquid.info import Info
                from hyperliquid.utils import constants
                from hyperliquid.utils.signing import SigningHelper
                from hyperliquid.exchange import Exchange
                
                # Determine network
                is_testnet = self.config.get("testnet", False)
                base_url = constants.TESTNET_API_URL if is_testnet else constants.MAINNET_API_URL
                
                # Initialize SDK components
                self._info_client = Info(base_url, skip_ws=True)
                self._signing_helper = SigningHelper(
                    self.private_key,
                    constants.TESTNET if is_testnet else constants.MAINNET
                )
                self._exchange_client = Exchange(
                    self._signing_helper,
                    base_url=base_url
                )
                self._sdk_client = {
                    "info": self._info_client,
                    "exchange": self._exchange_client,
                    "signing": self._signing_helper
                }
            except ImportError:
                raise WalletError(
                    "hyperliquid-python-sdk not installed. "
                    "Install with: pip install hyperliquid-python-sdk"
                )
            except Exception as e:
                raise WalletConnectionError(
                    f"Failed to initialize Hyperliquid SDK: {str(e)}"
                )
        
        return self._sdk_client
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **params
    ) -> Dict[str, Any]:
        """
        Make API request to Hyperliquid.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            **params: Request parameters
            
        Returns:
            Response JSON
            
        Raises:
            WalletConnectionError: Connection failed
            RateLimitError: Rate limit exceeded
        """
        session = await self._get_session()
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            if method == "GET":
                async with session.get(url, params=params) as response:
                    return await self._handle_response(response)
            elif method == "POST":
                async with session.post(url, json=params) as response:
                    return await self._handle_response(response)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        
        except aiohttp.ClientError as e:
            logger.error(f"Hyperliquid API request failed: {str(e)}")
            raise WalletConnectionError(
                f"Failed to connect to Hyperliquid: {str(e)}"
            )
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """
        Handle API response and errors.
        
        Args:
            response: HTTP response
            
        Returns:
            Response JSON
            
        Raises:
            AuthenticationError: Invalid credentials
            RateLimitError: Rate limit exceeded
            WalletError: Other API errors
        """
        try:
            data = await response.json()
        except Exception:
            data = {"error": await response.text()}
        
        # Check for errors
        if response.status == 200:
            return data
        
        error_msg = data.get("error", data.get("msg", "Unknown error"))
        
        # Handle specific error codes
        if response.status == 401:
            raise AuthenticationError(
                f"Hyperliquid authentication failed: {error_msg}"
            )
        
        if response.status == 429:
            raise RateLimitError(
                f"Hyperliquid rate limit exceeded: {error_msg}"
            )
        
        # Generic error
        logger.error(f"Hyperliquid API error: {response.status} - {error_msg}")
        raise WalletError(f"Hyperliquid API error: {error_msg}")
    
    # ==================== BALANCE OPERATIONS ====================
    
    async def get_balance(self, asset: str) -> Decimal:
        """Get balance for specific asset"""
        balances = await self.get_all_balances()
        return balances.get(asset, Decimal("0"))
    
    async def get_all_balances(self) -> Dict[str, Decimal]:
        """Get all non-zero balances"""
        try:
            sdk = self._get_sdk_client()
            info = sdk["info"]
            
            # Get user state (includes balances)
            user_state = info.user_state(self.wallet_address)
            
            if not user_state or "marginSummary" not in user_state:
                return {}
            
            balances = {}
            margin_summary = user_state.get("marginSummary", {})
            
            # Extract balances from margin summary
            # Hyperliquid uses USDC as collateral
            if "accountValue" in margin_summary:
                account_value = Decimal(str(margin_summary["accountValue"]))
                if account_value > 0:
                    balances["USDC"] = account_value
            
            # Also check for withdrawable balance (more accurate for available funds)
            if "withdrawable" in margin_summary:
                withdrawable = Decimal(str(margin_summary["withdrawable"]))
                if withdrawable > 0:
                    # Use withdrawable as it represents available balance
                    balances["USDC"] = withdrawable
            
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
        """
        Place order on Hyperliquid perpetual futures.
        
        Args:
            symbol: Trading pair (e.g., "BTC" - no /USDT suffix)
            side: BUY or SELL
            order_type: MARKET or LIMIT
            quantity: Order quantity (base asset)
            price: Limit price (required for limit orders)
            stop_price: Stop trigger price (for stop orders)
            time_in_force: Order time in force
            **kwargs: Additional parameters including leverage
        
        Returns:
            Order result dict
        """
        # Format symbol (remove /USDT if present)
        hyperliquid_symbol = self.format_symbol(symbol)
        
        # Extract leverage from kwargs (default 1x)
        leverage = kwargs.get("leverage", 1)
        leverage = max(self.MIN_LEVERAGE, min(int(leverage), self.MAX_LEVERAGE))
        
        # Validate order type
        if order_type not in [OrderType.MARKET, OrderType.LIMIT]:
            raise InvalidOrderError(
                f"Hyperliquid only supports MARKET and LIMIT orders. "
                f"Got: {order_type}"
            )
        
        # Validate limit orders have price
        if order_type == OrderType.LIMIT and price is None:
            raise InvalidOrderError("Limit orders require a price")
        
        try:
            sdk = self._get_sdk_client()
            exchange = sdk["exchange"]
            info = sdk["info"]
            
            # Determine order side
            is_buy = side == OrderSide.BUY
            
            # Set leverage first (required before placing orders)
            # update_leverage(leverage, coin, is_cross)
            leverage_result = exchange.update_leverage(leverage, hyperliquid_symbol, False)
            if leverage_result.get("status") != "ok":
                logger.warning(f"Failed to set leverage to {leverage}x: {leverage_result}")
            
            # Place order based on type
            if order_type == OrderType.MARKET:
                # Market order with 1% slippage tolerance
                # market_open(coin, is_buy, sz, px, slippage)
                slippage = 0.01
                result = exchange.market_open(hyperliquid_symbol, is_buy, float(quantity), None, slippage)
            else:
                # Limit order
                # order(coin, is_buy, sz, limit_px, order_type)
                result = exchange.order(
                    hyperliquid_symbol,
                    is_buy,
                    float(quantity),
                    float(price),
                    {"limit": {"tif": "Gtc"}}
                )
            
            # Parse response
            if result.get("status") == "ok":
                statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                order_id = None
                client_order_id = None
                filled_quantity = Decimal("0")
                average_price = float(price) if price else None
                
                if statuses:
                    status = statuses[0]
                    if "resting" in status:
                        # Limit order - resting on orderbook
                        order_id = status["resting"].get("oid")
                        client_order_id = status["resting"].get("cloid")
                    elif "filled" in status:
                        # Market order - filled immediately
                        filled_data = status["filled"]
                        order_id = filled_data.get("oid", f"HL-{int(time.time() * 1000)}")
                        filled_quantity = Decimal(str(filled_data.get("totalSz", 0)))
                        average_price = float(filled_data.get("avgPx", 0)) if filled_data.get("avgPx") else None
                    elif "error" in status:
                        error_msg = status["error"]
                        raise InvalidOrderError(f"Order placement failed: {error_msg}")
                
                if not order_id:
                    order_id = f"HL-{int(time.time() * 1000)}"
                
                return {
                    "success": True,
                    "order_id": str(order_id),
                    "client_order_id": str(client_order_id) if client_order_id else None,
                    "status": OrderStatus.FILLED if order_type == OrderType.MARKET or filled_quantity > 0 else OrderStatus.OPEN,
                    "filled_quantity": filled_quantity if filled_quantity > 0 else (quantity if order_type == OrderType.MARKET else Decimal("0")),
                    "average_price": average_price,
                    "timestamp": datetime.now(timezone.utc),
                    "leverage": leverage,
                }
            else:
                error_msg = "Unknown error"
                statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                if statuses and "error" in statuses[0]:
                    error_msg = statuses[0]["error"]
                raise InvalidOrderError(f"Order placement failed: {error_msg}")
        
        except Exception as e:
            logger.error(f"Failed to place order: {str(e)}")
            if "insufficient" in str(e).lower() or "balance" in str(e).lower():
                raise InsufficientFundsError(str(e))
            raise
    
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel open order"""
        hyperliquid_symbol = self.format_symbol(symbol)
        
        try:
            sdk = self._get_sdk_client()
            exchange = sdk["exchange"]
            
            # Cancel order via SDK
            result = exchange.cancel(hyperliquid_symbol, order_id)
            
            if result.get("status") == "ok":
                return {
                    "success": True,
                    "order_id": order_id,
                    "status": OrderStatus.CANCELLED,
                    "message": "Order cancelled successfully"
                }
            else:
                error_msg = "Unknown error"
                statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                if statuses and "error" in statuses[0]:
                    error_msg = statuses[0]["error"]
                raise OrderNotFoundError(f"Order cancellation failed: {error_msg}")
        
        except Exception as e:
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                raise OrderNotFoundError(f"Order {order_id} not found")
            logger.error(f"Failed to cancel order: {str(e)}")
            raise
    
    async def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order status"""
        try:
            sdk = self._get_sdk_client()
            info = sdk["info"]
            
            # Get open orders for user
            open_orders = info.open_orders(self.wallet_address)
            
            # Find order by ID
            order = None
            for o in open_orders:
                if str(o.get("oid")) == str(order_id):
                    order = o
                    break
            
            if not order:
                raise OrderNotFoundError(f"Order {order_id} not found")
            
            # Parse order data
            return {
                "order_id": str(order.get("oid", order_id)),
                "status": OrderStatus.OPEN if order.get("status") == "open" else OrderStatus.FILLED,
                "symbol": self.parse_symbol(order.get("coin", symbol)),
                "side": OrderSide.BUY if order.get("side") == "A" else OrderSide.SELL,
                "type": OrderType.LIMIT if order.get("limitPx") else OrderType.MARKET,
                "quantity": Decimal(str(order.get("sz", 0))),
                "filled_quantity": Decimal("0"),  # Hyperliquid doesn't provide this directly
                "remaining_quantity": Decimal(str(order.get("sz", 0))),
                "average_price": Decimal(str(order.get("limitPx", 0))) if order.get("limitPx") else None,
                "created_at": datetime.now(timezone.utc),  # Hyperliquid doesn't provide timestamp
                "updated_at": datetime.now(timezone.utc),
            }
        
        except OrderNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get order status: {str(e)}")
            raise
    
    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current position for a symbol.
        
        Hyperliquid tracks positions (not orders), so this returns actual position data.
        """
        try:
            sdk = self._get_sdk_client()
            info = sdk["info"]
            
            # Get user state
            user_state = info.user_state(self.wallet_address)
            
            if not user_state or "assetPositions" not in user_state:
                return None
            
            hyperliquid_symbol = self.format_symbol(symbol)
            
            # Find position for symbol
            for pos in user_state.get("assetPositions", []):
                if pos.get("position", {}).get("coin") == hyperliquid_symbol:
                    position_data = pos.get("position", {})
                    
                    # Parse position
                    size = Decimal(str(position_data.get("szi", 0)))
                    if size == 0:
                        return None
                    
                    entry_price = Decimal(str(position_data.get("entryPx", 0)))
                    leverage = int(position_data.get("leverage", 1))
                    
                    # Get current price
                    current_price = await self.get_market_price(symbol)
                    
                    # Calculate unrealized P&L
                    is_long = size > 0
                    if is_long:
                        unrealized_pnl = (current_price - entry_price) * abs(size) * leverage
                    else:
                        unrealized_pnl = (entry_price - current_price) * abs(size) * leverage
                    
                    return {
                        "symbol": symbol,
                        "side": "long" if is_long else "short",
                        "quantity": abs(size),
                        "entry_price": entry_price,
                        "current_price": current_price,
                        "unrealized_pnl": unrealized_pnl,
                        "leverage": leverage,
                    }
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get position: {str(e)}")
            raise
    
    # ==================== MARKET DATA ====================
    
    async def get_market_price(self, symbol: str) -> Decimal:
        """Get current market price"""
        hyperliquid_symbol = self.format_symbol(symbol)
        
        try:
            sdk = self._get_sdk_client()
            info = sdk["info"]
            
            # Get market data
            meta = info.meta()
            
            # Find symbol in universe
            for coin_info in meta.get("universe", []):
                if coin_info.get("name") == hyperliquid_symbol:
                    # Get latest price from orderbook
                    orderbook = info.l2_snapshot(hyperliquid_symbol)
                    if orderbook and "levels" in orderbook:
                        # Use mid price (average of best bid/ask)
                        bids = orderbook["levels"][0] if orderbook["levels"] else []
                        asks = orderbook["levels"][1] if len(orderbook["levels"]) > 1 else []
                        
                        if bids and asks:
                            best_bid = Decimal(str(bids[0][0]))
                            best_ask = Decimal(str(asks[0][0]))
                            mid_price = (best_bid + best_ask) / 2
                            return mid_price
                    
                    # Fallback: use mark price from meta
                    mark_px = coin_info.get("markPx")
                    if mark_px:
                        return Decimal(str(mark_px))
            
            raise SymbolNotSupportedError(
                f"Symbol {symbol} not found on Hyperliquid"
            )
        
        except SymbolNotSupportedError:
            raise
        except Exception as e:
            logger.error(f"Failed to get market price: {str(e)}")
            raise SymbolNotSupportedError(
                f"Failed to get price for {symbol}: {str(e)}"
            )
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get 24h ticker data"""
        hyperliquid_symbol = self.format_symbol(symbol)
        
        try:
            sdk = self._get_sdk_client()
            info = sdk["info"]
            
            # Get market data
            meta = info.meta()
            
            # Find symbol in universe
            coin_info = None
            for coin in meta.get("universe", []):
                if coin.get("name") == hyperliquid_symbol:
                    coin_info = coin
                    break
            
            if not coin_info:
                raise SymbolNotSupportedError(f"Symbol {symbol} not found")
            
            # Get orderbook for bid/ask
            orderbook = info.l2_snapshot(hyperliquid_symbol)
            best_bid = Decimal("0")
            best_ask = Decimal("0")
            
            if orderbook and "levels" in orderbook:
                bids = orderbook["levels"][0] if orderbook["levels"] else []
                asks = orderbook["levels"][1] if len(orderbook["levels"]) > 1 else []
                
                if bids:
                    best_bid = Decimal(str(bids[0][0]))
                if asks:
                    best_ask = Decimal(str(asks[0][0]))
            
            # Use mark price as last price
            last_price = Decimal(str(coin_info.get("markPx", 0)))
            
            # Get 24h stats (if available)
            # Note: Hyperliquid doesn't provide 24h stats directly, use mark price
            high_24h = last_price  # Approximation
            low_24h = last_price   # Approximation
            volume_24h = Decimal("0")  # Not available
            change_24h_percent = Decimal("0")  # Not available
            
            return {
                "symbol": symbol,
                "bid": best_bid,
                "ask": best_ask,
                "last": last_price,
                "high_24h": high_24h,
                "low_24h": low_24h,
                "volume_24h": volume_24h,
                "change_24h_percent": change_24h_percent,
                "timestamp": datetime.now(timezone.utc)
            }
        
        except Exception as e:
            logger.error(f"Failed to get ticker: {str(e)}")
            raise
    
    # ==================== SYMBOL FORMATTING ====================
    
    def format_symbol(self, symbol: str) -> str:
        """
        Convert universal format to Hyperliquid format.
        BTC/USDT → BTC
        """
        # Remove /USDT or /USDC suffix
        return symbol.split("/")[0].upper()
    
    def parse_symbol(self, exchange_symbol: str) -> str:
        """
        Convert Hyperliquid format to universal format.
        BTC → BTC/USDT
        """
        # Hyperliquid uses base symbol, assume USDT quote
        return f"{exchange_symbol}/USDT"
    
    def format_price(self, symbol: str, price: Decimal) -> Decimal:
        """Format price to exchange precision"""
        # Hyperliquid typically uses 2-4 decimal places
        # Use 2 decimals for most pairs
        return price.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    
    def format_quantity(self, symbol: str, quantity: Decimal) -> Decimal:
        """Format quantity to exchange precision"""
        # Hyperliquid uses 8 decimal places for most assets
        return quantity.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    
    # ==================== CONNECTION & INFO ====================
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Hyperliquid"""
        try:
            start_time = time.time()
            
            # Test by fetching meta
            sdk = self._get_sdk_client()
            info = sdk["info"]
            meta = info.meta()
            
            if not meta:
                raise WalletConnectionError("Failed to fetch Hyperliquid meta")
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                "success": True,
                "latency_ms": latency_ms,
                "server_time": datetime.now(timezone.utc),
                "message": f"Connected to Hyperliquid (address: {self.wallet_address[:10]}...)"
            }
        
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            raise
    
    async def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get exchange trading rules"""
        try:
            sdk = self._get_sdk_client()
            info = sdk["info"]
            
            meta = info.meta()
            
            symbols = []
            if symbol:
                # Get specific symbol info
                hyperliquid_symbol = self.format_symbol(symbol)
                for coin_info in meta.get("universe", []):
                    if coin_info.get("name") == hyperliquid_symbol:
                        symbols.append({
                            "name": coin_info.get("name"),
                            "maxLeverage": coin_info.get("maxLeverage", 20),
                            "szDecimals": coin_info.get("szDecimals", 8),
                        })
                        break
            else:
                # Get all symbols
                for coin_info in meta.get("universe", []):
                    symbols.append({
                        "name": coin_info.get("name"),
                        "maxLeverage": coin_info.get("maxLeverage", 20),
                        "szDecimals": coin_info.get("szDecimals", 8),
                    })
            
            return {
                "symbols": symbols,
                "rate_limits": [],  # Hyperliquid doesn't publish rate limits
                "server_time": datetime.now(timezone.utc)
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
