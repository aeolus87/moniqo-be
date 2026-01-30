"""
Market Data Service

Orchestrates market data providers and broadcasts updates via Socket.IO.
Also updates positions in real-time when prices change.

Author: Moniqo Team
"""

import asyncio
from typing import Optional, Set, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone
from socketio import AsyncServer

from app.infrastructure.market_data.base import MarketDataProvider, TickerUpdate, TradeUpdate
from app.core.database import db_provider
from app.core.context import TradingMode
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MarketDataService:
    """
    Market Data Service
    
    Bridges market data providers with Socket.IO for real-time updates.
    Also updates positions in real-time when prices change.
    
    Usage:
        provider = BinanceWebSocketClient()
        service = MarketDataService(provider, sio)
        await service.start()
        await service.subscribe_user("session_id", ["BTCUSDT"])
    """
    
    def __init__(self, provider: MarketDataProvider, sio: AsyncServer):
        """
        Initialize market data service.
        
        Args:
            provider: Any MarketDataProvider implementation
            sio: Socket.IO server instance
        """
        self.provider = provider
        self.sio = sio
        self._user_subscriptions: Dict[str, Set[str]] = {}  # sid -> symbols
        self._symbol_subscribers: Dict[str, Set[str]] = {}  # symbol -> sids
        self._position_symbols: Set[str] = set()  # symbols with open positions
        self._latest_prices: Dict[str, float] = {}  # symbol -> latest price cache
        self._started = False
    
    async def start(self) -> None:
        """
        Start the market data service.
        
        Uses DatabaseProvider to subscribe to positions from both demo and real databases.
        """
        if self._started:
            return
            
        logger.info("Starting market data service...")
        
        # Connect to provider
        await self.provider.connect()
        
        # Register callbacks
        self.provider.on_ticker(self._on_ticker_update)
        self.provider.on_trade(self._on_trade_update)
        
        self._started = True
        
        # Auto-subscribe to symbols with open positions from both databases
        await self._subscribe_position_symbols()
        
        logger.info("Market data service started")
    
    async def _subscribe_position_symbols(self) -> None:
        """
        Subscribe to WebSocket for all symbols with open positions.
        
        Checks both demo and real databases for positions.
        Handles permission errors gracefully - if one database fails, still checks the other.
        """
        symbols = set()
        
        # Check demo database (continue even if it fails)
        try:
            db_demo = db_provider.get_db_for_mode(TradingMode.DEMO)
            demo_cursor = db_demo["positions"].find(
                {"status": "open", "deleted_at": None},
                {"symbol": 1}
            )
            demo_docs = await demo_cursor.to_list(length=None)
            
            for doc in demo_docs:
                symbol = doc.get("symbol", "")
                if symbol:
                    normalized = symbol.replace("/", "").upper()
                    symbols.add(normalized)
        except Exception as e:
            logger.debug(f"Could not query demo database for positions (may be permission issue): {e}")
        
        # Check real database (continue even if it fails)
        try:
            db_real = db_provider.get_db_for_mode(TradingMode.REAL)
            real_cursor = db_real["positions"].find(
                {"status": "open", "deleted_at": None},
                {"symbol": 1}
            )
            real_docs = await real_cursor.to_list(length=None)
            
            for doc in real_docs:
                symbol = doc.get("symbol", "")
                if symbol:
                    normalized = symbol.replace("/", "").upper()
                    symbols.add(normalized)
        except Exception as e:
            logger.debug(f"Could not query real database for positions (may be permission issue): {e}")
        
        # Subscribe to symbols if any were found
        if symbols:
            try:
                self._position_symbols = symbols
                await self.provider.subscribe(list(symbols))
                logger.info(f"Auto-subscribed to position symbols from both databases: {symbols}")
            except Exception as e:
                logger.warning(f"Failed to subscribe to position symbols on provider: {e}")
        else:
            logger.debug("No open positions found in either database")
    
    async def stop(self) -> None:
        """Stop the market data service."""
        if not self._started:
            return
            
        logger.info("Stopping market data service...")
        
        await self.provider.disconnect()
        self._user_subscriptions.clear()
        self._symbol_subscribers.clear()
        
        self._started = False
        logger.info("Market data service stopped")
    
    async def subscribe_user(self, sid: str, symbols: list[str]) -> None:
        """
        Subscribe a user session to market data for symbols.
        
        Args:
            sid: Socket.IO session ID
            symbols: List of symbols to subscribe
        """
        # Normalize symbols
        normalized = [s.upper().replace("/", "") for s in symbols]
        
        # Track user subscriptions
        if sid not in self._user_subscriptions:
            self._user_subscriptions[sid] = set()
        
        new_symbols = []
        for symbol in normalized:
            self._user_subscriptions[sid].add(symbol)
            
            # Track symbol subscribers
            if symbol not in self._symbol_subscribers:
                self._symbol_subscribers[symbol] = set()
                new_symbols.append(symbol)
            
            self._symbol_subscribers[symbol].add(sid)
        
        # Join market room for this session
        await self.sio.enter_room(sid, "market")
        
        # Subscribe to new symbols on provider
        if new_symbols and self._started:
            await self.provider.subscribe(new_symbols)
            logger.info(f"User {sid} subscribed to: {normalized}")
    
    async def unsubscribe_user(self, sid: str, symbols: Optional[list[str]] = None) -> None:
        """
        Unsubscribe a user session from market data.
        
        Args:
            sid: Socket.IO session ID
            symbols: Symbols to unsubscribe (None = all)
        """
        if sid not in self._user_subscriptions:
            return
        
        # Determine which symbols to unsubscribe
        if symbols is None:
            symbols_to_remove = list(self._user_subscriptions[sid])
        else:
            symbols_to_remove = [s.upper().replace("/", "") for s in symbols]
        
        orphaned_symbols = []
        
        for symbol in symbols_to_remove:
            self._user_subscriptions[sid].discard(symbol)
            
            if symbol in self._symbol_subscribers:
                self._symbol_subscribers[symbol].discard(sid)
                
                # If no more subscribers, unsubscribe from provider
                if not self._symbol_subscribers[symbol]:
                    del self._symbol_subscribers[symbol]
                    orphaned_symbols.append(symbol)
        
        # Clean up empty user subscription set
        if not self._user_subscriptions[sid]:
            del self._user_subscriptions[sid]
            await self.sio.leave_room(sid, "market")
        
        # Unsubscribe orphaned symbols from provider
        if orphaned_symbols and self._started:
            await self.provider.unsubscribe(orphaned_symbols)
            logger.info(f"Unsubscribed from orphaned symbols: {orphaned_symbols}")
    
    async def handle_disconnect(self, sid: str) -> None:
        """
        Handle user disconnect - clean up subscriptions.
        
        Args:
            sid: Socket.IO session ID
        """
        await self.unsubscribe_user(sid)
    
    async def _on_ticker_update(self, ticker: TickerUpdate) -> None:
        """
        Handle ticker update from provider.
        Broadcasts to all subscribers and updates positions in real-time.
        """
        symbol = ticker.symbol
        
        # Cache latest price
        self._latest_prices[symbol] = ticker.price
        
        # Update positions with this symbol in real-time
        if symbol in self._position_symbols:
            asyncio.create_task(self._update_positions_price(symbol, ticker.price))
        
        # Get subscribers for this symbol
        subscribers = self._symbol_subscribers.get(symbol, set())
        
        if not subscribers:
            return
        
        # Emit to market room (all market subscribers)
        try:
            await self.sio.emit(
                "market_update",
                ticker.to_dict(),
                room="market"
            )
        except Exception as e:
            logger.error(f"Failed to emit market update: {e}")
    
    async def _update_positions_price(self, symbol: str, price: float) -> None:
        """
        Update all open positions for a symbol with the new price.
        
        Updates positions in both demo and real databases.
        """
        try:
            from app.modules.positions.models import PositionSide
            
            now = datetime.now(timezone.utc)
            current_price = Decimal(str(price))
            
            # Find all open positions for this symbol (support both formats)
            symbol_variants = [symbol, f"{symbol[:3]}/{symbol[3:]}"]  # BTCUSDT and BTC/USDT
            
            # Update positions in demo database
            await self._update_positions_in_database(TradingMode.DEMO, symbol_variants, current_price, now)
            
            # Update positions in real database
            await self._update_positions_in_database(TradingMode.REAL, symbol_variants, current_price, now)
            
        except Exception as e:
            logger.warning(f"Error updating positions for {symbol}: {e}")
    
    async def _update_positions_in_database(
        self,
        mode: TradingMode,
        symbol_variants: list[str],
        current_price: Decimal,
        now: datetime
    ) -> None:
        """Update positions in a specific database."""
        try:
            from app.modules.positions.models import PositionSide
            
            db = db_provider.get_db_for_mode(mode)
            
            cursor = db["positions"].find({
                "symbol": {"$in": symbol_variants},
                "status": "open",
                "deleted_at": None
            })
            
            async for doc in cursor:
                try:
                    entry = doc.get("entry", {})
                    entry_price = Decimal(str(entry.get("price", 0)))
                    entry_amount = Decimal(str(entry.get("amount", 0)))
                    
                    if entry_price == 0 or entry_amount == 0:
                        continue
                    
                    # Calculate P&L
                    if doc.get("side") == PositionSide.LONG.value:
                        unrealized_pnl = (current_price - entry_price) * entry_amount
                    else:
                        unrealized_pnl = (entry_price - current_price) * entry_amount
                    
                    unrealized_pnl_percent = (unrealized_pnl / (entry_price * entry_amount)) * 100
                    
                    # Determine risk level
                    pnl_pct = float(unrealized_pnl_percent)
                    if pnl_pct <= -10:
                        risk_level = "critical"
                    elif pnl_pct <= -5:
                        risk_level = "high"
                    elif pnl_pct < 0:
                        risk_level = "medium"
                    else:
                        risk_level = "low"
                    
                    # Update position in DB
                    current_update = {
                        "price": float(current_price),
                        "value": float(entry_amount * current_price),
                        "unrealized_pnl": float(unrealized_pnl),
                        "unrealized_pnl_percent": float(unrealized_pnl_percent),
                        "risk_level": risk_level,
                        "updated_at": now,
                    }
                    
                    await db["positions"].update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"current": current_update, "updated_at": now}}
                    )
                    
                    # Emit socket update
                    user_id = doc.get("user_id")
                    if user_id:
                        risk = doc.get("risk_management", {})
                        update_data = {
                            "id": str(doc["_id"]),
                            "symbol": doc.get("symbol"),
                            "side": doc.get("side"),
                            "entry_price": float(entry_price),
                            "current_price": float(current_price),
                            "quantity": float(entry_amount),
                            "unrealized_pnl": float(unrealized_pnl),
                            "realized_pnl": 0,
                            "status": "open",
                            "stop_loss": float(risk.get("stop_loss") or 0) or None,
                            "take_profit": float(risk.get("take_profit") or 0) or None,
                            "updated_at": now.isoformat(),
                        }
                        room = f"positions:{str(user_id)}"
                        await self.sio.emit("position_update", update_data, room=room)
                        
                except Exception as e:
                    logger.debug(f"Error updating position {doc.get('_id')} in {mode.value} database: {e}")
                    
        except Exception as e:
            logger.warning(f"Error updating positions in {mode.value} database: {e}")
    
    async def _on_trade_update(self, trade: TradeUpdate) -> None:
        """
        Handle trade update from provider.
        Broadcasts to all subscribers of this symbol.
        """
        symbol = trade.symbol
        subscribers = self._symbol_subscribers.get(symbol, set())
        
        if not subscribers:
            return
        
        try:
            await self.sio.emit(
                "trade_update",
                trade.to_dict(),
                room="market"
            )
        except Exception as e:
            logger.error(f"Failed to emit trade update: {e}")
    
    async def refresh_position_symbols(self) -> None:
        """Refresh the list of symbols with open positions and subscribe to them."""
        await self._subscribe_position_symbols()
    
    async def add_position_symbol(self, symbol: str) -> None:
        """Add a symbol to track for position updates (called when position opens)."""
        normalized = symbol.replace("/", "").upper()
        if normalized not in self._position_symbols:
            self._position_symbols.add(normalized)
            if self._started:
                await self.provider.subscribe([normalized])
                logger.info(f"Added position symbol: {normalized}")
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the latest cached price for a symbol."""
        normalized = symbol.replace("/", "").upper()
        return self._latest_prices.get(normalized)
    
    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._started
    
    @property
    def active_symbols(self) -> list[str]:
        """Get list of symbols with active subscribers."""
        return list(self._symbol_subscribers.keys())
    
    @property
    def position_symbols(self) -> list[str]:
        """Get list of symbols being tracked for positions."""
        return list(self._position_symbols)
    
    @property
    def subscriber_count(self) -> int:
        """Get total number of subscribed users."""
        return len(self._user_subscriptions)


# Global service instance
_market_data_service: Optional[MarketDataService] = None


def get_market_data_service() -> Optional[MarketDataService]:
    """Get the global market data service instance."""
    return _market_data_service


def set_market_data_service(service: MarketDataService) -> None:
    """Set the global market data service instance."""
    global _market_data_service
    _market_data_service = service
