"""
Coinlore API Client

FREE - No API key required!
Provides global crypto market stats and coin data.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

import aiohttp
from typing import List, Dict, Optional, Any
from decimal import Decimal
from dataclasses import dataclass

from app.utils.logger import get_logger

logger = get_logger(__name__)


# Coin ID mapping for popular coins
COIN_IDS = {
    "BTC": 90,
    "ETH": 80,
    "USDT": 518,
    "BNB": 2710,
    "SOL": 48543,
    "XRP": 58,
    "USDC": 33285,
    "ADA": 257,
    "AVAX": 44883,
    "DOGE": 2,
    "DOT": 12171,
    "TRX": 2713,
    "LINK": 1987,
    "MATIC": 3890,
    "SHIB": 45088,
    "LTC": 1,
    "UNI": 33162,
    "ATOM": 3794,
    "XLM": 89,
    "ETC": 118,
}


@dataclass
class GlobalStats:
    """Global crypto market statistics"""
    coins_count: int
    active_markets: int
    total_market_cap: Decimal
    total_volume: Decimal
    btc_dominance: Decimal
    eth_dominance: Decimal
    market_cap_change_24h: Decimal
    volume_change_24h: Decimal
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "coinsCount": self.coins_count,
            "activeMarkets": self.active_markets,
            "totalMarketCap": float(self.total_market_cap),
            "totalVolume": float(self.total_volume),
            "btcDominance": float(self.btc_dominance),
            "ethDominance": float(self.eth_dominance),
            "marketCapChange24h": float(self.market_cap_change_24h),
            "volumeChange24h": float(self.volume_change_24h),
        }


@dataclass
class CoinInfo:
    """Coin information"""
    id: str
    symbol: str
    name: str
    rank: int
    price_usd: Decimal
    change_1h: Decimal
    change_24h: Decimal
    change_7d: Decimal
    price_btc: Decimal
    market_cap: Decimal
    volume_24h: Decimal
    circulating_supply: Decimal
    total_supply: Decimal
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "rank": self.rank,
            "priceUsd": float(self.price_usd),
            "change1h": float(self.change_1h),
            "change24h": float(self.change_24h),
            "change7d": float(self.change_7d),
            "priceBtc": float(self.price_btc),
            "marketCap": float(self.market_cap),
            "volume24h": float(self.volume_24h),
            "circulatingSupply": float(self.circulating_supply),
            "totalSupply": float(self.total_supply),
        }


class CoinloreClient:
    """
    Coinlore API Client
    
    FREE - No API key required!
    
    Usage:
        async with CoinloreClient() as client:
            stats = await client.get_global_stats()
            coins = await client.get_top_coins(limit=20)
    """
    
    BASE_URL = "https://api.coinlore.net/api"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info("Coinlore client initialized")
    
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

    async def _read_json(self, response: aiohttp.ClientResponse) -> Optional[Any]:
        """Safely read JSON even if content-type is misreported."""
        try:
            return await response.json(content_type=None)
        except Exception as e:
            try:
                text = await response.text()
            except Exception:
                text = "<unreadable response body>"
            logger.error(f"Coinlore API invalid JSON: {str(e)} - body: {text[:200]}")
            return None
    
    async def get_global_stats(self) -> Optional[GlobalStats]:
        """
        Get global market statistics.
        
        Returns:
            GlobalStats or None
        """
        session = await self._get_session()
        url = f"{self.BASE_URL}/global/"
        
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Coinlore API error: {response.status}")
                    return None
                
                data = await self._read_json(response)
                
                if not data or len(data) == 0:
                    return None
                
                stats = data[0]
                
                return GlobalStats(
                    coins_count=stats.get("coins_count", 0),
                    active_markets=stats.get("active_markets", 0),
                    total_market_cap=Decimal(str(stats.get("total_mcap", 0))),
                    total_volume=Decimal(str(stats.get("total_volume", 0))),
                    btc_dominance=Decimal(str(stats.get("btc_d", 0))),
                    eth_dominance=Decimal(str(stats.get("eth_d", 0))),
                    market_cap_change_24h=Decimal(str(stats.get("mcap_change", 0))),
                    volume_change_24h=Decimal(str(stats.get("volume_change", 0))),
                )
                
        except aiohttp.ClientError as e:
            logger.error(f"Coinlore API fetch error: {str(e)}")
            return None
    
    async def get_top_coins(self, start: int = 0, limit: int = 100) -> List[CoinInfo]:
        """
        Get top coins by market cap.
        
        Args:
            start: Starting position (default: 0)
            limit: Number of coins (default: 100, max: 100)
            
        Returns:
            List of CoinInfo
        """
        session = await self._get_session()
        url = f"{self.BASE_URL}/tickers/"
        params = {"start": start, "limit": min(limit, 100)}
        
        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Coinlore API error: {response.status}")
                    return []
                
                data = await self._read_json(response)
                
                if not data or "data" not in data:
                    return []
                
                coins = []
                for coin in data["data"]:
                    coins.append(CoinInfo(
                        id=coin.get("id", ""),
                        symbol=coin.get("symbol", ""),
                        name=coin.get("name", ""),
                        rank=coin.get("rank", 0),
                        price_usd=Decimal(str(coin.get("price_usd", 0))),
                        change_1h=Decimal(str(coin.get("percent_change_1h", 0))),
                        change_24h=Decimal(str(coin.get("percent_change_24h", 0))),
                        change_7d=Decimal(str(coin.get("percent_change_7d", 0))),
                        price_btc=Decimal(str(coin.get("price_btc", 0))),
                        market_cap=Decimal(str(coin.get("market_cap_usd", 0))),
                        volume_24h=Decimal(str(coin.get("volume24", 0))),
                        circulating_supply=Decimal(str(coin.get("csupply", 0) or 0)),
                        total_supply=Decimal(str(coin.get("tsupply", 0) or 0)),
                    ))
                
                logger.debug(f"Fetched {len(coins)} coins from Coinlore")
                return coins
                
        except aiohttp.ClientError as e:
            logger.error(f"Coinlore API fetch error: {str(e)}")
            return []
    
    async def get_coin_by_id(self, coin_id: int) -> Optional[CoinInfo]:
        """
        Get specific coin by ID.
        
        Args:
            coin_id: Coinlore coin ID
            
        Returns:
            CoinInfo or None
        """
        session = await self._get_session()
        url = f"{self.BASE_URL}/ticker/"
        params = {"id": coin_id}
        
        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None
                
                data = await self._read_json(response)
                
                if not data or len(data) == 0:
                    return None
                
                coin = data[0]
                
                return CoinInfo(
                    id=coin.get("id", ""),
                    symbol=coin.get("symbol", ""),
                    name=coin.get("name", ""),
                    rank=coin.get("rank", 0),
                    price_usd=Decimal(str(coin.get("price_usd", 0))),
                    change_1h=Decimal(str(coin.get("percent_change_1h", 0))),
                    change_24h=Decimal(str(coin.get("percent_change_24h", 0))),
                    change_7d=Decimal(str(coin.get("percent_change_7d", 0))),
                    price_btc=Decimal(str(coin.get("price_btc", 0))),
                    market_cap=Decimal(str(coin.get("market_cap_usd", 0))),
                    volume_24h=Decimal(str(coin.get("volume24", 0))),
                    circulating_supply=Decimal(str(coin.get("csupply", 0) or 0)),
                    total_supply=Decimal(str(coin.get("tsupply", 0) or 0)),
                )
                
        except aiohttp.ClientError as e:
            logger.error(f"Coinlore API fetch error: {str(e)}")
            return None
    
    async def get_coin_by_symbol(self, symbol: str) -> Optional[CoinInfo]:
        """
        Get coin by symbol.
        
        Args:
            symbol: Coin symbol (e.g., "BTC", "ETH")
            
        Returns:
            CoinInfo or None
        """
        coin_id = COIN_IDS.get(symbol.upper())
        
        if coin_id:
            return await self.get_coin_by_id(coin_id)
        
        # Fallback: search in top 100 coins
        top_coins = await self.get_top_coins(0, 100)
        for coin in top_coins:
            if coin.symbol.upper() == symbol.upper():
                return coin
        
        return None
    
    async def test_connection(self) -> bool:
        """Test Coinlore API connectivity"""
        stats = await self.get_global_stats()
        return stats is not None


# Singleton instance
_coinlore_client: Optional[CoinloreClient] = None


def get_coinlore_client() -> CoinloreClient:
    """Get singleton Coinlore client instance"""
    global _coinlore_client
    if _coinlore_client is None:
        _coinlore_client = CoinloreClient()
    return _coinlore_client
