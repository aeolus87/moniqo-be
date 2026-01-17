"""
Sentiment Integrations

Social media and prediction market sentiment sources.

- X/Twitter: Search tweets for crypto sentiment
- Reddit: Search subreddits for crypto sentiment
- Polymarket: Prediction market odds as signals

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from app.integrations.sentiment.base import BaseSentimentClient, SentimentResult
from app.integrations.sentiment.twitter_client import TwitterSentimentClient
from app.integrations.sentiment.reddit_client import RedditSentimentClient
from app.integrations.sentiment.polymarket_client import PolymarketClient

__all__ = [
    "BaseSentimentClient",
    "SentimentResult",
    "TwitterSentimentClient",
    "RedditSentimentClient",
    "PolymarketClient",
]
