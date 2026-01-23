"""
Polymarket Market Data Client

Fetches prediction market odds for BTC Price Up/Down markets.
Used to provide "smart money" signals for trading decisions.

Polymarket API is public, no API key required.

Author: Moniqo Team
Last Updated: 2026-01-23
"""

import re
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PolymarketMarketDataClient:
    """
    Polymarket Market Data Client
    
    Fetches BTC Price Up/Down market odds for short-term price predictions.
    
    Usage:
        client = PolymarketMarketDataClient()
        odds = await client.get_btc_price_up_odds("1h")
        # Returns: {"probability": 0.65, "timeframe": "1h", ...}
    """
    
    GAMMA_API = "https://gamma-api.polymarket.com"
    
    # Timeframe patterns for detection
    TIMEFRAME_PATTERNS = {
        "15m": [r"15m", r"15\s*min", r"15-min", r"15\s*minute"],
        "1h": [r"1h", r"1\s*hour", r"1-hour", r"60\s*min"],
    }
    
    def __init__(self):
        """Initialize Polymarket client."""
        self._client: Optional[httpx.AsyncClient] = None
    
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
    
    def _detect_timeframe(self, market: Dict[str, Any], target_timeframe: str) -> bool:
        """
        Detect if market matches target timeframe using fallback approach.
        
        Priority:
        1. Check slug for timeframe indicators
        2. Check tags/series metadata
        3. Fallback to question text search
        
        Args:
            market: Market data from API
            target_timeframe: "15m" or "1h"
            
        Returns:
            True if market matches target timeframe
        """
        patterns = self.TIMEFRAME_PATTERNS.get(target_timeframe, [])
        if not patterns:
            return False
        
        # 1. Check slug (most reliable)
        slug = market.get("slug", "").lower()
        for pattern in patterns:
            if re.search(pattern, slug, re.IGNORECASE):
                return True
        
        # 2. Check tags/series metadata
        tags = market.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                tag_str = str(tag).lower() if tag else ""
                for pattern in patterns:
                    if re.search(pattern, tag_str, re.IGNORECASE):
                        return True
        
        series = market.get("series", "")
        if series:
            for pattern in patterns:
                if re.search(pattern, str(series).lower(), re.IGNORECASE):
                    return True
        
        # 3. Fallback to question text
        question = market.get("question", "").lower()
        title = market.get("title", "").lower()
        description = market.get("description", "").lower()
        
        for text in [question, title, description]:
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
        
        # Check for time range patterns like "3:00AM-3:15AM" (15m) or "3:00AM-4:00AM" (1h)
        time_range_pattern = r"(\d{1,2}):(\d{2})\s*(?:AM|PM)?\s*-\s*(\d{1,2}):(\d{2})\s*(?:AM|PM)?"
        for text in [question, title]:
            match = re.search(time_range_pattern, text, re.IGNORECASE)
            if match:
                start_hour, start_min = int(match.group(1)), int(match.group(2))
                end_hour, end_min = int(match.group(3)), int(match.group(4))
                
                # Calculate duration in minutes
                duration = (end_hour * 60 + end_min) - (start_hour * 60 + start_min)
                if duration < 0:
                    duration += 24 * 60  # Handle overnight
                
                if target_timeframe == "15m" and 10 <= duration <= 20:
                    return True
                if target_timeframe == "1h" and 50 <= duration <= 70:
                    return True
        
        return False
    
    def _is_btc_price_up_market(self, market: Dict[str, Any]) -> bool:
        """
        Check if market is a BTC Price Up/Down prediction.
        
        Args:
            market: Market data from API
            
        Returns:
            True if market is about BTC price direction
        """
        question = market.get("question", "").lower()
        title = market.get("title", "").lower()
        slug = market.get("slug", "").lower()
        
        # Must contain Bitcoin/BTC
        btc_keywords = ["bitcoin", "btc"]
        has_btc = any(kw in question or kw in title or kw in slug for kw in btc_keywords)
        
        if not has_btc:
            return False
        
        # Must be about price direction
        direction_keywords = ["up", "down", "price", "higher", "lower", "rise", "fall"]
        has_direction = any(kw in question or kw in title for kw in direction_keywords)
        
        return has_direction
    
    def _extract_probability(self, market: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Extract Yes/No probabilities from market tokens.
        
        Args:
            market: Market data from API
            
        Returns:
            Dict with yes_price and no_price, or None
        """
        tokens = market.get("tokens", [])
        outcomes = market.get("outcomes", [])
        
        yes_price = None
        no_price = None
        
        # Try tokens first (CLOB API format)
        for token in tokens:
            outcome = str(token.get("outcome", "")).lower()
            price = token.get("price")
            
            if price is not None:
                if outcome == "yes":
                    yes_price = float(price)
                elif outcome == "no":
                    no_price = float(price)
        
        # Try outcomes if tokens didn't work
        if yes_price is None and outcomes:
            for i, outcome in enumerate(outcomes):
                outcome_lower = str(outcome).lower()
                # Try to get price from outcomePrices
                prices = market.get("outcomePrices", [])
                if i < len(prices):
                    price = float(prices[i])
                    if "yes" in outcome_lower or "up" in outcome_lower:
                        yes_price = price
                    elif "no" in outcome_lower or "down" in outcome_lower:
                        no_price = price
        
        if yes_price is not None:
            return {
                "yes_price": yes_price,
                "no_price": no_price if no_price is not None else (1.0 - yes_price),
            }
        
        return None
    
    async def search_markets(self, query: str = "Bitcoin", limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search Polymarket markets.
        
        Args:
            query: Search query
            limit: Maximum markets to return
            
        Returns:
            List of market objects
        """
        try:
            client = await self._get_client()
            
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
                or query_lower in m.get("title", "").lower()
                or query_lower in m.get("description", "").lower()
                or query_lower in m.get("slug", "").lower()
            ]
            
            return filtered[:limit]
            
        except httpx.HTTPError as e:
            logger.error(f"Polymarket API error: {e}")
            return []
    
    async def get_btc_price_up_odds(self, timeframe: str = "1h") -> Optional[Dict[str, Any]]:
        """
        Get BTC Price Up market odds for specified timeframe.
        
        Args:
            timeframe: "15m" or "1h"
            
        Returns:
            Dict with probability, timeframe, market info, or None if not found
            {
                "probability": 0.65,
                "timeframe": "1h",
                "market_id": "...",
                "yes_price": 0.65,
                "no_price": 0.35,
                "question": "...",
                "timestamp": "..."
            }
        """
        try:
            # Search for Bitcoin markets
            markets = await self.search_markets("Bitcoin", limit=200)
            
            if not markets:
                logger.warning("No Bitcoin markets found on Polymarket")
                return None
            
            # Filter for BTC Price Up/Down markets with matching timeframe
            matching_markets = []
            for market in markets:
                if self._is_btc_price_up_market(market) and self._detect_timeframe(market, timeframe):
                    probs = self._extract_probability(market)
                    if probs:
                        matching_markets.append({
                            "market": market,
                            "probabilities": probs,
                        })
            
            if not matching_markets:
                logger.info(f"No BTC Price Up markets found for {timeframe} timeframe")
                return None
            
            # Use the first matching market (most recent/active)
            best_match = matching_markets[0]
            market = best_match["market"]
            probs = best_match["probabilities"]
            
            result = {
                "probability": probs["yes_price"],
                "timeframe": timeframe,
                "market_id": market.get("id") or market.get("condition_id", ""),
                "yes_price": probs["yes_price"],
                "no_price": probs["no_price"],
                "question": market.get("question", ""),
                "slug": market.get("slug", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            logger.info(
                f"Polymarket BTC Price Up odds ({timeframe}): "
                f"Yes={probs['yes_price']:.1%}, No={probs['no_price']:.1%}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching Polymarket BTC odds: {e}")
            return None
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_polymarket_client: Optional[PolymarketMarketDataClient] = None


def get_polymarket_client() -> PolymarketMarketDataClient:
    """Get Polymarket market data client singleton."""
    global _polymarket_client
    if _polymarket_client is None:
        _polymarket_client = PolymarketMarketDataClient()
    return _polymarket_client
