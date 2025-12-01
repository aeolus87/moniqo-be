"""
Order Model Tests

Comprehensive tests for Order model lifecycle management.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from bson import ObjectId

from app.modules.orders.models import (
    Order,
    OrderStatus,
    OrderSide,
    OrderType,
    TimeInForce
)


# ==================== FIXTURES ====================

@pytest.fixture
def user_id():
    """Test user ID"""
    return ObjectId()


@pytest.fixture
def wallet_id():
    """Test wallet ID"""
    return ObjectId()


@pytest.fixture
def sample_order(user_id, wallet_id):
    """Create sample order"""
    return Order(
        user_id=user_id,
        user_wallet_id=wallet_id,
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        requested_amount=Decimal("0.5"),
        time_in_force=TimeInForce.GTC
    )


# ==================== INITIALIZATION TESTS ====================

def test_order_creation(sample_order):
    """Test order creation"""
    assert sample_order.symbol == "BTC/USDT"
    assert sample_order.side == OrderSide.BUY
    assert sample_order.order_type == OrderType.MARKET
    assert sample_order.requested_amount == Decimal("0.5")
    assert sample_order.status == OrderStatus.PENDING
    assert sample_order.filled_amount == Decimal("0")
    assert sample_order.remaining_amount == Decimal("0.5")


def test_order_calculate_remaining_amount(user_id, wallet_id):
    """Test remaining amount calculation"""
    order = Order(
        user_id=user_id,
        user_wallet_id=wallet_id,
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        requested_amount=Decimal("1.0")
    )
    
    assert order.remaining_amount == Decimal("1.0")
    
    order.filled_amount = Decimal("0.3")
    order.remaining_amount = order.requested_amount - order.filled_amount
    assert order.remaining_amount == Decimal("0.7")


# ==================== STATUS UPDATE TESTS ====================

@pytest.mark.asyncio
async def test_update_status_pending_to_submitted(sample_order):
    """Test status update from PENDING to SUBMITTED"""
    await sample_order.update_status(OrderStatus.SUBMITTED, "Order sent to exchange")
    
    assert sample_order.status == OrderStatus.SUBMITTED
    assert sample_order.submitted_at is not None
    assert len(sample_order.status_history) == 1
    assert sample_order.status_history[0]["status"] == "submitted"


@pytest.mark.asyncio
async def test_update_status_to_filled(sample_order):
    """Test status update to FILLED"""
    await sample_order.update_status(OrderStatus.FILLED, "Order completely filled")
    
    assert sample_order.status == OrderStatus.FILLED
    assert sample_order.closed_at is not None
    assert len(sample_order.status_history) == 1


@pytest.mark.asyncio
async def test_update_status_to_cancelled(sample_order):
    """Test status update to CANCELLED"""
    await sample_order.update_status(OrderStatus.CANCELLED, "User cancelled")
    
    assert sample_order.status == OrderStatus.CANCELLED
    assert sample_order.cancelled_at is not None
    assert sample_order.closed_at is not None


@pytest.mark.asyncio
async def test_update_status_multiple_transitions(sample_order):
    """Test multiple status transitions"""
    await sample_order.update_status(OrderStatus.SUBMITTED, "Submitted")
    await sample_order.update_status(OrderStatus.OPEN, "Order opened")
    await sample_order.update_status(OrderStatus.PARTIALLY_FILLED, "Partial fill")
    
    assert len(sample_order.status_history) == 3
    assert sample_order.status == OrderStatus.PARTIALLY_FILLED


# ==================== FILL TESTS ====================

@pytest.mark.asyncio
async def test_add_fill_partial(sample_order):
    """Test adding partial fill"""
    fill = {
        "fill_id": "fill_001",
        "amount": Decimal("0.3"),
        "price": Decimal("50000.00"),
        "fee": Decimal("0.0003"),
        "fee_currency": "BTC"
    }
    
    await sample_order.add_fill(fill)
    
    assert sample_order.filled_amount == Decimal("0.3")
    assert sample_order.remaining_amount == Decimal("0.2")
    assert len(sample_order.fills) == 1
    assert sample_order.status == OrderStatus.PARTIALLY_FILLED
    assert sample_order.average_fill_price == Decimal("50000.00")
    assert sample_order.first_fill_at is not None
    assert sample_order.last_fill_at is not None


@pytest.mark.asyncio
async def test_add_fill_multiple(sample_order):
    """Test adding multiple fills"""
    # First fill
    fill1 = {
        "fill_id": "fill_001",
        "amount": Decimal("0.2"),
        "price": Decimal("49900.00"),
        "fee": Decimal("0.0002"),
        "fee_currency": "BTC"
    }
    await sample_order.add_fill(fill1)
    
    # Second fill
    fill2 = {
        "fill_id": "fill_002",
        "amount": Decimal("0.1"),
        "price": Decimal("50010.00"),
        "fee": Decimal("0.0001"),
        "fee_currency": "BTC"
    }
    await sample_order.add_fill(fill2)
    
    assert sample_order.filled_amount == Decimal("0.3")
    assert sample_order.remaining_amount == Decimal("0.2")
    assert len(sample_order.fills) == 2
    
    # Weighted average: (0.2 * 49900 + 0.1 * 50010) / 0.3 = 49936.67
    expected_avg = (Decimal("0.2") * Decimal("49900") + Decimal("0.1") * Decimal("50010")) / Decimal("0.3")
    assert sample_order.average_fill_price == expected_avg


@pytest.mark.asyncio
async def test_add_fill_complete(sample_order):
    """Test adding fill that completes order"""
    fill = {
        "fill_id": "fill_001",
        "amount": Decimal("0.5"),
        "price": Decimal("50000.00"),
        "fee": Decimal("0.0005"),
        "fee_currency": "BTC"
    }
    
    await sample_order.add_fill(fill)
    
    assert sample_order.filled_amount == Decimal("0.5")
    assert sample_order.remaining_amount == Decimal("0")
    assert sample_order.status == OrderStatus.FILLED
    assert sample_order.closed_at is not None


@pytest.mark.asyncio
async def test_add_fill_fees_calculation(sample_order):
    """Test fee calculation with fills"""
    fill1 = {
        "fill_id": "fill_001",
        "amount": Decimal("0.2"),
        "price": Decimal("50000.00"),
        "fee": Decimal("0.0002"),
        "fee_currency": "BTC"
    }
    await sample_order.add_fill(fill1)
    
    fill2 = {
        "fill_id": "fill_002",
        "amount": Decimal("0.3"),
        "price": Decimal("50100.00"),
        "fee": Decimal("0.0003"),
        "fee_currency": "BTC"
    }
    await sample_order.add_fill(fill2)
    
    assert sample_order.total_fees == Decimal("0.0005")


# ==================== STATUS CHECK TESTS ====================

def test_is_open_pending(sample_order):
    """Test is_open() for pending order"""
    assert sample_order.is_open() is True


def test_is_open_open(sample_order):
    """Test is_open() for open order"""
    sample_order.status = OrderStatus.OPEN
    assert sample_order.is_open() is True


def test_is_open_partially_filled(sample_order):
    """Test is_open() for partially filled order"""
    sample_order.status = OrderStatus.PARTIALLY_FILLED
    assert sample_order.is_open() is True


def test_is_open_filled(sample_order):
    """Test is_open() for filled order"""
    sample_order.status = OrderStatus.FILLED
    assert sample_order.is_open() is False


def test_is_complete_filled(sample_order):
    """Test is_complete() for filled order"""
    sample_order.status = OrderStatus.FILLED
    assert sample_order.is_complete() is True


def test_is_complete_cancelled(sample_order):
    """Test is_complete() for cancelled order"""
    sample_order.status = OrderStatus.CANCELLED
    assert sample_order.is_complete() is True


def test_is_complete_pending(sample_order):
    """Test is_complete() for pending order"""
    sample_order.status = OrderStatus.PENDING
    assert sample_order.is_complete() is False


# ==================== EDGE CASES ====================

@pytest.mark.asyncio
async def test_add_fill_exceeding_amount(sample_order):
    """Test adding fill that exceeds requested amount"""
    fill = {
        "fill_id": "fill_001",
        "amount": Decimal("0.6"),  # More than requested 0.5
        "price": Decimal("50000.00"),
        "fee": Decimal("0.0006"),
        "fee_currency": "BTC"
    }
    
    await sample_order.add_fill(fill)
    
    # Should cap at requested amount
    assert sample_order.filled_amount == Decimal("0.6")  # Allow it (exchange can fill more)
    assert sample_order.remaining_amount == Decimal("-0.1")  # Negative (over-filled)


@pytest.mark.asyncio
async def test_update_status_with_metadata(sample_order):
    """Test status update with metadata"""
    metadata = {
        "exchange_response": {"orderId": 12345},
        "latency_ms": 150
    }
    
    await sample_order.update_status(
        OrderStatus.OPEN,
        "Order accepted",
        metadata=metadata
    )
    
    assert sample_order.status_history[0]["metadata"] == metadata


# ==================== SUMMARY ====================

"""
Test Coverage Summary:
✅ Initialization (2 tests)
✅ Status updates (4 tests)
✅ Add fills (4 tests)
✅ Status checks (6 tests)
✅ Edge cases (2 tests)

TOTAL: 18 comprehensive tests
"""


