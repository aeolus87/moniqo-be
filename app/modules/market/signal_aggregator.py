"""
Signal Aggregator Service

Combines sentiment from multiple sources into a unified signal score.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.infrastructure.market_data.sentiment_base import SentimentResult, SentimentScore
from app.infrastructure.market_data.sentiment_twitter_client import get_twitter_client
from app.infrastructure.market_data.reddit_sentiment_client import get_reddit_client
from app.infrastructure.market_data.polymarket_sentiment_client import get_polymarket_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AggregatedSignal(BaseModel):
    """Aggregated signal from multiple sources."""
    symbol: str
    
    # Aggregated score
    score: float  # -1.0 (bearish) to 1.0 (bullish)
    classification: SentimentScore
    confidence: float  # 0.0 to 1.0
    
    # Individual source results
    sources: List[SentimentResult] = Field(default_factory=list)
    
    # Breakdown
    social_score: Optional[float] = None  # Twitter + Reddit
    market_score: Optional[float] = None  # Polymarket
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_bullish(self) -> bool:
        return self.score > 0.2
    
    @property
    def is_bearish(self) -> bool:
        return self.score < -0.2
    
    @property
    def is_neutral(self) -> bool:
        return -0.2 <= self.score <= 0.2
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/logging."""
        return {
            "symbol": self.symbol,
            "score": self.score,
            "classification": self.classification.value,
            "confidence": self.confidence,
            "social_score": self.social_score,
            "market_score": self.market_score,
            "sources": [
                {
                    "source": s.source,
                    "score": s.score,
                    "sample_size": s.sample_size,
                }
                for s in self.sources
            ],
            "timestamp": self.timestamp.isoformat(),
        }


class SignalAggregator:
    """
    Aggregates sentiment signals from multiple sources.
    
    Sources:
    - Twitter/X: Social sentiment from tweets
    - Reddit: Social sentiment from posts
    - Polymarket: Prediction market odds
    
    Usage:
        aggregator = SignalAggregator()
        signal = await aggregator.get_signal("BTC")
        
        if signal.is_bullish and signal.confidence > 0.7:
            # Execute trade
    """
    
    # Source weights for aggregation
    WEIGHTS = {
        "twitter": 0.3,
        "reddit": 0.3,
        "polymarket": 0.4,  # Higher weight for prediction markets
    }
    
    def __init__(self):
        """Initialize signal aggregator."""
        self.twitter = get_twitter_client()
        self.reddit = get_reddit_client()
        self.polymarket = get_polymarket_client()
    
    async def get_signal(
        self,
        symbol: str,
        include_sources: Optional[List[str]] = None,
    ) -> AggregatedSignal:
        """
        Get aggregated signal for a symbol.
        
        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            include_sources: List of sources to include (default: all)
            
        Returns:
            AggregatedSignal with combined sentiment
        """
        sources = include_sources or ["twitter", "reddit", "polymarket"]
        
        # Fetch sentiment from all sources in parallel
        tasks = []
        source_names = []
        
        if "twitter" in sources:
            tasks.append(self._safe_get_sentiment(self.twitter, symbol))
            source_names.append("twitter")
        
        if "reddit" in sources:
            tasks.append(self._safe_get_sentiment(self.reddit, symbol))
            source_names.append("reddit")
        
        if "polymarket" in sources:
            tasks.append(self._safe_get_sentiment(self.polymarket, symbol))
            source_names.append("polymarket")
        
        results = await asyncio.gather(*tasks)
        
        # Collect valid results
        valid_results: List[SentimentResult] = []
        for name, result in zip(source_names, results):
            if result and result.sample_size > 0:
                valid_results.append(result)
        
        if not valid_results:
            return AggregatedSignal(
                symbol=symbol,
                score=0.0,
                classification=SentimentScore.NEUTRAL,
                confidence=0.0,
                sources=[],
            )
        
        # Calculate weighted average
        weighted_sum = 0.0
        total_weight = 0.0
        
        social_scores = []
        market_scores = []
        
        for result in valid_results:
            weight = self.WEIGHTS.get(result.source, 0.2)
            weighted_sum += result.score * weight * result.confidence
            total_weight += weight * result.confidence
            
            if result.source in ["twitter", "reddit"]:
                social_scores.append(result.score)
            elif result.source == "polymarket":
                market_scores.append(result.score)
        
        final_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Calculate confidence based on source coverage
        source_coverage = len(valid_results) / len(sources)
        avg_sample_confidence = sum(r.confidence for r in valid_results) / len(valid_results)
        final_confidence = source_coverage * avg_sample_confidence
        
        # Classify
        if final_score <= -0.6:
            classification = SentimentScore.VERY_BEARISH
        elif final_score <= -0.2:
            classification = SentimentScore.BEARISH
        elif final_score <= 0.2:
            classification = SentimentScore.NEUTRAL
        elif final_score <= 0.6:
            classification = SentimentScore.BULLISH
        else:
            classification = SentimentScore.VERY_BULLISH
        
        return AggregatedSignal(
            symbol=symbol,
            score=round(final_score, 4),
            classification=classification,
            confidence=round(final_confidence, 4),
            sources=valid_results,
            social_score=sum(social_scores) / len(social_scores) if social_scores else None,
            market_score=sum(market_scores) / len(market_scores) if market_scores else None,
        )
    
    async def _safe_get_sentiment(self, client, symbol: str) -> Optional[SentimentResult]:
        """Safely get sentiment, catching any errors."""
        try:
            return await client.get_sentiment(symbol)
        except Exception as e:
            logger.error(f"Error getting sentiment from {client.source_name}: {e}")
            return None


# Singleton instance
_aggregator: Optional[SignalAggregator] = None


def get_signal_aggregator() -> SignalAggregator:
    """Get signal aggregator singleton."""
    global _aggregator
    if _aggregator is None:
        _aggregator = SignalAggregator()
    return _aggregator
