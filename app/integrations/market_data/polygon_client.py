"""
Polygon.io Client - WebSocket + REST API

Complete Polygon.io integration:
- WebSocket for real-time market data (trades, quotes, aggregates)
- REST API for historical OHLCV data
- Multi-asset support (crypto, stocks, forex, commodities)

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import asyncio
import json
import websockets
import aiohttp
from typing import Dict, List, Optional, Callable, Set, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ==================== ENUMS ====================

class MessageType(str, Enum):
    """Polygon message types"""
    STATUS = "status"
    TRADE = "T"          # Trade
    QUOTE = "Q"          # Quote
    AGGREGATE = "A"      # Minute aggregate
    SECOND_AGG = "A"     # Second aggregate
    CRYPTO_TRADE = "XT"  # Crypto trade
    CRYPTO_QUOTE = "XQ"  # Crypto quote
    CRYPTO_AGG = "XA"    # Crypto aggregate


class AssetClass(str, Enum):
    """Asset classes"""
    CRYPTO = "crypto"
    STOCKS = "stocks"
    FOREX = "forex"
    COMMODITIES = "commodities"


class Timeframe(str, Enum):
    """Timeframes for historical data"""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


# ==================== POLYGON REST API CLIENT ====================

class PolygonRestClient:
    """
    Polygon.io REST API client for historical data.
    
    Features:
    - Historical OHLCV data (candlestick data)
    - Aggregates (bars) for any timeframe
    - Trade and quote history
    - Ticker snapshots
    
    Usage:
        client = PolygonRestClient(api_key="your_key")
        
        # Get historical OHLCV data
        bars = await client.get_aggregates(
            ticker="BTC-USD",
            multiplier=1,
            timespan="day",
            from_date="2025-01-01",
            to_date="2025-11-22"
        )
    """
    
    BASE_URL = "https://api.polygon.io"
    
    def __init__(self, api_key: str):
        """
        Initialize Polygon REST client.
        
        Args:
            api_key: Polygon.io API key
        """
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info("Polygon REST client initialized")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _close_session(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make API request to Polygon.io.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Response JSON
        """
        session = await self._get_session()
        
        # Add API key to params
        if params is None:
            params = {}
        params["apiKey"] = self.api_key
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Polygon API error: {response.status} - {error_text}")
                    raise Exception(f"Polygon API error: {error_text}")
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error: {str(e)}")
            raise Exception(f"Failed to connect to Polygon.io: {str(e)}")
    
    async def get_aggregates(
        self,
        ticker: str,
        multiplier: int,
        timespan: str,
        from_date: str,
        to_date: str,
        adjusted: bool = True,
        sort: str = "asc",
        limit: int = 50000
    ) -> List[Dict[str, Any]]:
        """
        Get aggregate bars (OHLCV) for a ticker.
        
        Args:
            ticker: Ticker symbol (e.g., "BTC-USD", "AAPL", "EUR/USD")
            multiplier: Size of timespan multiplier (e.g., 1 for 1 day)
            timespan: Size of time window (minute, hour, day, week, month, quarter, year)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            adjusted: Whether results are adjusted for splits
            sort: Sort order (asc or desc)
            limit: Max number of results (max: 50000)
            
        Returns:
            List of OHLCV bars
            
        Example:
            # Get daily bars for BTC
            bars = await client.get_aggregates(
                ticker="X:BTCUSD",
                multiplier=1,
                timespan="day",
                from_date="2025-01-01",
                to_date="2025-11-22"
            )
            
            for bar in bars:
                print(f"Date: {bar['date']}, Open: {bar['open']}, Close: {bar['close']}")
        """
        endpoint = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        
        params = {
            "adjusted": str(adjusted).lower(),
            "sort": sort,
            "limit": limit
        }
        
        try:
            response = await self._request(endpoint, params)
            
            results = response.get("results", [])
            
            # Parse results into readable format
            bars = []
            for result in results:
                bars.append({
                    "timestamp": datetime.fromtimestamp(
                        result["t"] / 1000,
                        tz=timezone.utc
                    ),
                    "date": datetime.fromtimestamp(
                        result["t"] / 1000,
                        tz=timezone.utc
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "open": Decimal(str(result["o"])),
                    "high": Decimal(str(result["h"])),
                    "low": Decimal(str(result["l"])),
                    "close": Decimal(str(result["c"])),
                    "volume": Decimal(str(result["v"])),
                    "vwap": Decimal(str(result.get("vw", 0))),  # Volume weighted average price
                    "transactions": result.get("n", 0)  # Number of transactions
                })
            
            logger.info(
                f"Fetched {len(bars)} bars for {ticker} "
                f"({from_date} to {to_date})"
            )
            
            return bars
        
        except Exception as e:
            logger.error(f"Failed to get aggregates: {str(e)}")
            raise
    
    async def get_previous_close(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get previous day's close for a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Previous close data
        """
        endpoint = f"/v2/aggs/ticker/{ticker}/prev"
        
        try:
            response = await self._request(endpoint)
            
            results = response.get("results", [])
            if not results:
                return None
            
            result = results[0]
            return {
                "ticker": result.get("T", ticker),
                "timestamp": datetime.fromtimestamp(
                    result["t"] / 1000,
                    tz=timezone.utc
                ),
                "open": Decimal(str(result["o"])),
                "high": Decimal(str(result["h"])),
                "low": Decimal(str(result["l"])),
                "close": Decimal(str(result["c"])),
                "volume": Decimal(str(result["v"]))
            }
        
        except Exception as e:
            logger.error(f"Failed to get previous close: {str(e)}")
            raise
    
    async def get_ticker_snapshot(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get current snapshot for a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Current ticker snapshot with latest trade, quote, and day data
        """
        # Determine asset class from ticker format
        if ticker.startswith("X:"):
            # Crypto
            endpoint = f"/v2/snapshot/locale/global/markets/crypto/tickers/{ticker}"
        else:
            # Stocks
            endpoint = f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        
        try:
            response = await self._request(endpoint)
            
            ticker_data = response.get("ticker", {})
            if not ticker_data:
                return None
            
            return {
                "ticker": ticker_data.get("ticker", ticker),
                "last_trade": {
                    "price": Decimal(str(ticker_data.get("lastTrade", {}).get("p", 0))),
                    "size": Decimal(str(ticker_data.get("lastTrade", {}).get("s", 0))),
                    "timestamp": datetime.fromtimestamp(
                        ticker_data.get("lastTrade", {}).get("t", 0) / 1000000000,
                        tz=timezone.utc
                    )
                },
                "last_quote": {
                    "bid": Decimal(str(ticker_data.get("lastQuote", {}).get("p", 0))),
                    "bid_size": Decimal(str(ticker_data.get("lastQuote", {}).get("s", 0))),
                    "ask": Decimal(str(ticker_data.get("lastQuote", {}).get("P", 0))),
                    "ask_size": Decimal(str(ticker_data.get("lastQuote", {}).get("S", 0)))
                },
                "day": {
                    "open": Decimal(str(ticker_data.get("day", {}).get("o", 0))),
                    "high": Decimal(str(ticker_data.get("day", {}).get("h", 0))),
                    "low": Decimal(str(ticker_data.get("day", {}).get("l", 0))),
                    "close": Decimal(str(ticker_data.get("day", {}).get("c", 0))),
                    "volume": Decimal(str(ticker_data.get("day", {}).get("v", 0)))
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to get ticker snapshot: {str(e)}")
            raise
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()


# ==================== POLYGON WEBSOCKET CLIENT ====================

class PolygonWebSocketClient:
    """
    Polygon.io WebSocket client for real-time data.
    
    Features:
    - Real-time trades, quotes, aggregates
    - Multi-asset support (crypto, stocks, forex)
    - Auto-reconnection with exponential backoff
    - Message parsing and routing
    
    Usage:
        client = PolygonWebSocketClient(api_key="your_key")
        
        # Set message handler
        client.set_message_handler(my_handler_function)
        
        # Connect and authenticate
        await client.connect()
        
        # Subscribe to symbols
        await client.subscribe_crypto_trades(["BTC-USD", "ETH-USD"])
        await client.subscribe_crypto_aggregates(["BTC-USD"])
        
        # Keep running
        await client.run()
        
        # Cleanup
        await client.close()
    """
    
    def __init__(self, api_key: str, asset_class: AssetClass = AssetClass.CRYPTO):
        """
        Initialize Polygon WebSocket client.
        
        Args:
            api_key: Polygon.io API key
            asset_class: Type of assets to stream
        """
        self.api_key = api_key
        self.asset_class = asset_class
        
        # WebSocket URLs by asset class
        self.ws_urls = {
            AssetClass.CRYPTO: "wss://socket.polygon.io/crypto",
            AssetClass.STOCKS: "wss://socket.polygon.io/stocks",
            AssetClass.FOREX: "wss://socket.polygon.io/forex"
        }
        
        self.ws_url = self.ws_urls.get(asset_class, self.ws_urls[AssetClass.CRYPTO])
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        
        # Connection state
        self.is_connected = False
        self.is_authenticated = False
        self.is_running = False
        
        # Subscriptions
        self.subscriptions: Set[str] = set()
        
        # Message handler
        self.message_handler: Optional[Callable] = None
        
        # Reconnection
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 1  # Start with 1 second
        self.max_reconnect_delay = 60  # Max 1 minute
    
    def set_message_handler(self, handler: Callable):
        """
        Set function to handle incoming messages.
        
        Handler signature: async def handler(message: Dict)
        """
        self.message_handler = handler
    
    async def connect(self):
        """
        Connect to Polygon WebSocket and authenticate.
        
        Process:
        1. Establish WebSocket connection
        2. Send authentication message
        3. Wait for auth confirmation
        """
        try:
            logger.info(f"Connecting to Polygon.io WebSocket: {self.ws_url}")
            
            # Connect
            self.ws = await websockets.connect(
                self.ws_url,
                ping_interval=30,  # Send ping every 30s
                ping_timeout=10     # Wait 10s for pong
            )
            
            self.is_connected = True
            logger.info("WebSocket connected")
            
            # Authenticate
            auth_message = {
                "action": "auth",
                "params": self.api_key
            }
            
            await self.ws.send(json.dumps(auth_message))
            logger.info("Authentication message sent")
            
            # Wait for auth response
            response = await self.ws.recv()
            data = json.loads(response)
            
            if data[0].get("status") == "auth_success":
                self.is_authenticated = True
                logger.info("✅ Polygon.io authenticated successfully")
                self.reconnect_attempts = 0  # Reset on success
            else:
                error_msg = data[0].get("message", "Unknown error")
                logger.error(f"❌ Authentication failed: {error_msg}")
                raise ConnectionError(f"Authentication failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            self.is_connected = False
            self.is_authenticated = False
            raise
    
    async def subscribe_crypto_trades(self, symbols: List[str]):
        """
        Subscribe to crypto trades.
        
        Args:
            symbols: List of crypto pairs (e.g., ["BTC-USD", "ETH-USD"])
            
        Format: XT.<PAIR>
        Example: XT.BTC-USD
        """
        channels = [f"XT.{symbol}" for symbol in symbols]
        await self._subscribe(channels)
    
    async def subscribe_crypto_quotes(self, symbols: List[str]):
        """
        Subscribe to crypto quotes (bid/ask).
        
        Format: XQ.<PAIR>
        Example: XQ.BTC-USD
        """
        channels = [f"XQ.{symbol}" for symbol in symbols]
        await self._subscribe(channels)
    
    async def subscribe_crypto_aggregates(
        self,
        symbols: List[str],
        interval: str = "minute"
    ):
        """
        Subscribe to crypto aggregates (candles).
        
        Args:
            symbols: List of crypto pairs
            interval: "second" or "minute"
            
        Format: 
        - XA.<PAIR> (minute)
        - XAS.<PAIR> (second)
        """
        if interval == "second":
            channels = [f"XAS.{symbol}" for symbol in symbols]
        else:
            channels = [f"XA.{symbol}" for symbol in symbols]
        
        await self._subscribe(channels)
    
    async def _subscribe(self, channels: List[str]):
        """
        Internal: Subscribe to channels.
        
        Args:
            channels: List of channel strings
        """
        if not self.is_authenticated:
            raise ConnectionError("Not authenticated")
        
        subscribe_message = {
            "action": "subscribe",
            "params": ",".join(channels)
        }
        
        await self.ws.send(json.dumps(subscribe_message))
        self.subscriptions.update(channels)
        
        logger.info(f"Subscribed to {len(channels)} channels: {channels[:5]}...")
    
    async def unsubscribe(self, channels: List[str]):
        """Unsubscribe from channels"""
        if not self.is_authenticated:
            return
        
        unsubscribe_message = {
            "action": "unsubscribe",
            "params": ",".join(channels)
        }
        
        await self.ws.send(json.dumps(unsubscribe_message))
        self.subscriptions.difference_update(channels)
        
        logger.info(f"Unsubscribed from {len(channels)} channels")
    
    async def run(self):
        """
        Main loop: Receive and process messages.
        
        This should run in a background task.
        Handles reconnection automatically.
        """
        self.is_running = True
        
        while self.is_running:
            try:
                if not self.is_connected:
                    await self._reconnect()
                
                # Receive message
                message = await asyncio.wait_for(
                    self.ws.recv(),
                    timeout=90  # Timeout after 90s (3x ping interval)
                )
                
                # Parse and handle
                data = json.loads(message)
                await self._handle_messages(data)
                
            except asyncio.TimeoutError:
                logger.warning("WebSocket receive timeout, reconnecting...")
                await self._reconnect()
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                await self._reconnect()
                
            except Exception as e:
                logger.error(f"Error in message loop: {str(e)}")
                await asyncio.sleep(1)
    
    async def _handle_messages(self, data: List[Dict]):
        """
        Handle incoming messages.
        
        Polygon sends messages as array of objects.
        """
        for message in data:
            ev = message.get("ev")  # Event type
            
            # Status messages
            if ev == "status":
                status = message.get("status")
                msg = message.get("message", "")
                
                if status == "success":
                    logger.debug(f"Status: {msg}")
                elif status == "error":
                    logger.error(f"Error status: {msg}")
                
                continue
            
            # Market data messages
            if self.message_handler:
                try:
                    await self.message_handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler: {str(e)}")
    
    async def _reconnect(self):
        """
        Reconnect with exponential backoff.
        """
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached, giving up")
            self.is_running = False
            return
        
        self.reconnect_attempts += 1
        
        # Exponential backoff
        delay = min(
            self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)),
            self.max_reconnect_delay
        )
        
        logger.info(
            f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} "
            f"in {delay}s..."
        )
        
        await asyncio.sleep(delay)
        
        try:
            # Close old connection if exists
            if self.ws:
                await self.ws.close()
            
            # Reconnect
            await self.connect()
            
            # Re-subscribe to previous channels
            if self.subscriptions:
                await self._subscribe(list(self.subscriptions))
            
            logger.info("✅ Reconnected successfully")
            
        except Exception as e:
            logger.error(f"Reconnection failed: {str(e)}")
    
    async def close(self):
        """Close WebSocket connection"""
        self.is_running = False
        
        if self.ws:
            await self.ws.close()
        
        self.is_connected = False
        self.is_authenticated = False
        
        logger.info("Polygon WebSocket client closed")


# ==================== MESSAGE PARSERS ====================

def parse_crypto_trade(message: Dict) -> Dict:
    """
    Parse crypto trade message.
    
    Fields:
    - ev: "XT" (event type)
    - pair: "BTC-USD"
    - p: price
    - s: size
    - t: timestamp (ms)
    - x: exchange ID
    """
    return {
        "type": "trade",
        "symbol": message["pair"],
        "price": Decimal(str(message["p"])),
        "size": Decimal(str(message["s"])),
        "timestamp": datetime.fromtimestamp(
            message["t"] / 1000,
            tz=timezone.utc
        ),
        "exchange": message.get("x", "unknown")
    }


def parse_crypto_quote(message: Dict) -> Dict:
    """
    Parse crypto quote message.
    
    Fields:
    - ev: "XQ"
    - pair: "BTC-USD"
    - bp: bid price
    - bs: bid size
    - ap: ask price
    - as: ask size
    - t: timestamp
    """
    return {
        "type": "quote",
        "symbol": message["pair"],
        "bid_price": Decimal(str(message["bp"])),
        "bid_size": Decimal(str(message["bs"])),
        "ask_price": Decimal(str(message["ap"])),
        "ask_size": Decimal(str(message.get("as", message.get("s", 0)))),  # 'as' might be 's'
        "timestamp": datetime.fromtimestamp(
            message["t"] / 1000,
            tz=timezone.utc
        )
    }


def parse_crypto_aggregate(message: Dict) -> Dict:
    """
    Parse crypto aggregate (candle) message.
    
    Fields:
    - ev: "XA" (minute) or "XAS" (second)
    - pair: "BTC-USD"
    - o: open
    - h: high
    - l: low
    - c: close
    - v: volume
    - s: start time
    - e: end time
    """
    return {
        "type": "aggregate",
        "symbol": message["pair"],
        "open": Decimal(str(message["o"])),
        "high": Decimal(str(message["h"])),
        "low": Decimal(str(message["l"])),
        "close": Decimal(str(message["c"])),
        "volume": Decimal(str(message["v"])),
        "start_time": datetime.fromtimestamp(
            message["s"] / 1000,
            tz=timezone.utc
        ),
        "end_time": datetime.fromtimestamp(
            message["e"] / 1000,
            tz=timezone.utc
        )
    }

