"""
Binance Public API Client

FREE - No API key required!
Provides real OHLCV data from Binance exchange.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

import aiohttp
from typing import List, Dict, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass

from app.utils.logger import get_logger

logger = get_logger(__name__)


# Timeframe mapping
TIMEFRAME_MAP = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1d",
    "3d": "3d",
    "1w": "1w",
    "1M": "1M",
}


@dataclass
class Candle:
    """OHLCV candle data"""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": int(self.timestamp.timestamp()),
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": float(self.volume),
        }


@dataclass
class TickerStats:
    """24h ticker statistics"""
    symbol: str
    price: Decimal
    change_24h: Decimal
    change_percent_24h: Decimal
    high_24h: Decimal
    low_24h: Decimal
    volume_24h: Decimal
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": float(self.price),
            "change24h": float(self.change_24h),
            "changePercent24h": float(self.change_percent_24h),
            "high24h": float(self.high_24h),
            "low24h": float(self.low_24h),
            "volume24h": float(self.volume_24h),
        }


class BinanceClient:
    """
    Binance Public API Client
    
    FREE - No API key required!
    
    Usage:
        async with BinanceClient() as client:
            candles = await client.get_klines("BTC/USDT", "1h", 100)
            ticker = await client.get_24h_ticker("BTC/USDT")
    """
    
    BASE_URL = "https://api.binance.com/api/v3"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info("Binance client initialized")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    @staticmethod
    def to_binance_symbol(symbol: str) -> str:
        """Convert symbol format: BTC/USDT -> BTCUSDT"""
        return symbol.replace("/", "").upper()
    
    @staticmethod
    def from_binance_symbol(binance_symbol: str) -> str:
        """Convert Binance symbol back: BTCUSDT -> BTC/USDT"""
        quotes = ["USDT", "BUSD", "USDC", "BTC", "ETH", "BNB", "TUSD", "FDUSD"]
        for quote in quotes:
            if binance_symbol.endswith(quote):
                return f"{binance_symbol[:-len(quote)]}/{quote}"
        return binance_symbol
    
    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100
    ) -> List[Candle]:
        """
        Get OHLCV candlestick data from Binance.
        
        Args:
            symbol: Symbol like "BTC/USDT" or "BTCUSDT"
            interval: Timeframe: "1m", "5m", "15m", "1h", "4h", "1d", etc.
            limit: Number of candles (default: 100, max: 1000)
            
        Returns:
            List of Candle objects
        """
        binance_symbol = self.to_binance_symbol(symbol)
        binance_interval = TIMEFRAME_MAP.get(interval, "1h")
        
        session = await self._get_session()
        url = f"{self.BASE_URL}/klines"
        params = {
            "symbol": binance_symbol,
            "interval": binance_interval,
            "limit": min(limit, 1000)
        }
        
        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Binance API error: {response.status} - {error_text}")
                    return []
                
                data = await response.json()
                
                candles = []
                for kline in data:
                    candles.append(Candle(
                        timestamp=datetime.fromtimestamp(kline[0] / 1000, tz=timezone.utc),
                        open=Decimal(kline[1]),
                        high=Decimal(kline[2]),
                        low=Decimal(kline[3]),
                        close=Decimal(kline[4]),
                        volume=Decimal(kline[5]),
                    ))
                
                logger.debug(f"Fetched {len(candles)} candles for {symbol}")
                return candles
                
        except aiohttp.ClientError as e:
            logger.error(f"Binance API fetch error: {str(e)}")
            return []
    
    async def get_24h_ticker(self, symbol: str) -> Optional[TickerStats]:
        """
        Get 24h ticker stats for a symbol.
        
        Args:
            symbol: Symbol like "BTC/USDT" or "BTCUSDT"
            
        Returns:
            TickerStats or None
        """
        binance_symbol = self.to_binance_symbol(symbol)
        
        session = await self._get_session()
        url = f"{self.BASE_URL}/ticker/24hr"
        params = {"symbol": binance_symbol}
        
        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Binance API error: {response.status}")
                    return None
                
                data = await response.json()
                
                return TickerStats(
                    symbol=self.from_binance_symbol(data["symbol"]),
                    price=Decimal(data["lastPrice"]),
                    change_24h=Decimal(data["priceChange"]),
                    change_percent_24h=Decimal(data["priceChangePercent"]),
                    high_24h=Decimal(data["highPrice"]),
                    low_24h=Decimal(data["lowPrice"]),
                    volume_24h=Decimal(data["quoteVolume"]),
                )
                
        except aiohttp.ClientError as e:
            logger.error(f"Binance API fetch error: {str(e)}")
            return None
    
    async def get_price(self, symbol: str) -> Optional[Decimal]:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Symbol like "BTC/USDT" or "BTCUSDT"
            
        Returns:
            Current price or None
        """
        binance_symbol = self.to_binance_symbol(symbol)
        
        session = await self._get_session()
        url = f"{self.BASE_URL}/ticker/price"
        params = {"symbol": binance_symbol}
        
        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                return Decimal(data["price"])
                
        except aiohttp.ClientError as e:
            logger.error(f"Binance price fetch error: {str(e)}")
            return None
    
    async def get_multiple_tickers(self, symbols: List[str]) -> List[TickerStats]:
        """
        Get 24h tickers for multiple symbols.
        
        Args:
            symbols: List of symbols
            
        Returns:
            List of TickerStats
        """
        binance_symbols = [self.to_binance_symbol(s) for s in symbols]
        
        session = await self._get_session()
        url = f"{self.BASE_URL}/ticker/24hr"
        
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return []
                
                all_tickers = await response.json()
                
                result = []
                for data in all_tickers:
                    if data["symbol"] in binance_symbols:
                        result.append(TickerStats(
                            symbol=self.from_binance_symbol(data["symbol"]),
                            price=Decimal(data["lastPrice"]),
                            change_24h=Decimal(data["priceChange"]),
                            change_percent_24h=Decimal(data["priceChangePercent"]),
                            high_24h=Decimal(data["highPrice"]),
                            low_24h=Decimal(data["lowPrice"]),
                            volume_24h=Decimal(data["quoteVolume"]),
                        ))
                
                return result
                
        except aiohttp.ClientError as e:
            logger.error(f"Binance tickers fetch error: {str(e)}")
            return []
    
    async def test_connection(self) -> bool:
        """Test Binance API connectivity"""
        session = await self._get_session()
        url = f"{self.BASE_URL}/time"
        
        try:
            async with session.get(url) as response:
                return response.status == 200
        except:
            return False


# Singleton instance
_binance_client: Optional[BinanceClient] = None


def get_binance_client() -> BinanceClient:
    """Get singleton Binance client instance"""
    global _binance_client
    if _binance_client is None:
        _binance_client = BinanceClient()
    return _binance_client
