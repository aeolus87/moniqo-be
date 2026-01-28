"""
Binance WebSocket Client

FREE real-time market data via Binance WebSocket API.
No API key required for public market data streams.

Supports:
- Spot: wss://stream.binance.com:9443/ws
- Futures: wss://fstream.binance.com/ws

Author: Moniqo Team
"""

import asyncio
import json
from typing import Callable, List, Optional, Any, Set
from datetime import datetime, timezone

import websockets
from websockets.client import WebSocketClientProtocol

from app.integrations.market_data.base import MarketDataProvider, TickerUpdate, TradeUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BinanceWebSocketClient(MarketDataProvider):
    """
    Binance WebSocket client for real-time market data.
    
    FREE - No API key required!
    
    Usage:
        client = BinanceWebSocketClient()
        await client.connect()
        client.on_ticker(lambda t: print(f"{t.symbol}: ${t.price}"))
        await client.subscribe(["BTCUSDT", "ETHUSDT"])
    """
    
    # WebSocket endpoints
    SPOT_WS_URL = "wss://stream.binance.com:9443/ws"
    FUTURES_WS_URL = "wss://fstream.binance.com/ws"
    
    def __init__(self, use_futures: bool = True):
        """
        Initialize Binance WebSocket client.
        
        Args:
            use_futures: Use futures endpoint (default) or spot endpoint
        """
        self._ws_url = self.FUTURES_WS_URL if use_futures else self.SPOT_WS_URL
        self._ws: Optional[WebSocketClientProtocol] = None
        self._connected = False
        self._subscribed_symbols: Set[str] = set()
        self._ticker_callbacks: List[Callable[[TickerUpdate], Any]] = []
        self._trade_callbacks: List[Callable[[TradeUpdate], Any]] = []
        self._listen_task: Optional[asyncio.Task] = None
        self._reconnect_delay = 1  # Start with 1 second
        self._max_reconnect_delay = 60  # Max 60 seconds
        self._should_reconnect = True
        self._message_id = 0
        
    def _get_next_id(self) -> int:
        """Get next message ID for requests."""
        self._message_id += 1
        return self._message_id
    
    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """
        Normalize symbol to Binance format.
        
        Args:
            symbol: Symbol like "BTC/USDT" or "BTCUSDT"
            
        Returns:
            Binance format symbol (lowercase for streams)
        """
        return symbol.replace("/", "").lower()
    
    async def connect(self) -> None:
        """Establish WebSocket connection to Binance."""
        if self._connected:
            return
            
        try:
            logger.info(f"Connecting to Binance WebSocket: {self._ws_url}")
            self._ws = await websockets.connect(
                self._ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            )
            self._connected = True
            self._reconnect_delay = 1  # Reset on successful connect
            self._should_reconnect = True
            
            # Start listening for messages
            self._listen_task = asyncio.create_task(self._listen_loop())
            
            logger.info("Connected to Binance WebSocket")
            
            # Resubscribe to symbols if any
            if self._subscribed_symbols:
                await self._send_subscribe(list(self._subscribed_symbols))
                
        except Exception as e:
            logger.error(f"Failed to connect to Binance WebSocket: {e}")
            self._connected = False
            raise
    
    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._should_reconnect = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
            
        if self._ws:
            await self._ws.close()
            self._ws = None
            
        self._connected = False
        logger.info("Disconnected from Binance WebSocket")
    
    async def subscribe(self, symbols: List[str]) -> None:
        """
        Subscribe to ticker streams for given symbols.
        
        Args:
            symbols: List of symbols (e.g., ["BTCUSDT", "ETHUSDT"])
        """
        normalized = [self.normalize_symbol(s) for s in symbols]
        new_symbols = [s for s in normalized if s not in self._subscribed_symbols]
        
        if not new_symbols:
            return
            
        self._subscribed_symbols.update(new_symbols)
        
        if self._connected:
            await self._send_subscribe(new_symbols)
    
    async def unsubscribe(self, symbols: List[str]) -> None:
        """
        Unsubscribe from ticker streams for given symbols.
        
        Args:
            symbols: List of symbols to unsubscribe
        """
        normalized = [self.normalize_symbol(s) for s in symbols]
        existing = [s for s in normalized if s in self._subscribed_symbols]
        
        if not existing:
            return
            
        for s in existing:
            self._subscribed_symbols.discard(s)
            
        if self._connected:
            await self._send_unsubscribe(existing)
    
    async def _send_subscribe(self, symbols: List[str]) -> None:
        """Send subscribe message to WebSocket."""
        if not self._ws:
            return
            
        # Subscribe to ticker streams
        streams = [f"{s}@ticker" for s in symbols]
        
        message = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": self._get_next_id()
        }
        
        await self._ws.send(json.dumps(message))
        logger.info(f"Subscribed to: {symbols}")
    
    async def _send_unsubscribe(self, symbols: List[str]) -> None:
        """Send unsubscribe message to WebSocket."""
        if not self._ws:
            return
            
        streams = [f"{s}@ticker" for s in symbols]
        
        message = {
            "method": "UNSUBSCRIBE",
            "params": streams,
            "id": self._get_next_id()
        }
        
        await self._ws.send(json.dumps(message))
        logger.info(f"Unsubscribed from: {symbols}")
    
    async def _listen_loop(self) -> None:
        """Main loop to listen for WebSocket messages."""
        while self._should_reconnect:
            try:
                if not self._ws:
                    break
                    
                async for message in self._ws:
                    await self._handle_message(message)
                    
            except websockets.ConnectionClosed as e:
                logger.warning(f"Binance WebSocket connection closed: {e}")
                self._connected = False
                
                if self._should_reconnect:
                    await self._reconnect()
                    
            except asyncio.CancelledError:
                break
                
            except Exception as e:
                logger.error(f"Error in Binance WebSocket listen loop: {e}")
                self._connected = False
                
                if self._should_reconnect:
                    await self._reconnect()
    
    async def _reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        logger.info(f"Reconnecting in {self._reconnect_delay} seconds...")
        await asyncio.sleep(self._reconnect_delay)
        
        # Exponential backoff
        self._reconnect_delay = min(
            self._reconnect_delay * 2,
            self._max_reconnect_delay
        )
        
        try:
            await self.connect()
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
    
    async def _handle_message(self, raw_message: str) -> None:
        """
        Parse and handle incoming WebSocket message.
        
        Args:
            raw_message: Raw JSON message from WebSocket
        """
        try:
            data = json.loads(raw_message)
            
            # Skip response messages (have "result" or "id" field)
            if "result" in data or (isinstance(data, dict) and "id" in data and "e" not in data):
                return
            
            # Handle ticker updates
            if data.get("e") == "24hrTicker":
                ticker = self._parse_ticker(data)
                await self._emit_ticker(ticker)
                
            # Handle trade updates
            elif data.get("e") == "trade":
                trade = self._parse_trade(data)
                await self._emit_trade(trade)
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from Binance: {raw_message[:100]}")
        except Exception as e:
            logger.error(f"Error handling Binance message: {e}")
    
    def _parse_ticker(self, data: dict) -> TickerUpdate:
        """Parse Binance ticker message to TickerUpdate."""
        return TickerUpdate(
            symbol=data.get("s", "").upper(),
            price=float(data.get("c", 0)),  # Last price
            change_24h=float(data.get("p", 0)),  # Price change
            change_percent_24h=float(data.get("P", 0)),  # Price change percent
            high_24h=float(data.get("h", 0)),  # High price
            low_24h=float(data.get("l", 0)),  # Low price
            volume_24h=float(data.get("v", 0)),  # Base asset volume
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    
    def _parse_trade(self, data: dict) -> TradeUpdate:
        """Parse Binance trade message to TradeUpdate."""
        return TradeUpdate(
            symbol=data.get("s", "").upper(),
            price=float(data.get("p", 0)),
            quantity=float(data.get("q", 0)),
            side="sell" if data.get("m", False) else "buy",  # m=True means buyer is maker
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    
    async def _emit_ticker(self, ticker: TickerUpdate) -> None:
        """Emit ticker update to all registered callbacks."""
        for callback in self._ticker_callbacks:
            try:
                result = callback(ticker)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in ticker callback: {e}")
    
    async def _emit_trade(self, trade: TradeUpdate) -> None:
        """Emit trade update to all registered callbacks."""
        for callback in self._trade_callbacks:
            try:
                result = callback(trade)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in trade callback: {e}")
    
    def on_ticker(self, callback: Callable[[TickerUpdate], Any]) -> None:
        """
        Register callback for ticker updates.
        
        Args:
            callback: Function to call with TickerUpdate
        """
        self._ticker_callbacks.append(callback)
    
    def on_trade(self, callback: Callable[[TradeUpdate], Any]) -> None:
        """
        Register callback for trade updates.
        
        Args:
            callback: Function to call with TradeUpdate
        """
        self._trade_callbacks.append(callback)
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected
    
    @property
    def subscribed_symbols(self) -> List[str]:
        """Get list of subscribed symbols."""
        return list(self._subscribed_symbols)


# Singleton instance
_binance_ws_client: Optional[BinanceWebSocketClient] = None


def get_binance_ws_client(use_futures: bool = True) -> BinanceWebSocketClient:
    """
    Get singleton Binance WebSocket client instance.
    
    Args:
        use_futures: Use futures endpoint (default) or spot
        
    Returns:
        BinanceWebSocketClient instance
    """
    global _binance_ws_client
    if _binance_ws_client is None:
        _binance_ws_client = BinanceWebSocketClient(use_futures=use_futures)
    return _binance_ws_client
