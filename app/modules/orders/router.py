"""
Order Management Router

FastAPI endpoints for order management.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from decimal import Decimal
from bson import ObjectId

from app.core.dependencies import get_current_user
from app.config.database import get_database
from app.modules.orders.models import Order, OrderStatus, OrderSide, OrderType, TimeInForce
from app.modules.orders.schemas import (
    CreateOrderRequest,
    UpdateOrderRequest,
    CancelOrderRequest,
    OrderResponse,
    OrderListResponse,
    OrderCreateResponse,
    OrderCancelResponse
)
from app.integrations.wallets.factory import create_wallet_from_db
from app.services.order_monitor import get_order_monitor
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


# ==================== CREATE ORDER ====================

@router.post("/", response_model=OrderCreateResponse, status_code=201)
async def create_order(
    request: CreateOrderRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Create a new order.
    
    This endpoint creates an order and optionally places it on the exchange.
    
    **Order Types:**
    - `MARKET`: Execute immediately at market price
    - `LIMIT`: Execute at specified price or better
    - `STOP_LOSS`: Triggered when price hits stop price
    - `TAKE_PROFIT`: Triggered when price hits stop price
    
    **Required Fields:**
    - `symbol`: Trading pair (e.g., "BTC/USDT")
    - `side`: "buy" or "sell"
    - `order_type`: Order type
    - `quantity`: Order quantity (must be > 0)
    - `price`: Required for LIMIT/STOP orders
    - `stop_price`: Required for STOP orders
    """
    try:
        user_id = current_user["_id"]
        
        # Validate user_wallet_id belongs to user
        # TODO: Add validation
        
        # Create order in database
        order = Order(
            user_id=ObjectId(user_id) if isinstance(user_id, str) else user_id,
            user_wallet_id=ObjectId(request.user_wallet_id),
            symbol=request.symbol,
            side=OrderSide(request.side.value),
            order_type=OrderType(request.order_type.value),
            requested_amount=request.quantity,
            limit_price=request.price,
            stop_price=request.stop_price,
            time_in_force=TimeInForce(request.time_in_force.value),
            flow_id=ObjectId(request.flow_id) if request.flow_id else None,
            metadata=request.metadata,
            status=OrderStatus.PENDING
        )
        order.remaining_amount = order.requested_amount
        
        await order.insert()
        
        logger.info(f"Order {order.id} created for user {user_id}")
        
        # Place order on exchange/wallet
        try:
            wallet = await create_wallet_from_db(db, str(order.user_wallet_id))
            
            # Execute order immediately for MARKET orders, or prepare for LIMIT orders
            if order.order_type == OrderType.MARKET:
                order_result = await wallet.place_order(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.requested_amount,
                    price=order.limit_price,
                    stop_price=order.stop_price,
                    time_in_force=order.time_in_force,
                )
                
                if order_result.get("success", True):
                    # Update order with execution details
                    order.external_order_id = order_result.get("order_id")
                    order.submitted_at = datetime.now(timezone.utc)
                    
                    filled_quantity = order_result.get("filled_quantity") or Decimal("0")
                    if filled_quantity > 0:
                        order.filled_amount = filled_quantity
                        order.remaining_amount = order.requested_amount - filled_quantity
                        order.average_fill_price = Decimal(str(order_result.get("average_price", order_result.get("price", 0))))
                        order.total_fees = Decimal(str(order_result.get("fee", 0)))
                        order.first_fill_at = datetime.now(timezone.utc)
                        order.last_fill_at = datetime.now(timezone.utc)
                        
                        if filled_quantity >= order.requested_amount:
                            await order.update_status(OrderStatus.FILLED, "Order filled completely")
                        else:
                            await order.update_status(OrderStatus.PARTIALLY_FILLED, "Order partially filled")
                    else:
                        await order.update_status(OrderStatus.OPEN, "Order placed on exchange")
                else:
                    await order.update_status(OrderStatus.REJECTED, order_result.get("error", "Order placement failed"))
            else:
                # LIMIT/STOP orders - place but don't execute immediately
                order_result = await wallet.place_order(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.requested_amount,
                    price=order.limit_price,
                    stop_price=order.stop_price,
                    time_in_force=order.time_in_force,
                )
                
                if order_result.get("success", True):
                    order.external_order_id = order_result.get("order_id")
                    order.submitted_at = datetime.now(timezone.utc)
                    await order.update_status(OrderStatus.OPEN, "Limit order placed")
                else:
                    await order.update_status(OrderStatus.REJECTED, order_result.get("error", "Order placement failed"))
            
            await order.save()
        except Exception as e:
            logger.error(f"Failed to place order {order.id} on exchange: {str(e)}")
            await order.update_status(OrderStatus.FAILED, f"Order placement error: {str(e)}")
            await order.save()
        
        return OrderCreateResponse(
            success=True,
            order=OrderResponse(
                id=str(order.id),
                user_id=str(order.user_id),
                user_wallet_id=str(order.user_wallet_id),
                position_id=str(order.position_id) if order.position_id else None,
                flow_id=str(order.flow_id) if order.flow_id else None,
                symbol=order.symbol,
                side=order.side.value,
                order_type=order.order_type.value,
                time_in_force=order.time_in_force.value,
                status=order.status.value,
                requested_amount=order.requested_amount,
                filled_amount=order.filled_amount,
                remaining_amount=order.remaining_amount,
                limit_price=order.limit_price,
                stop_price=order.stop_price,
                average_fill_price=order.average_fill_price,
                total_fees=order.total_fees,
                total_fees_usd=order.total_fees_usd,
                external_order_id=order.external_order_id,
                fills=[],
                status_history=[
                    {
                        "status": h["status"],
                        "timestamp": h["timestamp"],
                        "reason": h.get("reason"),
                        "metadata": h.get("metadata")
                    }
                    for h in order.status_history
                ],
                created_at=order.created_at,
                submitted_at=order.submitted_at,
                first_fill_at=order.first_fill_at,
                last_fill_at=order.last_fill_at,
                closed_at=order.closed_at,
                metadata=order.metadata
            ),
            message="Order created successfully"
        )
    
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GET ORDER ====================

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get order by ID"""
    try:
        user_id = current_user["_id"]
        
        order = await Order.get(order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Verify order belongs to user
        if str(order.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return OrderResponse(
            id=str(order.id),
            user_id=str(order.user_id),
            user_wallet_id=str(order.user_wallet_id),
            position_id=str(order.position_id) if order.position_id else None,
            flow_id=str(order.flow_id) if order.flow_id else None,
            symbol=order.symbol,
            side=order.side.value,
            order_type=order.order_type.value,
            time_in_force=order.time_in_force.value,
            status=order.status.value,
            requested_amount=order.requested_amount,
            filled_amount=order.filled_amount,
            remaining_amount=order.remaining_amount,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            average_fill_price=order.average_fill_price,
            total_fees=order.total_fees,
            total_fees_usd=order.total_fees_usd,
            external_order_id=order.external_order_id,
            fills=[
                {
                    "fill_id": f["fill_id"],
                    "amount": Decimal(str(f["amount"])),
                    "price": Decimal(str(f["price"])),
                    "fee": Decimal(str(f.get("fee", 0))),
                    "fee_currency": f.get("fee_currency", "USDT"),
                    "timestamp": f.get("timestamp", datetime.now(timezone.utc)),
                    "trade_id": f.get("trade_id")
                }
                for f in order.fills
            ],
            status_history=[
                {
                    "status": h["status"],
                    "timestamp": h["timestamp"],
                    "reason": h.get("reason"),
                    "metadata": h.get("metadata")
                }
                for h in order.status_history
            ],
            created_at=order.created_at,
            submitted_at=order.submitted_at,
            first_fill_at=order.first_fill_at,
            last_fill_at=order.last_fill_at,
            closed_at=order.closed_at,
            metadata=order.metadata
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== LIST ORDERS ====================

@router.get("/", response_model=OrderListResponse)
async def list_orders(
    status: Optional[OrderStatus] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    page: Optional[int] = Query(None, ge=1, description="Page number"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Page size"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Limit (alternative to page_size)"),
    offset: Optional[int] = Query(None, ge=0, description="Offset (alternative to page)"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """List orders for current user"""
    try:
        user_id = current_user["_id"]
        
        # Build query
        query = Order.find(Order.user_id == ObjectId(user_id) if isinstance(user_id, str) else user_id)
        
        if status:
            query = query.find(Order.status == status)
        
        if symbol:
            query = query.find(Order.symbol == symbol)
        
        # Get total count
        total = await query.count()
        
        # Support both pagination styles: page/page_size OR limit/offset
        if limit is not None:
            # Frontend uses limit/offset
            page_size_val = limit
            skip = offset or 0
        else:
            # Backend default uses page/page_size
            page_size_val = page_size or 50
            page_val = page or 1
            skip = (page_val - 1) * page_size_val
        
        # Paginate
        orders = await query.skip(skip).limit(page_size_val).sort(-Order.created_at).to_list()
        
        # Convert to response
        order_responses = [
            OrderResponse(
                id=str(order.id),
                user_id=str(order.user_id),
                user_wallet_id=str(order.user_wallet_id),
                position_id=str(order.position_id) if order.position_id else None,
                flow_id=str(order.flow_id) if order.flow_id else None,
                symbol=order.symbol,
                side=order.side.value,
                order_type=order.order_type.value,
                time_in_force=order.time_in_force.value,
                status=order.status.value,
                requested_amount=order.requested_amount,
                filled_amount=order.filled_amount,
                remaining_amount=order.remaining_amount,
                limit_price=order.limit_price,
                stop_price=order.stop_price,
                average_fill_price=order.average_fill_price,
                total_fees=order.total_fees,
                total_fees_usd=order.total_fees_usd,
                external_order_id=order.external_order_id,
                fills=[
                    {
                        "fill_id": f["fill_id"],
                        "amount": Decimal(str(f["amount"])),
                        "price": Decimal(str(f["price"])),
                        "fee": Decimal(str(f.get("fee", 0))),
                        "fee_currency": f.get("fee_currency", "USDT"),
                        "timestamp": f.get("timestamp", datetime.now(timezone.utc)),
                        "trade_id": f.get("trade_id")
                    }
                    for f in order.fills
                ],
                status_history=[
                    {
                        "status": h["status"],
                        "timestamp": h["timestamp"],
                        "reason": h.get("reason"),
                        "metadata": h.get("metadata")
                    }
                    for h in order.status_history
                ],
                created_at=order.created_at,
                submitted_at=order.submitted_at,
                first_fill_at=order.first_fill_at,
                last_fill_at=order.last_fill_at,
                closed_at=order.closed_at,
                metadata=order.metadata
            )
            for order in orders
        ]
        
        return OrderListResponse(
            orders=order_responses,
            total=total,
            page=page,
            page_size=page_size
        )
    
    except Exception as e:
        logger.error(f"Error listing orders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CANCEL ORDER ====================

@router.post("/{order_id}/cancel", response_model=OrderCancelResponse)
async def cancel_order(
    order_id: str,
    request: CancelOrderRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Cancel an open order"""
    try:
        user_id = current_user["_id"]
        
        order = await Order.get(order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Verify order belongs to user
        if str(order.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if order can be cancelled
        if not order.is_open():
            raise HTTPException(
                status_code=400,
                detail=f"Order cannot be cancelled. Current status: {order.status.value}"
            )
        
        # Update status
        await order.update_status(
            OrderStatus.CANCELLING,
            request.reason or "User requested cancellation"
        )

        if order.external_order_id:
            wallet = await create_wallet_from_db(db, str(order.user_wallet_id))
            await wallet.cancel_order(order.external_order_id, order.symbol)
            await order.update_status(
                OrderStatus.CANCELLED,
                "Order cancelled successfully",
                metadata={"exchange_cancel": True}
            )
        else:
            await order.update_status(
                OrderStatus.CANCELLED,
                "Order cancelled without external order id",
                metadata={"exchange_cancel": False}
            )
        
        logger.info(f"Order {order_id} cancelled by user {user_id}")
        
        return OrderCancelResponse(
            success=True,
            message="Order cancelled successfully",
            order_id=str(order.id),
            status=order.status.value
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MONITOR ORDER ====================

@router.post("/{order_id}/monitor")
async def monitor_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Manually trigger order monitoring"""
    try:
        user_id = current_user["_id"]
        
        order = await Order.get(order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Verify order belongs to user
        if str(order.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Monitor order
        monitor_service = await get_order_monitor(db)
        result = await monitor_service.monitor_order(order_id)
        
        return {
            "success": result["success"],
            "message": result.get("message", "Order monitored"),
            "status": result.get("status"),
            "filled_amount": result.get("filled_amount"),
            "remaining_amount": result.get("remaining_amount")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error monitoring order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

