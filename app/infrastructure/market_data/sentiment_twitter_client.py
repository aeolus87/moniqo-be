"""
Twitter/X Sentiment Client

Fetches crypto sentiment from X/Twitter.

Requires: X API Bearer Token (TWITTER_BEARER_TOKEN)

Author: Moniqo Team
Last Updated: 2026-01-17
"""

import os
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from app.infrastructure.market_data.sentiment_base import BaseSentimentClient, SentimentResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TwitterSentimentClient(BaseSentimentClient):
    """
    Twitter/X sentiment client.
    
    Uses Twitter API v2 to search recent tweets.
    
    Usage:
        client = TwitterSentimentClient(api_key="your_bearer_token")
        sentiment = await client.get_sentiment("BTC")
    """
    
    BASE_URL = "https://api.twitter.com/2"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Twitter client.
        
        Args:
            api_key: Twitter Bearer Token (or set TWITTER_BEARER_TOKEN env var)
        """
        super().__init__(api_key or os.getenv("TWITTER_BEARER_TOKEN", ""))
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def source_name(self) -> str:
        return "twitter"
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client
    
    async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search recent tweets.
        
        Args:
            query: Search query (supports Twitter search operators)
            limit: Maximum tweets to return (max 100 per request)
            
        Returns:
            List of tweet objects
        """
        if not self.api_key:
            logger.warning("Twitter API key not set, returning empty results")
            return []
        
        try:
            client = await self._get_client()
            
            response = await client.get(
                "/tweets/search/recent",
                params={
                    "query": query,
                    "max_results": min(limit, 100),
                    "tweet.fields": "created_at,public_metrics,text",
                },
            )
            
            if response.status_code == 401:
                logger.error("Twitter API authentication failed")
                return []
            
            if response.status_code == 429:
                logger.warning("Twitter API rate limit exceeded")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            return data.get("data", [])
            
        except httpx.HTTPError as e:
            logger.error(f"Twitter API error: {e}")
            return []
    
    async def get_sentiment(self, symbol: str, **kwargs) -> SentimentResult:
        """
        Get sentiment for a crypto symbol from Twitter.
        
        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            
        Returns:
            SentimentResult with Twitter sentiment
        """
        # Build search query
        query = f"({symbol} OR ${symbol}) crypto -is:retweet lang:en"
        
        tweets = await self.search(query, limit=100)
        
        if not tweets:
            return SentimentResult.from_score(
                source=self.source_name,
                symbol=symbol,
                score=0.0,
                sample_size=0,
                data={"error": "No tweets found or API unavailable"},
            )
        
        # Extract tweet texts
        texts = [t.get("text", "") for t in tweets]
        
        # Analyze sentiment
        score = self._analyze_text_sentiment(texts)
        
        # Get engagement metrics
        total_likes = sum(t.get("public_metrics", {}).get("like_count", 0) for t in tweets)
        total_retweets = sum(t.get("public_metrics", {}).get("retweet_count", 0) for t in tweets)
        
        return SentimentResult.from_score(
            source=self.source_name,
            symbol=symbol,
            score=score,
            sample_size=len(tweets),
            data={
                "tweet_count": len(tweets),
                "total_likes": total_likes,
                "total_retweets": total_retweets,
                "query": query,
            },
        )
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_twitter_client: Optional[TwitterSentimentClient] = None


def get_twitter_client() -> TwitterSentimentClient:
    """Get Twitter sentiment client singleton."""
    global _twitter_client
    if _twitter_client is None:
        _twitter_client = TwitterSentimentClient()
    return _twitter_client
