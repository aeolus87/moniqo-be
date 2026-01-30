"""
Base Sentiment Client

Abstract base class for sentiment data sources.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


class SentimentScore(str, Enum):
    """Sentiment classification"""
    VERY_BEARISH = "very_bearish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    VERY_BULLISH = "very_bullish"


class SentimentResult(BaseModel):
    """Result from a sentiment analysis"""
    source: str  # "twitter", "reddit", "polymarket"
    symbol: str  # "BTC", "ETH", etc.
    score: float  # -1.0 (bearish) to 1.0 (bullish)
    classification: SentimentScore
    confidence: float  # 0.0 to 1.0
    sample_size: int  # Number of data points analyzed
    data: Optional[Dict[str, Any]] = None  # Raw data
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def from_score(cls, source: str, symbol: str, score: float, sample_size: int, data: Optional[Dict] = None) -> "SentimentResult":
        """Create SentimentResult from numeric score."""
        # Classify score
        if score <= -0.6:
            classification = SentimentScore.VERY_BEARISH
        elif score <= -0.2:
            classification = SentimentScore.BEARISH
        elif score <= 0.2:
            classification = SentimentScore.NEUTRAL
        elif score <= 0.6:
            classification = SentimentScore.BULLISH
        else:
            classification = SentimentScore.VERY_BULLISH
        
        # Confidence based on sample size
        confidence = min(1.0, sample_size / 100)
        
        return cls(
            source=source,
            symbol=symbol,
            score=score,
            classification=classification,
            confidence=confidence,
            sample_size=sample_size,
            data=data,
        )


class BaseSentimentClient(ABC):
    """
    Abstract base class for sentiment data sources.
    
    All sentiment clients should implement:
    - get_sentiment(symbol): Get current sentiment for a symbol
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize sentiment client.
        
        Args:
            api_key: API key for the service (if required)
        """
        self.api_key = api_key
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source name (e.g., 'twitter', 'reddit')."""
        pass
    
    @abstractmethod
    async def get_sentiment(self, symbol: str, **kwargs) -> SentimentResult:
        """
        Get sentiment for a symbol.
        
        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            **kwargs: Additional parameters
            
        Returns:
            SentimentResult with score and classification
        """
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for content matching query.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of search results
        """
        pass
    
    def _analyze_text_sentiment(self, texts: List[str]) -> float:
        """
        Simple keyword-based sentiment analysis.
        
        This is a basic implementation. For production, use a proper
        NLP model or sentiment API.
        
        Args:
            texts: List of text to analyze
            
        Returns:
            Average sentiment score (-1.0 to 1.0)
        """
        if not texts:
            return 0.0
        
        # Bullish keywords
        bullish_words = {
            "moon", "bullish", "buy", "long", "pump", "breakout", "ath",
            "rally", "surge", "rocket", "explosion", "gains", "profit",
            "hodl", "accumulate", "undervalued", "opportunity", "green",
            "up", "higher", "bull", "lambo", "rich", "winner", "strong"
        }
        
        # Bearish keywords
        bearish_words = {
            "dump", "bearish", "sell", "short", "crash", "drop", "dip",
            "correction", "plunge", "tank", "dead", "scam", "rug",
            "down", "lower", "bear", "loss", "red", "fear", "panic",
            "weak", "overvalued", "bubble", "rekt", "loser"
        }
        
        scores = []
        for text in texts:
            text_lower = text.lower()
            words = set(text_lower.split())
            
            bullish_count = len(words & bullish_words)
            bearish_count = len(words & bearish_words)
            
            if bullish_count + bearish_count == 0:
                scores.append(0.0)
            else:
                score = (bullish_count - bearish_count) / (bullish_count + bearish_count)
                scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.0
