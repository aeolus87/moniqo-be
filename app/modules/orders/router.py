"""
Order Management Router

FastAPI endpoints for order management using clean architecture.
Router → Service → Repository → Database
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from decimal import Decimal

from app.core.dependencies import get_current_user
from app.domain.models.order import Order, OrderStatus, OrderSide, OrderType, TimeInForce
from app.modules.orders.service import OrderService
from app.modules.orders.repository import OrderRepository, get_order_repository
from app.infrastructure.exchanges.factory import WalletFactory
from app.modules.orders.schemas import (
    CreateOrderRequest,
    UpdateOrderRequest,
    CancelOrderRequest,
    OrderResponse,
    OrderListResponse,
    OrderCreateResponse,
    OrderCancelResponse,
    OrderFillResponse,
    OrderStatusHistoryResponse,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_to_response(order: Order) -> OrderResponse:
    """
    Convert Order domain model to OrderResponse schema.
    
    Args:
        order: Order domain model
        
    Returns:
        OrderResponse schema
    """
    return OrderResponse(
        id=str(order.id) if order.id else "",
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
            OrderFillResponse(
                fill_id=fill.get("fill_id", ""),
                amount=Decimal(str(fill.get("amount", 0))),
                price=Decimal(str(fill.get("price", 0))),
                fee=Decimal(str(fill.get("fee", 0))),
                fee_currency=fill.get("fee_currency", ""),
                timestamp=fill.get("timestamp"),
                trade_id=fill.get("trade_id"),
            )
            for fill in order.fills
        ],
        status_history=[
            OrderStatusHistoryResponse(
                status=hist.get("status", ""),
                timestamp=hist.get("timestamp"),
                reason=hist.get("reason"),
                metadata=hist.get("metadata"),
            )
            for hist in order.status_history
        ],
        created_at=order.created_at,
        submitted_at=order.submitted_at,
        first_fill_at=order.first_fill_at,
        last_fill_at=order.last_fill_at,
        closed_at=order.closed_at,
        metadata=order.metadata,
    )


def get_wallet_factory() -> WalletFactory:
    """Get wallet factory instance."""
    return WalletFactory()


# ==================== CREATE ORDER ====================

@router.post("/", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: CreateOrderRequest,
    current_user: dict = Depends(get_current_user),
    repo: OrderRepository = Depends(get_order_repository),
    wallet_factory: WalletFactory = Depends(get_wallet_factory),
):
    """
    Create a new order.
    
    This endpoint creates an order and places it on the exchange.
    
    **Order Types:**
    - `MARKET`: Execute immediately at market price
    - `LIMIT`: Execute at specified price or better
    - `STOP_LOSS`: Triggered when price hits stop price
    - `TAKE_PROFIT`: Triggered when price hits stop price
    
    **Context Switching:**
    The middleware has already determined the trading mode (real/demo) from the
    wallet_id and set the context. The service automatically routes to the correct
    database and wallet instance.
    """
    try:
        service = OrderService(repository=repo, wallet_factory=wallet_factory)
        
        order = await service.create_order(
            user_id=str(current_user["_id"]),
            user_wallet_id=request.user_wallet_id,
            symbol=request.symbol,
            side=OrderSide(request.side),
            order_type=OrderType(request.order_type),
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
            time_in_force=TimeInForce(request.time_in_force),
            flow_id=request.flow_id,
            metadata=request.metadata,
        )
        
        return OrderCreateResponse(
            success=True,
            order=_order_to_response(order),
            message="Order created successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order"
        )


# ==================== GET ORDER ====================

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    repo: OrderRepository = Depends(get_order_repository),
):
    """Get order by ID."""
    service = OrderService(repository=repo, wallet_factory=WalletFactory())
    
    order = await service.get_order(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Verify order belongs to user
    if str(order.user_id) != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return _order_to_response(order)


# ==================== LIST ORDERS ====================

@router.get("/", response_model=OrderListResponse)
async def list_orders(
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    flow_id: Optional[str] = Query(None, description="Filter by flow ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    repo: OrderRepository = Depends(get_order_repository),
):
    """List orders for current user."""
    service = OrderService(repository=repo, wallet_factory=WalletFactory())
    
    orders = await service.get_user_orders(
        user_id=str(current_user["_id"]),
        status=status,
        symbol=symbol,
        flow_id=flow_id,
        skip=skip,
        limit=limit,
    )
    
    total = await repo.count_by_user(
        user_id=str(current_user["_id"]),
        status=status,
        symbol=symbol,
        flow_id=flow_id,
    )
    
    return OrderListResponse(
        orders=[_order_to_response(order) for order in orders],
        total=total,
        limit=limit,
        offset=skip,
    )


# ==================== CANCEL ORDER ====================

@router.post("/{order_id}/cancel", response_model=OrderCancelResponse)
async def cancel_order(
    order_id: str,
    request: CancelOrderRequest,
    current_user: dict = Depends(get_current_user),
    repo: OrderRepository = Depends(get_order_repository),
):
    """Cancel an order."""
    service = OrderService(repository=repo, wallet_factory=WalletFactory())
    
    # Verify order belongs to user
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if str(order.user_id) != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    order = await service.cancel_order(order_id, reason=request.reason)
    
    return OrderCancelResponse(
        success=True,
        message="Order cancelled successfully",
        order_id=str(order.id),
        status=order.status.value,
    )
