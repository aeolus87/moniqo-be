"""
Market Data Provider Base Classes

Abstract interface for market data providers following SOLID principles.
Allows easy swapping between Binance, OKX, Bybit, etc.

Author: Moniqo Team
"""

from abc import ABC, abstractmethod
from typing import Callable, List, Optional, Any, Dict
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TickerUpdate:
    """Standardized ticker update from any provider"""
    symbol: str
    price: float
    change_24h: float = 0.0
    change_percent_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    volume_24h: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change_24h": self.change_24h,
            "change_percent_24h": self.change_percent_24h,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "volume_24h": self.volume_24h,
            "timestamp": self.timestamp,
        }


@dataclass
class TradeUpdate:
    """Standardized trade update from any provider"""
    symbol: str
    price: float
    quantity: float
    side: str  # "buy" or "sell"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "quantity": self.quantity,
            "side": self.side,
            "timestamp": self.timestamp,
        }


class MarketDataProvider(ABC):
    """
    Abstract base class for market data providers.
    
    Implementations: BinanceWebSocketClient, OkxWebSocketClient, etc.
    
    Usage:
        provider = BinanceWebSocketClient()
        await provider.connect()
        provider.on_ticker(my_callback)
        await provider.subscribe(["BTCUSDT", "ETHUSDT"])
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the market data source."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the market data source."""
        pass
    
    @abstractmethod
    async def subscribe(self, symbols: List[str]) -> None:
        """Subscribe to market data for given symbols."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, symbols: List[str]) -> None:
        """Unsubscribe from market data for given symbols."""
        pass
    
    @abstractmethod
    def on_ticker(self, callback: Callable[[TickerUpdate], Any]) -> None:
        """Register callback for ticker updates."""
        pass
    
    @abstractmethod
    def on_trade(self, callback: Callable[[TradeUpdate], Any]) -> None:
        """Register callback for trade updates."""
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if currently connected."""
        pass
    
    @property
    @abstractmethod
    def subscribed_symbols(self) -> List[str]:
        """Get list of currently subscribed symbols."""
        pass
