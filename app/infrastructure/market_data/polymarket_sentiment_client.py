"""
Polymarket Client

Fetches prediction market odds for crypto-related markets.

Polymarket API is public, no API key required.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.infrastructure.market_data.sentiment_base import BaseSentimentClient, SentimentResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PolymarketClient(BaseSentimentClient):
    """
    Polymarket prediction market client.
    
    Fetches odds from crypto-related prediction markets.
    
    Usage:
        client = PolymarketClient()
        sentiment = await client.get_sentiment("BTC")
    """
    
    # Polymarket CLOB API (public)
    BASE_URL = "https://clob.polymarket.com"
    GAMMA_API = "https://gamma-api.polymarket.com"
    
    def __init__(self):
        """Initialize Polymarket client."""
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def source_name(self) -> str:
        return "polymarket"
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "MoniqoTradingBot/1.0",
                },
            )
        return self._client
    
    async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search Polymarket markets.
        
        Args:
            query: Search query (e.g., "Bitcoin", "BTC")
            limit: Maximum markets to return
            
        Returns:
            List of market objects
        """
        try:
            client = await self._get_client()
            
            # Search markets using Gamma API
            response = await client.get(
                f"{self.GAMMA_API}/markets",
                params={
                    "closed": "false",
                    "limit": limit,
                },
            )
            
            response.raise_for_status()
            markets = response.json()
            
            # Filter by query
            query_lower = query.lower()
            filtered = [
                m for m in markets
                if query_lower in m.get("question", "").lower()
                or query_lower in m.get("description", "").lower()
            ]
            
            return filtered[:limit]
            
        except httpx.HTTPError as e:
            logger.error(f"Polymarket API error: {e}")
            return []
    
    async def get_market(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific market by condition ID.
        
        Args:
            condition_id: Market condition ID
            
        Returns:
            Market data or None
        """
        try:
            client = await self._get_client()
            
            response = await client.get(
                f"{self.GAMMA_API}/markets/{condition_id}",
            )
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Polymarket market fetch error: {e}")
            return None
    
    async def get_sentiment(self, symbol: str, **kwargs) -> SentimentResult:
        """
        Get sentiment for a crypto symbol from Polymarket.
        
        Analyzes prediction markets related to the symbol.
        Markets with high "Yes" odds for price increases = bullish.
        Markets with high "No" odds = bearish.
        
        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            
        Returns:
            SentimentResult with Polymarket signal
        """
        # Map symbols to search terms
        symbol_terms = {
            "BTC": ["Bitcoin", "BTC"],
            "ETH": ["Ethereum", "ETH"],
            "SOL": ["Solana", "SOL"],
        }
        
        search_terms = symbol_terms.get(symbol.upper(), [symbol])
        
        all_markets = []
        for term in search_terms:
            markets = await self.search(term, limit=50)
            all_markets.extend(markets)
        
        # Remove duplicates
        seen_ids = set()
        unique_markets = []
        for m in all_markets:
            mid = m.get("id") or m.get("condition_id")
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                unique_markets.append(m)
        
        if not unique_markets:
            return SentimentResult.from_score(
                source=self.source_name,
                symbol=symbol,
                score=0.0,
                sample_size=0,
                data={"error": "No markets found"},
            )
        
        # Analyze market odds
        # Look for price prediction markets
        bullish_signals = []
        
        for market in unique_markets:
            question = market.get("question", "").lower()
            
            # Check if it's a price prediction market
            price_keywords = ["price", "reach", "hit", "above", "below", "ath", "high"]
            is_price_market = any(kw in question for kw in price_keywords)
            
            if not is_price_market:
                continue
            
            # Get outcome prices (probability)
            outcomes = market.get("tokens", [])
            if not outcomes:
                continue
            
            # Find "Yes" outcome probability
            yes_prob = None
            for outcome in outcomes:
                if outcome.get("outcome", "").lower() == "yes":
                    yes_prob = outcome.get("price", 0.5)
                    break
            
            if yes_prob is not None:
                # Determine if market is bullish or bearish
                # "Will X reach $Y" with high yes = bullish
                # "Will X drop below $Y" with high yes = bearish
                bearish_words = ["drop", "fall", "below", "crash", "decline"]
                is_bearish_question = any(w in question for w in bearish_words)
                
                if is_bearish_question:
                    # High yes prob on bearish question = bearish signal
                    signal = -(yes_prob - 0.5) * 2
                else:
                    # High yes prob on bullish question = bullish signal
                    signal = (yes_prob - 0.5) * 2
                
                bullish_signals.append(signal)
        
        if not bullish_signals:
            return SentimentResult.from_score(
                source=self.source_name,
                symbol=symbol,
                score=0.0,
                sample_size=len(unique_markets),
                data={
                    "markets_found": len(unique_markets),
                    "price_markets_analyzed": 0,
                },
            )
        
        # Average signal
        avg_signal = sum(bullish_signals) / len(bullish_signals)
        
        return SentimentResult.from_score(
            source=self.source_name,
            symbol=symbol,
            score=avg_signal,
            sample_size=len(bullish_signals),
            data={
                "markets_found": len(unique_markets),
                "price_markets_analyzed": len(bullish_signals),
                "signals": bullish_signals,
            },
        )
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_polymarket_client: Optional[PolymarketClient] = None


def get_polymarket_client() -> PolymarketClient:
    """Get Polymarket client singleton."""
    global _polymarket_client
    if _polymarket_client is None:
        _polymarket_client = PolymarketClient()
    return _polymarket_client
