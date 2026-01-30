"""
Symbol Validation Service

Validates trading symbols across different exchanges and formats.
Converts between different symbol formats.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Dict, Optional, List, Set
from enum import Enum
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.logger import get_logger

logger = get_logger(__name__)


class Exchange(str, Enum):
    """Supported exchanges"""
    BINANCE = "binance"
    COINBASE = "coinbase"
    POLYGON = "polygon"
    DEMO = "demo"


class SymbolService:
    """
    Symbol validation and conversion service.
    
    Features:
    - Validate symbols for specific exchanges
    - Convert between symbol formats
    - Cache supported symbols
    - Symbol normalization
    
    Usage:
        service = SymbolService(db)
        
        # Validate symbol
        is_valid = await service.is_valid_symbol("BTC/USDT", Exchange.BINANCE)
        
        # Convert format
        binance_symbol = service.to_binance_format("BTC/USDT")  # -> "BTCUSDT"
        universal = service.to_universal_format("BTCUSDT", Exchange.BINANCE)  # -> "BTC/USDT"
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize symbol service.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        
        # Symbol cache (exchange -> set of symbols)
        self._symbol_cache: Dict[Exchange, Set[str]] = {}
        
        # Common quote currencies
        self.common_quotes = ["USDT", "BUSD", "BTC", "ETH", "BNB", "USD", "USDC"]
    
    async def load_symbols_for_exchange(self, exchange: Exchange) -> Set[str]:
        """
        Load supported symbols for an exchange.
        
        This would typically fetch from exchange API or database.
        For now, returns a predefined set.
        
        Args:
            exchange: Exchange to load symbols for
            
        Returns:
            Set of supported symbols in universal format
        """
        # TODO: Fetch from exchange API or database
        # For now, return common symbols
        
        common_symbols = {
            "BTC/USDT", "ETH/USDT", "BNB/USDT",
            "SOL/USDT", "ADA/USDT", "DOT/USDT",
            "MATIC/USDT", "LINK/USDT", "UNI/USDT",
            "AVAX/USDT", "ATOM/USDT", "XRP/USDT"
        }
        
        self._symbol_cache[exchange] = common_symbols
        
        logger.info(f"Loaded {len(common_symbols)} symbols for {exchange.value}")
        
        return common_symbols
    
    async def is_valid_symbol(
        self,
        symbol: str,
        exchange: Optional[Exchange] = None
    ) -> bool:
        """
        Check if symbol is valid.
        
        Args:
            symbol: Symbol in universal format (e.g., "BTC/USDT")
            exchange: Specific exchange to check (optional)
            
        Returns:
            True if valid
        """
        # Normalize symbol
        symbol = self.normalize_symbol(symbol)
        
        # If exchange specified, check exchange-specific list
        if exchange:
            if exchange not in self._symbol_cache:
                await self.load_symbols_for_exchange(exchange)
            
            return symbol in self._symbol_cache[exchange]
        
        # Otherwise, check if format is valid
        return "/" in symbol and len(symbol.split("/")) == 2
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to universal format.
        
        Args:
            symbol: Symbol in any format
            
        Returns:
            Symbol in universal format (BASE/QUOTE)
            
        Example:
            normalize_symbol("btc/usdt") -> "BTC/USDT"
            normalize_symbol("BTC-USDT") -> "BTC/USDT"
            normalize_symbol("BTCUSDT") -> "BTC/USDT" (if recognizable)
        """
        # Uppercase
        symbol = symbol.upper()
        
        # Replace separators with /
        symbol = symbol.replace("-", "/").replace("_", "/")
        
        # If no separator, try to split by common quotes
        if "/" not in symbol:
            for quote in self.common_quotes:
                if symbol.endswith(quote) and symbol != quote:
                    base = symbol[:-len(quote)]
                    return f"{base}/{quote}"
        
        return symbol
    
    def to_binance_format(self, symbol: str) -> str:
        """
        Convert to Binance format.
        
        Args:
            symbol: Universal format (BTC/USDT)
            
        Returns:
            Binance format (BTCUSDT)
        """
        return symbol.replace("/", "")
    
    def to_polygon_format(self, symbol: str) -> str:
        """
        Convert to Polygon.io format.
        
        Args:
            symbol: Universal format (BTC/USDT)
            
        Returns:
            Polygon format (BTC-USD or X:BTCUSD)
        """
        # Replace USDT with USD for crypto
        symbol = symbol.replace("/USDT", "-USD")
        
        # For crypto pairs, add X: prefix
        if "-USD" in symbol or "-" in symbol:
            base = symbol.split("-")[0]
            # Check if it's a crypto symbol (3-5 chars)
            if 2 <= len(base) <= 5:
                return f"X:{symbol.replace('-', '')}"
        
        return symbol.replace("/", "-")
    
    def to_universal_format(self, symbol: str, exchange: Exchange) -> str:
        """
        Convert exchange-specific format to universal.
        
        Args:
            symbol: Exchange-specific format
            exchange: Which exchange format this is
            
        Returns:
            Universal format (BASE/QUOTE)
        """
        if exchange == Exchange.BINANCE:
            # BTCUSDT -> BTC/USDT
            return self.normalize_symbol(symbol)
        
        elif exchange == Exchange.POLYGON:
            # X:BTCUSD -> BTC/USD or BTC-USD -> BTC/USD
            symbol = symbol.replace("X:", "").replace("-", "/")
            # Convert USD back to USDT for crypto
            if "/USD" in symbol:
                symbol = symbol.replace("/USD", "/USDT")
            return symbol
        
        else:
            return self.normalize_symbol(symbol)
    
    def split_symbol(self, symbol: str) -> tuple:
        """
        Split symbol into base and quote.
        
        Args:
            symbol: Symbol in universal format
            
        Returns:
            Tuple of (base, quote)
            
        Example:
            split_symbol("BTC/USDT") -> ("BTC", "USDT")
        """
        if "/" in symbol:
            parts = symbol.split("/")
            return (parts[0], parts[1])
        
        # Try to split by common quotes
        for quote in self.common_quotes:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return (base, quote)
        
        raise ValueError(f"Cannot split symbol: {symbol}")
    
    async def get_supported_symbols(
        self,
        exchange: Optional[Exchange] = None
    ) -> List[str]:
        """
        Get list of supported symbols.
        
        Args:
            exchange: Specific exchange (optional)
            
        Returns:
            List of symbols in universal format
        """
        if exchange:
            if exchange not in self._symbol_cache:
                await self.load_symbols_for_exchange(exchange)
            return sorted(list(self._symbol_cache[exchange]))
        
        # Return all symbols
        all_symbols = set()
        for symbols in self._symbol_cache.values():
            all_symbols.update(symbols)
        
        return sorted(list(all_symbols))


# Global instance
_symbol_service = None


async def get_symbol_service(db: AsyncIOMotorDatabase) -> SymbolService:
    """
    Get global symbol service instance.
    
    Args:
        db: Database instance
        
    Returns:
        Symbol service
    """
    global _symbol_service
    
    if _symbol_service is None:
        _symbol_service = SymbolService(db)
    
    return _symbol_service

