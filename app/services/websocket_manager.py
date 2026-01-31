"""
WebSocket Connection Manager

Centralized manager for all WebSocket connections:
- Polygon.io market data
- Binance user data streams (future)
- Health monitoring
- Auto-reconnection
- Message routing to handlers
- Graceful shutdown

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import asyncio
from typing import Dict, Optional, Callable, List
from datetime import datetime, timezone
from collections import defaultdict

from app.infrastructure.market_data.polygon_client import (
    PolygonWebSocketClient,
    AssetClass,
    parse_crypto_trade,
    parse_crypto_quote,
    parse_crypto_aggregate
)
from app.utils.logger import get_logger
from app.utils.cache import get_redis_client

logger = get_logger(__name__)


class WebSocketManager:
    """
    Centralized WebSocket connection manager.
    
    Singleton pattern - one instance per application.
    
    Features:
    - Manages Polygon.io WebSocket connection
    - Routes messages to registered handlers
    - Caches prices in Redis
    - Health monitoring & statistics
    - Graceful startup/shutdown
    
    Usage:
        manager = WebSocketManager()
        
        # Start all connections
        await manager.start(polygon_api_key="your_key")
        
        # Subscribe to symbols
        await manager.subscribe_market_data(["BTC/USDT", "ETH/USDT"])
        
        # Register custom handler
        manager.add_market_data_handler(my_handler)
        
        # Stop all connections
        await manager.stop()
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize manager"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        
        # Polygon.io client
        self.polygon_client: Optional[PolygonWebSocketClient] = None
        self.polygon_task: Optional[asyncio.Task] = None
        
        # Binance user streams (per wallet) - future
        self.binance_streams: Dict[str, asyncio.Task] = {}
        
        # Message handlers
        self.market_data_handlers: List[Callable] = []
        self.order_update_handlers: List[Callable] = []
        
        # State
        self.is_running = False
        
        # Redis for price caching
        self.redis = None
        
        # Statistics
        self.stats = {
            "messages_received": 0,
            "trades_processed": 0,
            "quotes_processed": 0,
            "aggregates_processed": 0,
            "errors": 0,
            "last_message_time": None
        }
        
        logger.info("WebSocket manager initialized")
    
    async def start(self, polygon_api_key: str):
        """
        Start all WebSocket connections.
        
        Args:
            polygon_api_key: Polygon.io API key
            
        Example:
            manager = WebSocketManager()
            await manager.start(polygon_api_key="your_key")
        """
        if self.is_running:
            logger.warning("WebSocket manager already running")
            return
        
        logger.info("Starting WebSocket manager...")
        
        # Get Redis connection
        try:
            self.redis = await get_redis_client()
            logger.info("Redis client connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {str(e)}. Price caching disabled.")
            self.redis = None
        
        # Initialize Polygon.io client
        self.polygon_client = PolygonWebSocketClient(
            api_key=polygon_api_key,
            asset_class=AssetClass.CRYPTO
        )
        
        # Set message handler
        self.polygon_client.set_message_handler(self._handle_polygon_message)
        
        # Connect
        await self.polygon_client.connect()
        
        # Start message loop in background
        self.polygon_task = asyncio.create_task(self.polygon_client.run())
        
        self.is_running = True
        logger.info("✅ WebSocket manager started successfully")
    
    async def stop(self):
        """Stop all WebSocket connections"""
        if not self.is_running:
            return
        
        logger.info("Stopping WebSocket manager...")
        
        # Stop Polygon.io
        if self.polygon_client:
            await self.polygon_client.close()
        
        if self.polygon_task:
            self.polygon_task.cancel()
            try:
                await self.polygon_task
            except asyncio.CancelledError:
                pass
        
        # Stop Binance streams
        for task in self.binance_streams.values():
            task.cancel()
        
        self.is_running = False
        logger.info("WebSocket manager stopped")
    
    async def subscribe_market_data(
        self,
        symbols: List[str],
        data_types: Optional[List[str]] = None
    ):
        """
        Subscribe to market data for symbols.
        
        Args:
            symbols: List of symbols (e.g., ["BTC/USDT", "ETH/USDT"])
            data_types: ["trades", "quotes", "aggregates"] (default: all)
            
        Example:
            await manager.subscribe_market_data(
                symbols=["BTC/USDT", "ETH/USDT"],
                data_types=["trades", "quotes"]
            )
        """
        if not self.polygon_client:
            raise RuntimeError("WebSocket manager not started")
        
        data_types = data_types or ["trades", "quotes", "aggregates"]
        
        # Convert symbol format (BTC/USDT -> BTC-USD)
        polygon_symbols = [self._convert_symbol_format(s) for s in symbols]
        
        # Subscribe to requested data types
        if "trades" in data_types:
            await self.polygon_client.subscribe_crypto_trades(polygon_symbols)
        
        if "quotes" in data_types:
            await self.polygon_client.subscribe_crypto_quotes(polygon_symbols)
        
        if "aggregates" in data_types:
            await self.polygon_client.subscribe_crypto_aggregates(
                polygon_symbols,
                interval="minute"
            )
        
        logger.info(f"Subscribed to market data for {len(symbols)} symbols")
    
    def _convert_symbol_format(self, symbol: str) -> str:
        """
        Convert universal format to Polygon format.
        BTC/USDT -> BTC-USD
        """
        # Replace /USDT with -USD (Polygon uses USD not USDT for crypto)
        return symbol.replace("/USDT", "-USD").replace("/", "-")
    
    def add_market_data_handler(self, handler: Callable):
        """
        Add handler for market data messages.
        
        Handler signature: async def handler(data: Dict)
        
        Example:
            async def my_handler(data: Dict):
                if data["type"] == "trade":
                    print(f"Trade: {data['symbol']} @ {data['price']}")
            
            manager.add_market_data_handler(my_handler)
        """
        self.market_data_handlers.append(handler)
        logger.info(f"Added market data handler: {handler.__name__}")
    
    def add_order_update_handler(self, handler: Callable):
        """
        Add handler for order update messages.
        
        Handler signature: async def handler(data: Dict)
        """
        self.order_update_handlers.append(handler)
        logger.info(f"Added order update handler: {handler.__name__}")
    
    async def _handle_polygon_message(self, message: Dict):
        """
        Handle message from Polygon.io.
        
        Routes to appropriate parser and handlers.
        """
        try:
            ev = message.get("ev")
            
            # Parse message based on type
            parsed_data = None
            
            if ev == "XT":  # Crypto trade
                parsed_data = parse_crypto_trade(message)
                self.stats["trades_processed"] += 1
                
                # Cache latest price in Redis
                await self._cache_price(
                    parsed_data["symbol"],
                    float(parsed_data["price"])
                )
            
            elif ev == "XQ":  # Crypto quote
                parsed_data = parse_crypto_quote(message)
                self.stats["quotes_processed"] += 1
                
                # Cache latest bid/ask
                await self._cache_quote(
                    parsed_data["symbol"],
                    float(parsed_data["bid_price"]),
                    float(parsed_data["ask_price"])
                )
            
            elif ev in ["XA", "XAS"]:  # Crypto aggregate
                parsed_data = parse_crypto_aggregate(message)
                self.stats["aggregates_processed"] += 1
            
            # Update stats
            self.stats["messages_received"] += 1
            self.stats["last_message_time"] = datetime.now(timezone.utc)
            
            # Call handlers
            if parsed_data:
                for handler in self.market_data_handlers:
                    try:
                        await handler(parsed_data)
                    except Exception as e:
                        logger.error(f"Error in market data handler: {str(e)}")
                        self.stats["errors"] += 1
        
        except Exception as e:
            logger.error(f"Error handling Polygon message: {str(e)}")
            self.stats["errors"] += 1
    
    async def _cache_price(self, symbol: str, price: float):
        """
        Cache latest price in Redis.
        
        Args:
            symbol: Symbol (e.g., "BTC-USD")
            price: Latest price
        """
        if not self.redis:
            return
        
        try:
            # Convert back to universal format (BTC-USD -> BTC/USDT)
            universal_symbol = symbol.replace("-USD", "/USDT")
            
            key = f"price:{universal_symbol}"
            await self.redis.set(key, str(price), ex=60)  # Expire in 60s
            
            logger.debug(f"Cached price: {universal_symbol} = {price}")
        
        except Exception as e:
            logger.error(f"Failed to cache price: {str(e)}")
    
    async def _cache_quote(self, symbol: str, bid: float, ask: float):
        """
        Cache latest quote in Redis.
        
        Args:
            symbol: Symbol
            bid: Bid price
            ask: Ask price
        """
        if not self.redis:
            return
        
        try:
            # Convert to universal format
            universal_symbol = symbol.replace("-USD", "/USDT")
            
            mid = (bid + ask) / 2
            spread = ask - bid
            
            await self.redis.hset(
                f"quote:{universal_symbol}",
                mapping={
                    "bid": str(bid),
                    "ask": str(ask),
                    "mid": str(mid),
                    "spread": str(spread),
                    "timestamp": str(int(datetime.now(timezone.utc).timestamp()))
                }
            )
            await self.redis.expire(f"quote:{universal_symbol}", 60)
            
            logger.debug(f"Cached quote: {universal_symbol} bid={bid} ask={ask}")
        
        except Exception as e:
            logger.error(f"Failed to cache quote: {str(e)}")
    
    async def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get latest price from cache.
        
        Args:
            symbol: Symbol in universal format (e.g., "BTC/USDT")
            
        Returns:
            Latest price or None
        """
        if not self.redis:
            return None
        
        try:
            price_str = await self.redis.get(f"price:{symbol}")
            if price_str:
                return float(price_str)
        except Exception as e:
            logger.error(f"Failed to get cached price: {str(e)}")
        
        return None
    
    async def get_latest_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get latest quote from cache.
        
        Args:
            symbol: Symbol in universal format
            
        Returns:
            Quote dict with bid, ask, mid, spread
        """
        if not self.redis:
            return None
        
        try:
            quote = await self.redis.hgetall(f"quote:{symbol}")
            if quote:
                return {
                    "bid": float(quote.get("bid", 0)),
                    "ask": float(quote.get("ask", 0)),
                    "mid": float(quote.get("mid", 0)),
                    "spread": float(quote.get("spread", 0)),
                    "timestamp": int(quote.get("timestamp", 0))
                }
        except Exception as e:
            logger.error(f"Failed to get cached quote: {str(e)}")
        
        return None
    
    def get_stats(self) -> Dict:
        """
        Get manager statistics.
        
        Returns:
            Dict with stats
        """
        return {
            **self.stats,
            "is_running": self.is_running,
            "polygon_connected": self.polygon_client.is_connected if self.polygon_client else False,
            "polygon_authenticated": self.polygon_client.is_authenticated if self.polygon_client else False,
            "subscriptions": len(self.polygon_client.subscriptions) if self.polygon_client else 0
        }


# Global singleton instance
_ws_manager = None


def get_websocket_manager() -> WebSocketManager:
    """
    Get global WebSocket manager instance.
    
    Returns:
        Shared WebSocketManager instance
        
    Example:
        from app.infrastructure.market_data.websocket_manager import get_websocket_manager
        
        manager = get_websocket_manager()
        await manager.start(polygon_api_key="your_key")
    """
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager

