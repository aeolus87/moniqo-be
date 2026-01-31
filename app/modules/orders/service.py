"""
Order Service

Business logic for order management.
Uses repositories for data access - no direct database access.
Handles Real vs Demo order placement via context switching.
"""

from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone

from app.domain.models.order import Order, OrderStatus, OrderSide, OrderType, TimeInForce
from app.modules.orders.repository import OrderRepository
from app.infrastructure.exchanges.factory import WalletFactory
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OrderService:
    """
    Order Service
    
    Handles order business logic:
    - Order creation
    - Status updates
    - Fill processing
    - Exchange order placement
    
    **Context Switching:**
    The service uses `db_provider.get_db()` which automatically routes to the
    correct database (real/demo) based on the trading mode context set by middleware.
    No explicit mode checking needed - the context handles it.
    """
    
    def __init__(self, repository: OrderRepository, wallet_factory: WalletFactory):
        """
        Initialize order service.
        
        Args:
            repository: Order repository instance
            wallet_factory: Wallet factory instance
        """
        self.repository = repository
        self.wallet_factory = wallet_factory
    
    async def create_order(
        self,
        user_id: str,
        user_wallet_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
        flow_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Order:
        """
        Create a new order and place it on the exchange.
        
        **Context Switching Moment:**
        - Middleware has already set trading mode context based on wallet_id
        - Repository.save() automatically routes to correct database (real/demo)
        - place_order_on_exchange() uses db_provider.get_db() which reads context
        - Wallet factory loads wallet from correct database
        - Wallet instance (DemoWallet vs RealWallet) handles exchange call
        
        Args:
            user_id: User ID
            user_wallet_id: User wallet ID
            symbol: Trading pair (e.g., "BTC/USDT")
            side: Order side (BUY/SELL)
            order_type: Order type (MARKET/LIMIT/etc)
            quantity: Order quantity
            price: Limit price (required for limit orders)
            stop_price: Stop price (for stop orders)
            time_in_force: Time in force
            flow_id: Optional flow ID
            metadata: Optional metadata
            
        Returns:
            Created Order
            
        Raises:
            ValueError: If validation fails
        """
        # Validate price for limit orders
        if order_type in [OrderType.LIMIT, OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
            if price is None:
                raise ValueError("Price is required for limit/stop orders")
        
        # Validate stop price for stop orders
        if order_type in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
            if stop_price is None:
                raise ValueError("Stop price is required for stop orders")
        
        # Create order domain model
        order = Order(
            user_id=user_id,
            user_wallet_id=user_wallet_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            requested_amount=quantity,
            limit_price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            flow_id=flow_id,
            metadata=metadata or {},
            status=OrderStatus.PENDING,
            remaining_amount=quantity
        )
        
        # Save to database via repository
        # Repository automatically routes to correct database (real/demo) based on context
        order = await self.repository.save(order)
        
        logger.info(f"Order {order.id} created for user {user_id}")
        
        # Place order on exchange
        await self.place_order_on_exchange(order)
        
        return order
    
    async def place_order_on_exchange(self, order: Order) -> None:
        """
        Place order on exchange using wallet.
        
        **The Context Switching Moment:**
        - db_provider.get_db() reads trading mode context (set by middleware)
        - Returns correct database instance (real or demo)
        - Wallet factory loads wallet from that database
        - Wallet instance handles demo vs real internally:
          * DemoWallet: Simulates order execution
          * RealWallet: Calls actual exchange API
        
        Args:
            order: Order to place
        """
        # Get correct database based on context (already set by middleware)
        from app.core.database import db_provider
        db = db_provider.get_db()  # Automatically real or demo based on context
        
        try:
            # Get wallet instance (factory loads from correct DB)
            wallet = await self.wallet_factory.create_wallet_from_db(
                db=db,
                user_wallet_id=str(order.user_wallet_id)
            )
            
            # Place order (wallet handles demo vs real internally)
            order_result = await wallet.place_order(
                symbol=order.symbol,
                side=order.side.value,  # Convert enum to string
                order_type=order.order_type.value,
                quantity=order.requested_amount,
                price=order.limit_price,
                stop_price=order.stop_price,
                time_in_force=order.time_in_force.value,
            )
            
            # Update order status based on result
            if order_result.get("success", True):
                # Update order with execution details
                order.external_order_id = order_result.get("order_id")
                order.submitted_at = datetime.now(timezone.utc)
                
                filled_quantity = Decimal(str(order_result.get("filled_quantity", 0)))
                if filled_quantity > 0:
                    # Order was filled (fully or partially)
                    order.filled_amount = filled_quantity
                    order.remaining_amount = order.requested_amount - filled_quantity
                    order.average_fill_price = Decimal(str(order_result.get("average_price", order_result.get("price", 0))))
                    order.total_fees = Decimal(str(order_result.get("fee", 0)))
                    order.first_fill_at = datetime.now(timezone.utc)
                    order.last_fill_at = datetime.now(timezone.utc)
                    
                    if filled_quantity >= order.requested_amount:
                        order.update_status(OrderStatus.FILLED, "Order filled completely")
                    else:
                        order.update_status(OrderStatus.PARTIALLY_FILLED, "Order partially filled")
                else:
                    # Order placed but not filled yet
                    order.update_status(OrderStatus.OPEN, "Order placed on exchange")
            else:
                # Order rejected
                order.update_status(
                    OrderStatus.REJECTED,
                    order_result.get("error", "Order placement failed")
                )
            
            # Save updated order
            order = await self.repository.save(order)
            
            logger.info(f"Order {order.id} placed on exchange: status={order.status.value}")
            
        except Exception as e:
            logger.error(f"Failed to place order {order.id} on exchange: {e}")
            order.update_status(OrderStatus.FAILED, f"Exchange error: {str(e)}")
            await self.repository.save(order)
            raise
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order or None if not found
        """
        return await self.repository.find_by_id(order_id)
    
    async def get_user_orders(
        self,
        user_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        flow_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> list[Order]:
        """
        Get orders for a user.
        
        Args:
            user_id: User ID
            status: Optional status filter
            symbol: Optional symbol filter
            flow_id: Optional flow ID filter
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            
        Returns:
            List of orders
        """
        return await self.repository.find_by_user(
            user_id=user_id,
            status=status,
            symbol=symbol,
            flow_id=flow_id,
            skip=skip,
            limit=limit
        )
    
    async def update_order_status(
        self,
        order_id: str,
        new_status: OrderStatus,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Order:
        """
        Update order status.
        
        Args:
            order_id: Order ID
            new_status: New status
            reason: Reason for status change
            metadata: Additional metadata
            
        Returns:
            Updated order
            
        Raises:
            ValueError: If order not found
        """
        order = await self.repository.find_by_id(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        
        # Update status (domain logic)
        order.update_status(new_status, reason, metadata)
        
        # Save via repository
        order = await self.repository.save(order)
        
        logger.info(f"Order {order_id} status updated to {new_status.value}")
        
        return order
    
    async def add_fill(
        self,
        order_id: str,
        fill: dict
    ) -> Order:
        """
        Add a fill to an order.
        
        Args:
            order_id: Order ID
            fill: Fill dictionary with amount, price, fee, etc.
            
        Returns:
            Updated order
            
        Raises:
            ValueError: If order not found
        """
        order = await self.repository.find_by_id(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        
        # Add fill (domain logic)
        order.add_fill(fill)
        
        # Save via repository
        order = await self.repository.save(order)
        
        logger.info(f"Fill added to order {order_id}: {fill.get('amount')} @ {fill.get('price')}")
        
        return order
    
    async def cancel_order(
        self,
        order_id: str,
        reason: Optional[str] = None
    ) -> Order:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID
            reason: Cancellation reason
            
        Returns:
            Updated order
            
        Raises:
            ValueError: If order not found
        """
        return await self.update_order_status(
            order_id=order_id,
            new_status=OrderStatus.CANCELLED,
            reason=reason or "Order cancelled by user"
        )