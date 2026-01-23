"""
Reddit Guerrilla Market Data Client

Fetches crypto sentiment from Reddit using the .json endpoint hack.
No API credentials required - bypasses official API rate limits.

Author: Moniqo Team
Last Updated: 2026-01-23
"""

import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedditGuerrillaClient:
    """
    Reddit Guerrilla Client
    
    Fetches Reddit posts using the public .json endpoint hack.
    No OAuth required - uses realistic browser User-Agent to avoid 429s.
    
    Usage:
        client = RedditGuerrillaClient()
        data = await client.get_symbol_sentiment("BTC", limit=10)
        # Returns: {"mention_volume": 10, "total_upvotes": 1500, "posts": [...]}
    """
    
    # Realistic browser User-Agent to avoid rate limits
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Symbol to subreddit mapping
    SYMBOL_SUBREDDITS: Dict[str, List[str]] = {
        "BTC": ["Bitcoin", "BitcoinMarkets"],
        "ETH": ["ethereum", "ethtrader"],
        "SOL": ["solana"],
        "XRP": ["Ripple", "XRP"],
        "DOGE": ["dogecoin"],
        "ADA": ["cardano"],
        "AVAX": ["Avax"],
        "LINK": ["Chainlink"],
        "DOT": ["Polkadot"],
        "MATIC": ["maticnetwork", "polygonnetwork"],
    }
    
    # Bullish keywords for sentiment analysis
    BULLISH_WORDS = {
        "moon", "bullish", "buy", "long", "pump", "breakout", "ath",
        "rally", "surge", "rocket", "explosion", "gains", "profit",
        "hodl", "accumulate", "undervalued", "opportunity", "green",
        "up", "higher", "bull", "lambo", "rich", "winner", "strong",
        "support", "bounce", "recovery", "momentum", "fomo"
    }
    
    # Bearish keywords for sentiment analysis
    BEARISH_WORDS = {
        "dump", "bearish", "sell", "short", "crash", "drop", "dip",
        "correction", "plunge", "tank", "dead", "scam", "rug",
        "down", "lower", "bear", "loss", "red", "fear", "panic",
        "weak", "overvalued", "bubble", "rekt", "loser", "hack",
        "exploit", "rug pull", "liquidation", "capitulation"
    }
    
    def __init__(self):
        """Initialize Reddit Guerrilla client."""
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with browser User-Agent."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": self.USER_AGENT,
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                follow_redirects=True,
            )
        return self._client
    
    def _get_subreddits_for_symbol(self, symbol: str) -> List[str]:
        """
        Get list of subreddits for a symbol.
        
        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            
        Returns:
            List of subreddit names
        """
        symbol_upper = symbol.upper()
        if symbol_upper in self.SYMBOL_SUBREDDITS:
            return self.SYMBOL_SUBREDDITS[symbol_upper]
        # Default fallback for unknown symbols
        return ["CryptoCurrency", "CryptoMarkets"]
    
    async def _fetch_subreddit_hot(self, subreddit: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch hot posts from a subreddit using .json endpoint.
        
        Args:
            subreddit: Subreddit name (e.g., "Bitcoin")
            limit: Maximum posts to fetch
            
        Returns:
            List of post data dicts
        """
        try:
            client = await self._get_client()
            
            # Use the .json endpoint hack
            url = f"https://www.reddit.com/r/{subreddit}/hot.json"
            
            response = await client.get(
                url,
                params={
                    "limit": min(limit, 25),  # Reddit limits to 25 without auth
                    "raw_json": 1,  # Get unescaped JSON
                },
            )
            
            if response.status_code == 429:
                logger.warning(f"Reddit rate limit hit for r/{subreddit}")
                return []
            
            if response.status_code != 200:
                logger.warning(f"Reddit returned {response.status_code} for r/{subreddit}")
                return []
            
            data = response.json()
            
            posts = []
            for child in data.get("data", {}).get("children", []):
                post_data = child.get("data", {})
                
                # Skip stickied posts (usually mod announcements)
                if post_data.get("stickied", False):
                    continue
                
                posts.append({
                    "id": post_data.get("id", ""),
                    "title": post_data.get("title", ""),
                    "selftext": post_data.get("selftext", ""),
                    "ups": post_data.get("ups", 0),
                    "num_comments": post_data.get("num_comments", 0),
                    "subreddit": post_data.get("subreddit", subreddit),
                    "created_utc": post_data.get("created_utc", 0),
                    "url": post_data.get("url", ""),
                })
            
            return posts
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching r/{subreddit}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching r/{subreddit}: {e}")
            return []
    
    def _analyze_text_sentiment(self, texts: List[str]) -> float:
        """
        Analyze sentiment from text using keyword matching.
        
        Args:
            texts: List of text strings to analyze
            
        Returns:
            Sentiment score from -1.0 (bearish) to 1.0 (bullish)
        """
        if not texts:
            return 0.0
        
        scores = []
        for text in texts:
            text_lower = text.lower()
            words = set(text_lower.split())
            
            bullish_count = len(words & self.BULLISH_WORDS)
            bearish_count = len(words & self.BEARISH_WORDS)
            
            # Also check for multi-word phrases
            for phrase in ["rug pull", "all time high", "to the moon"]:
                if phrase in text_lower:
                    if phrase == "rug pull":
                        bearish_count += 2
                    else:
                        bullish_count += 2
            
            if bullish_count + bearish_count == 0:
                scores.append(0.0)
            else:
                score = (bullish_count - bearish_count) / (bullish_count + bearish_count)
                scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _classify_sentiment(self, score: float) -> str:
        """
        Classify sentiment score into category.
        
        Args:
            score: Sentiment score from -1.0 to 1.0
            
        Returns:
            "positive", "negative", or "neutral"
        """
        if score > 0.2:
            return "positive"
        elif score < -0.2:
            return "negative"
        else:
            return "neutral"
    
    async def get_symbol_sentiment(self, symbol: str, limit: int = 10) -> Optional[Dict[str, Any]]:
        """
        Get sentiment for a crypto symbol from Reddit.
        
        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH", "SOL")
            limit: Number of posts to analyze (default 10)
            
        Returns:
            Dict with sentiment data or None if unavailable:
            {
                "mention_volume": 10,
                "total_upvotes": 1500,
                "sentiment_score": 0.65,
                "sentiment": "positive",
                "posts": [
                    {
                        "title": "...",
                        "selftext_preview": "...",
                        "upvotes": 150
                    }
                ],
                "timestamp": "..."
            }
        """
        try:
            subreddits = self._get_subreddits_for_symbol(symbol)
            
            all_posts = []
            for subreddit in subreddits:
                posts = await self._fetch_subreddit_hot(subreddit, limit=limit)
                all_posts.extend(posts)
            
            if not all_posts:
                logger.info(f"No Reddit posts found for {symbol}")
                return None
            
            # Sort by upvotes and take top posts
            all_posts.sort(key=lambda x: x.get("ups", 0), reverse=True)
            top_posts = all_posts[:limit]
            
            # Extract text for sentiment analysis
            texts = []
            for post in top_posts:
                title = post.get("title", "")
                selftext = post.get("selftext", "")
                texts.append(f"{title} {selftext}")
            
            # Analyze sentiment
            sentiment_score = self._analyze_text_sentiment(texts)
            sentiment = self._classify_sentiment(sentiment_score)
            
            # Calculate totals
            total_upvotes = sum(p.get("ups", 0) for p in top_posts)
            
            # Format posts for AI consumption
            formatted_posts = []
            for post in top_posts:
                selftext = post.get("selftext", "")
                formatted_posts.append({
                    "title": post.get("title", ""),
                    "selftext_preview": selftext[:200] if selftext else "",
                    "upvotes": post.get("ups", 0),
                    "subreddit": post.get("subreddit", ""),
                })
            
            result = {
                "mention_volume": len(top_posts),
                "total_upvotes": total_upvotes,
                "sentiment_score": round(sentiment_score, 4),
                "sentiment": sentiment,
                "posts": formatted_posts,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            logger.info(
                f"Reddit Guerrilla: {symbol} -> {sentiment} "
                f"(score={sentiment_score:.2f}, posts={len(top_posts)}, upvotes={total_upvotes})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching Reddit sentiment for {symbol}: {e}")
            return None
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_reddit_client: Optional[RedditGuerrillaClient] = None


def get_reddit_client() -> RedditGuerrillaClient:
    """Get Reddit Guerrilla client singleton."""
    global _reddit_client
    if _reddit_client is None:
        _reddit_client = RedditGuerrillaClient()
    return _reddit_client
