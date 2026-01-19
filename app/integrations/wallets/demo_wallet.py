"""
DemoWallet - Simulated Trading Wallet

Paper trading implementation that simulates a real exchange without
using real money or making actual API calls.

Features:
- Simulated order execution with market prices
- Fee simulation (0.1% default)
- Slippage simulation (0.01% default)
- Balance tracking (cash + assets)
- Order book simulation (limit orders)
- Position tracking
- MongoDB persistence

Perfect for testing strategies risk-free!

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import uuid
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.integrations.wallets.base import (
    BaseWallet,
    OrderSide,
    OrderType,
    OrderStatus,
    TimeInForce,
    WalletError,
    InsufficientFundsError,
    InvalidOrderError,
    OrderNotFoundError,
    SymbolNotSupportedError
)
from app.config.database import get_database
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DemoWallet(BaseWallet):
    """
    Demo/Paper Trading Wallet
    
    Simulates trading without real money. Uses real market prices
    from Polygon.io for realistic simulation.
    
    Usage:
        wallet = DemoWallet(
            wallet_id="demo-wallet-001",
            user_wallet_id="user_wallet_123",
            credentials={},  # No credentials needed
            initial_balance={"USDT": 10000.0}
        )
        
        # Check balance
        balance = await wallet.get_balance("USDT")
        
        # Place order
        result = await wallet.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1")
        )
    """
    
    def __init__(
        self,
        wallet_id: str,
        user_wallet_id: str,
        credentials: Dict[str, str],
        initial_balance: Optional[Dict[str, float]] = None,
        fee_rate: float = 0.001,  # 0.1%
        slippage_rate: float = 0.0001,  # 0.01%
        **kwargs
    ):
        """
        Initialize demo wallet.
        
        Args:
            wallet_id: Wallet provider ID
            user_wallet_id: User wallet instance ID
            credentials: Empty dict (no credentials needed)
            initial_balance: Starting balances (default: {"USDT": 10000})
            fee_rate: Fee percentage (default: 0.1%)
            slippage_rate: Slippage percentage (default: 0.01%)
        """
        super().__init__(wallet_id, user_wallet_id, credentials, **kwargs)
        
        # Configuration
        self.fee_rate = Decimal(str(fee_rate))
        self.slippage_rate = Decimal(str(slippage_rate))
        
        # Initial balance
        self.initial_balance = initial_balance or {"USDT": 10000.0}
        
        # Database
        self.db: Optional[AsyncIOMotorDatabase] = None
        
        # In-memory state (will be synced with DB)
        self._state_loaded = False
    
    async def _ensure_db(self):
        """Ensure database connection"""
        if self.db is None:
            self.db = get_database()
    
    async def _load_state(self) -> Dict[str, Any]:
        """
        Load wallet state from MongoDB.
        
        Returns state dict or creates new state if doesn't exist.
        """
        await self._ensure_db()
        
        state = await self.db.demo_wallet_state.find_one({
            "user_wallet_id": self.user_wallet_id
        })
        
        if state:
            logger.debug(f"Loaded demo wallet state for {self.user_wallet_id}")
            return state
        
        # Create initial state
        logger.info(f"Creating new demo wallet state for {self.user_wallet_id}")
        
        initial_state = {
            "user_wallet_id": self.user_wallet_id,
            "cash_balances": self.initial_balance.copy(),
            "asset_balances": {},
            "locked_balances": {},
            "open_orders": [],
            "transaction_history": [],
            "starting_balance": sum(self.initial_balance.values()),
            "total_realized_pnl": 0.0,
            "total_fees_paid": 0.0,
            "total_trades": 0,
            "fee_rate": float(self.fee_rate),
            "slippage_rate": float(self.slippage_rate),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = await self.db.demo_wallet_state.insert_one(initial_state)
        initial_state["_id"] = result.inserted_id
        
        return initial_state
    
    async def _save_state(self, state: Dict[str, Any]):
        """Save wallet state to MongoDB"""
        await self._ensure_db()
        
        state["updated_at"] = datetime.now(timezone.utc)
        
        await self.db.demo_wallet_state.update_one(
            {"user_wallet_id": self.user_wallet_id},
            {"$set": state}
        )
        
        logger.debug(f"Saved demo wallet state for {self.user_wallet_id}")
    
    # ==================== BALANCE OPERATIONS ====================
    
    async def get_balance(self, asset: str) -> Decimal:
        """Get available balance for asset"""
        state = await self._load_state()
        
        # Check cash balances (USDT, USD, etc.)
        if asset in state["cash_balances"]:
            return Decimal(str(state["cash_balances"][asset]))
        
        # Check asset balances (BTC, ETH, etc.)
        if asset in state["asset_balances"]:
            return Decimal(str(state["asset_balances"][asset]))
        
        return Decimal("0")
    
    async def get_all_balances(self) -> Dict[str, Decimal]:
        """Get all non-zero balances"""
        state = await self._load_state()
        
        balances = {}
        
        # Add cash balances
        for asset, amount in state["cash_balances"].items():
            if amount > 0:
                balances[asset] = Decimal(str(amount))
        
        # Add asset balances
        for asset, amount in state["asset_balances"].items():
            if amount > 0:
                balances[asset] = Decimal(str(amount))
        
        return balances
    
    async def _update_balance(
        self,
        asset: str,
        amount: Decimal,
        is_cash: bool = False
    ):
        """
        Update balance (internal method).
        
        Args:
            asset: Asset symbol
            amount: Amount to add (negative to subtract)
            is_cash: Is this a cash currency (USDT, USD)
        """
        state = await self._load_state()
        
        balance_key = "cash_balances" if is_cash else "asset_balances"
        
        current = Decimal(str(state[balance_key].get(asset, 0)))
        new_balance = current + amount
        
        if new_balance < 0:
            raise InsufficientFundsError(
                f"Insufficient {asset} balance. "
                f"Available: {current}, Required: {abs(amount)}"
            )
        
        state[balance_key][asset] = float(new_balance)
        
        await self._save_state(state)
    
    # ==================== ORDER OPERATIONS ====================
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Place simulated order.
        
        Market orders: Execute immediately at current price + slippage
        Limit orders: Store in open_orders, wait for price trigger
        Stop orders: Store in open_orders, convert to market when triggered
        """
        # Validate symbol format
        if "/" not in symbol:
            raise InvalidOrderError(
                f"Invalid symbol format: {symbol}. Expected format: BTC/USDT"
            )
        
        base_asset, quote_asset = symbol.split("/")
        
        # Generate order ID
        order_id = f"demo_{uuid.uuid4().hex[:12]}"
        client_order_id = f"client_{uuid.uuid4().hex[:8]}"
        
        # Validate order parameters
        if order_type in [OrderType.LIMIT, OrderType.STOP_LOSS_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
            if price is None:
                raise InvalidOrderError(
                    f"{order_type} orders require a limit price"
                )
        
        if order_type in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
            if stop_price is None:
                raise InvalidOrderError(
                    f"{order_type} orders require a stop price"
                )
        
        # Create order record
        order = {
            "order_id": order_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "side": side.value,
            "type": order_type.value,
            "quantity": float(quantity),
            "filled_quantity": 0.0,
            "remaining_quantity": float(quantity),
            "price": float(price) if price else None,
            "stop_price": float(stop_price) if stop_price else None,
            "time_in_force": time_in_force.value,
            "status": OrderStatus.PENDING.value,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Execute based on order type
        if order_type == OrderType.MARKET:
            # Execute immediately
            result = await self._execute_market_order(
                order,
                base_asset,
                quote_asset
            )
            return result
        
        elif order_type in [OrderType.LIMIT, OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
            # Add to open orders (will be executed by monitor)
            result = await self._add_open_order(order)
            return result
        
        else:
            raise InvalidOrderError(
                f"Order type {order_type} not supported in demo wallet"
            )
    
    async def _execute_market_order(
        self,
        order: Dict[str, Any],
        base_asset: str,
        quote_asset: str
    ) -> Dict[str, Any]:
        """
        Execute market order immediately.
        
        Steps:
        1. Get current market price (from WebSocket manager or Polygon.io)
        2. Apply slippage
        3. Calculate total cost (including fees)
        4. Check balance
        5. Update balances
        6. Record transaction
        """
        # TODO: Get real market price from WebSocket manager
        # For now, use placeholder price
        market_price = await self._get_market_price_placeholder(order["symbol"])
        
        if market_price is None:
            raise WalletError(f"Cannot get market price for {order['symbol']}")
        
        # Apply slippage
        if order["side"] == "buy":
            # Buying: price goes up (worse for buyer)
            execution_price = market_price * (Decimal("1") + self.slippage_rate)
        else:
            # Selling: price goes down (worse for seller)
            execution_price = market_price * (Decimal("1") - self.slippage_rate)
        
        quantity = Decimal(str(order["quantity"]))
        
        # Calculate costs
        notional_value = quantity * execution_price
        fee = notional_value * self.fee_rate
        
        if order["side"] == "buy":
            total_cost = notional_value + fee
            
            # Check quote balance (USDT)
            quote_balance = await self.get_balance(quote_asset)
            if quote_balance < total_cost:
                raise InsufficientFundsError(
                    f"Insufficient {quote_asset} balance. "
                    f"Required: {total_cost}, Available: {quote_balance}"
                )
            
            # Update balances
            await self._update_balance(quote_asset, -total_cost, is_cash=True)
            await self._update_balance(base_asset, quantity, is_cash=False)
            
        else:  # sell
            # Check base balance (BTC)
            base_balance = await self.get_balance(base_asset)
            if base_balance < quantity:
                raise InsufficientFundsError(
                    f"Insufficient {base_asset} balance. "
                    f"Required: {quantity}, Available: {base_balance}"
                )
            
            total_received = notional_value - fee
            
            # Update balances
            await self._update_balance(base_asset, -quantity, is_cash=False)
            await self._update_balance(quote_asset, total_received, is_cash=True)
        
        # Update order status
        order["status"] = OrderStatus.FILLED.value
        order["filled_quantity"] = float(quantity)
        order["remaining_quantity"] = 0.0
        order["average_price"] = float(execution_price)
        order["updated_at"] = datetime.now(timezone.utc)
        
        # Record transaction
        await self._record_transaction({
            "order_id": order["order_id"],
            "symbol": order["symbol"],
            "side": order["side"],
            "quantity": float(quantity),
            "price": float(execution_price),
            "fee": float(fee),
            "fee_currency": quote_asset,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Update statistics
        state = await self._load_state()
        state["total_trades"] += 1
        state["total_fees_paid"] += float(fee)
        await self._save_state(state)
        
        logger.info(
            f"Executed market order: {order['side']} {quantity} {base_asset} "
            f"@ ${execution_price} (fee: ${fee})"
        )
        
        return {
            "success": True,
            "order_id": order["order_id"],
            "client_order_id": order["client_order_id"],
            "status": OrderStatus.FILLED,
            "filled_quantity": quantity,
            "average_price": execution_price,
            "fee": fee,
            "fee_currency": quote_asset,
            "timestamp": datetime.now(timezone.utc)
        }
    
    async def _add_open_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Add order to open orders list"""
        state = await self._load_state()
        
        order["status"] = OrderStatus.OPEN.value
        state["open_orders"].append(order)
        
        await self._save_state(state)
        
        logger.info(
            f"Added open order: {order['type']} {order['side']} "
            f"{order['quantity']} {order['symbol']}"
        )
        
        return {
            "success": True,
            "order_id": order["order_id"],
            "client_order_id": order["client_order_id"],
            "status": OrderStatus.OPEN,
            "filled_quantity": Decimal("0"),
            "timestamp": datetime.now(timezone.utc)
        }
    
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel open order"""
        state = await self._load_state()
        
        # Find order
        order = None
        for i, o in enumerate(state["open_orders"]):
            if o["order_id"] == order_id:
                order = state["open_orders"].pop(i)
                break
        
        if not order:
            raise OrderNotFoundError(
                f"Order {order_id} not found in open orders"
            )
        
        # Update status
        order["status"] = OrderStatus.CANCELLED.value
        order["updated_at"] = datetime.now(timezone.utc)
        
        await self._save_state(state)
        
        logger.info(f"Cancelled order: {order_id}")
        
        return {
            "success": True,
            "order_id": order_id,
            "status": OrderStatus.CANCELLED,
            "message": "Order cancelled successfully"
        }
    
    async def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order status"""
        state = await self._load_state()
        
        # Search open orders
        for order in state["open_orders"]:
            if order["order_id"] == order_id:
                return self._format_order_status(order)
        
        # Search transaction history
        for tx in state["transaction_history"]:
            if tx.get("order_id") == order_id:
                return {
                    "order_id": order_id,
                    "status": OrderStatus.FILLED,
                    "symbol": tx["symbol"],
                    "side": OrderSide(tx["side"]),
                    "type": OrderType.MARKET,  # Assume market (simplified)
                    "quantity": Decimal(str(tx["quantity"])),
                    "filled_quantity": Decimal(str(tx["quantity"])),
                    "remaining_quantity": Decimal("0"),
                    "average_price": Decimal(str(tx["price"])),
                    "created_at": tx["timestamp"],
                    "updated_at": tx["timestamp"]
                }
        
        raise OrderNotFoundError(f"Order {order_id} not found")
    
    def _format_order_status(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Format order dict to standard status format"""
        return {
            "order_id": order["order_id"],
            "status": OrderStatus(order["status"]),
            "symbol": order["symbol"],
            "side": OrderSide(order["side"]),
            "type": OrderType(order["type"]),
            "quantity": Decimal(str(order["quantity"])),
            "filled_quantity": Decimal(str(order["filled_quantity"])),
            "remaining_quantity": Decimal(str(order["remaining_quantity"])),
            "average_price": Decimal(str(order.get("average_price", 0))) if order.get("average_price") else None,
            "created_at": order["created_at"],
            "updated_at": order["updated_at"]
        }
    
    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current position for symbol.
        
        Demo wallet doesn't track positions explicitly.
        Returns None (positions tracked separately in positions collection).
        """
        return None
    
    # ==================== MARKET DATA ====================
    
    async def get_market_price(self, symbol: str) -> Decimal:
        """Get current market price"""
        # TODO: Integrate with WebSocket manager / Polygon.io
        price = await self._get_market_price_placeholder(symbol)
        if price is None:
            raise SymbolNotSupportedError(
                f"Cannot get price for {symbol}. Symbol may not be supported."
            )
        return price
    
    async def _get_market_price_placeholder(self, symbol: str) -> Optional[Decimal]:
        """
        Placeholder for market price.
        
        TODO: Replace with actual Polygon.io integration.
        """
        # Placeholder prices for testing
        placeholder_prices = {
            "BTC/USDT": Decimal("50000.00"),
            "ETH/USDT": Decimal("3000.00"),
            "BNB/USDT": Decimal("400.00")
        }
        
        return placeholder_prices.get(symbol)
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker data"""
        price = await self.get_market_price(symbol)
        
        return {
            "symbol": symbol,
            "bid": price * Decimal("0.9999"),
            "ask": price * Decimal("1.0001"),
            "last": price,
            "high_24h": price * Decimal("1.05"),
            "low_24h": price * Decimal("0.95"),
            "volume_24h": Decimal("1000000"),
            "change_24h_percent": Decimal("2.5"),
            "timestamp": datetime.now(timezone.utc)
        }
    
    # ==================== SYMBOL FORMATTING ====================
    
    def format_symbol(self, symbol: str) -> str:
        """Demo wallet uses universal format (BTC/USDT)"""
        return symbol
    
    def parse_symbol(self, exchange_symbol: str) -> str:
        """Demo wallet uses universal format"""
        return exchange_symbol
    
    def format_price(self, symbol: str, price: Decimal) -> Decimal:
        """Format price to 2 decimal places (default)"""
        return price.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    
    def format_quantity(self, symbol: str, quantity: Decimal) -> Decimal:
        """Format quantity to 8 decimal places (crypto standard)"""
        return quantity.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    
    # ==================== CONNECTION ====================
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection (always succeeds for demo wallet)"""
        await self._ensure_db()
        
        return {
            "success": True,
            "latency_ms": 0,  # Instant (no network)
            "server_time": datetime.now(timezone.utc),
            "message": "Demo wallet connected (simulation)"
        }
    
    async def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get exchange info"""
        return {
            "symbols": [
                {
                    "symbol": "BTC/USDT",
                    "base": "BTC",
                    "quote": "USDT",
                    "min_quantity": "0.00001",
                    "max_quantity": "9000",
                    "min_notional": "10.00"
                },
                {
                    "symbol": "ETH/USDT",
                    "base": "ETH",
                    "quote": "USDT",
                    "min_quantity": "0.0001",
                    "max_quantity": "90000",
                    "min_notional": "10.00"
                }
            ],
            "rate_limits": [],
            "server_time": datetime.now(timezone.utc)
        }
    
    # ==================== TRANSACTION HISTORY ====================
    
    async def _record_transaction(self, transaction: Dict[str, Any]):
        """Record transaction in history"""
        state = await self._load_state()
        state["transaction_history"].append(transaction)
        
        # Keep only last 1000 transactions (prevent unlimited growth)
        if len(state["transaction_history"]) > 1000:
            state["transaction_history"] = state["transaction_history"][-1000:]
        
        await self._save_state(state)
    
    async def get_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get trade history"""
        state = await self._load_state()
        
        transactions = state["transaction_history"]
        
        # Filter by symbol if provided
        if symbol:
            transactions = [
                tx for tx in transactions
                if tx["symbol"] == symbol
            ]
        
        # Limit results
        transactions = transactions[-limit:]
        
        return transactions

