"""
Reddit Sentiment Client

Fetches crypto sentiment from Reddit.

Requires: Reddit API credentials (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)

Author: Moniqo Team
Last Updated: 2026-01-17
"""

import os
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.integrations.sentiment.base import BaseSentimentClient, SentimentResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedditSentimentClient(BaseSentimentClient):
    """
    Reddit sentiment client.
    
    Uses Reddit API to search posts in crypto subreddits.
    
    Usage:
        client = RedditSentimentClient()
        sentiment = await client.get_sentiment("BTC")
    """
    
    BASE_URL = "https://oauth.reddit.com"
    AUTH_URL = "https://www.reddit.com/api/v1/access_token"
    
    # Crypto-related subreddits
    CRYPTO_SUBREDDITS = [
        "Bitcoin",
        "CryptoCurrency",
        "CryptoMarkets",
        "ethereum",
        "altcoin",
        "BitcoinMarkets",
    ]
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize Reddit client.
        
        Args:
            client_id: Reddit app client ID (or set REDDIT_CLIENT_ID)
            client_secret: Reddit app client secret (or set REDDIT_CLIENT_SECRET)
        """
        super().__init__()
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
    
    @property
    def source_name(self) -> str:
        return "reddit"
    
    async def _authenticate(self) -> bool:
        """Get OAuth2 access token."""
        if not self.client_id or not self.client_secret:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.AUTH_URL,
                    auth=(self.client_id, self.client_secret),
                    data={
                        "grant_type": "client_credentials",
                    },
                    headers={
                        "User-Agent": "MoniqoTradingBot/1.0",
                    },
                )
                response.raise_for_status()
                data = response.json()
                self._access_token = data.get("access_token")
                return bool(self._access_token)
        except httpx.HTTPError as e:
            logger.error(f"Reddit authentication failed: {e}")
            return False
    
    async def _get_client(self) -> Optional[httpx.AsyncClient]:
        """Get or create authenticated HTTP client."""
        if not self._access_token:
            if not await self._authenticate():
                return None
        
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "User-Agent": "MoniqoTradingBot/1.0",
                },
                timeout=30.0,
            )
        return self._client
    
    async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search Reddit posts.
        
        Args:
            query: Search query
            limit: Maximum posts to return
            
        Returns:
            List of post objects
        """
        client = await self._get_client()
        if not client:
            logger.warning("Reddit API not authenticated, returning empty results")
            return []
        
        try:
            # Search across crypto subreddits
            subreddit_str = "+".join(self.CRYPTO_SUBREDDITS)
            
            response = await client.get(
                f"/r/{subreddit_str}/search",
                params={
                    "q": query,
                    "sort": "new",
                    "limit": min(limit, 100),
                    "t": "day",  # Last 24 hours
                    "restrict_sr": "true",
                },
            )
            
            if response.status_code == 401:
                # Token expired, re-authenticate
                self._access_token = None
                self._client = None
                return await self.search(query, limit)
            
            if response.status_code == 429:
                logger.warning("Reddit API rate limit exceeded")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            posts = []
            for child in data.get("data", {}).get("children", []):
                posts.append(child.get("data", {}))
            
            return posts
            
        except httpx.HTTPError as e:
            logger.error(f"Reddit API error: {e}")
            return []
    
    async def get_sentiment(self, symbol: str, **kwargs) -> SentimentResult:
        """
        Get sentiment for a crypto symbol from Reddit.
        
        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            
        Returns:
            SentimentResult with Reddit sentiment
        """
        posts = await self.search(symbol, limit=100)
        
        if not posts:
            return SentimentResult.from_score(
                source=self.source_name,
                symbol=symbol,
                score=0.0,
                sample_size=0,
                data={"error": "No posts found or API unavailable"},
            )
        
        # Extract post titles and selftext
        texts = []
        for post in posts:
            title = post.get("title", "")
            selftext = post.get("selftext", "")
            texts.append(f"{title} {selftext}")
        
        # Analyze sentiment
        score = self._analyze_text_sentiment(texts)
        
        # Get engagement metrics
        total_upvotes = sum(p.get("ups", 0) for p in posts)
        total_comments = sum(p.get("num_comments", 0) for p in posts)
        
        return SentimentResult.from_score(
            source=self.source_name,
            symbol=symbol,
            score=score,
            sample_size=len(posts),
            data={
                "post_count": len(posts),
                "total_upvotes": total_upvotes,
                "total_comments": total_comments,
                "subreddits": self.CRYPTO_SUBREDDITS,
            },
        )
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_reddit_client: Optional[RedditSentimentClient] = None


def get_reddit_client() -> RedditSentimentClient:
    """Get Reddit sentiment client singleton."""
    global _reddit_client
    if _reddit_client is None:
        _reddit_client = RedditSentimentClient()
    return _reddit_client
