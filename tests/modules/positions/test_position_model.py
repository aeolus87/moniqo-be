"""
Position Model Tests

Comprehensive tests for Position model and P&L calculation.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from bson import ObjectId

from app.modules.positions.models import (
    Position,
    PositionStatus,
    PositionSide,
    PositionUpdate
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
def entry_order_id():
    """Test entry order ID"""
    return ObjectId()


@pytest.fixture
def sample_entry_data(entry_order_id):
    """Sample entry data"""
    return {
        "order_id": entry_order_id,
        "timestamp": datetime.now(timezone.utc),
        "price": Decimal("50000.00"),
        "amount": Decimal("0.5"),
        "value": Decimal("25000.00"),
        "leverage": Decimal("1"),
        "margin_used": Decimal("25000.00"),
        "fees": Decimal("25.00"),
        "fee_currency": "USDT",
        "market_conditions": {
            "price": Decimal("50000.00"),
            "rsi_14": 45,
            "volume_24h": Decimal("1500000000"),
            "volatility": "medium"
        },
        "ai_reasoning": "Strong support at 49K",
        "ai_confidence": 85,
        "ai_agent": "momentum_trader"
    }


@pytest.fixture
def sample_position(user_id, wallet_id, sample_entry_data):
    """Create sample position"""
    position = Position(
        user_id=user_id,
        user_wallet_id=wallet_id,
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        entry=sample_entry_data,
        status=PositionStatus.OPENING
    )
    position.opened_at = datetime.now(timezone.utc)
    position.status = PositionStatus.OPEN
    return position


# ==================== INITIALIZATION TESTS ====================

def test_position_creation(sample_position):
    """Test position creation"""
    assert sample_position.symbol == "BTC/USDT"
    assert sample_position.side == PositionSide.LONG
    assert sample_position.status == PositionStatus.OPEN
    assert sample_position.entry["price"] == Decimal("50000.00")
    assert sample_position.entry["amount"] == Decimal("0.5")
    assert sample_position.entry["value"] == Decimal("25000.00")


def test_position_short_creation(user_id, wallet_id, sample_entry_data):
    """Test short position creation"""
    position = Position(
        user_id=user_id,
        user_wallet_id=wallet_id,
        symbol="BTC/USDT",
        side=PositionSide.SHORT,
        entry=sample_entry_data,
        status=PositionStatus.OPEN
    )
    
    assert position.side == PositionSide.SHORT


# ==================== PRICE UPDATE TESTS ====================

@pytest.mark.asyncio
async def test_update_price_profit(sample_position):
    """Test price update with profit"""
    await sample_position.update_price(Decimal("51000.00"))
    
    assert sample_position.current is not None
    assert sample_position.current["price"] == Decimal("51000.00")
    assert sample_position.current["unrealized_pnl"] > 0  # Profit
    assert sample_position.current["unrealized_pnl_percent"] > 0
    assert sample_position.current["high_water_mark"] == Decimal("51000.00")
    assert sample_position.current["low_water_mark"] == Decimal("51000.00")


@pytest.mark.asyncio
async def test_update_price_loss(sample_position):
    """Test price update with loss"""
    await sample_position.update_price(Decimal("49000.00"))
    
    assert sample_position.current["price"] == Decimal("49000.00")
    assert sample_position.current["unrealized_pnl"] < 0  # Loss
    assert sample_position.current["unrealized_pnl_percent"] < 0
    assert sample_position.current["low_water_mark"] == Decimal("49000.00")


@pytest.mark.asyncio
async def test_update_price_multiple(sample_position):
    """Test multiple price updates"""
    # First update - profit
    await sample_position.update_price(Decimal("51000.00"))
    assert sample_position.current["high_water_mark"] == Decimal("51000.00")
    
    # Second update - higher profit
    await sample_position.update_price(Decimal("52000.00"))
    assert sample_position.current["high_water_mark"] == Decimal("52000.00")
    
    # Third update - lower (but still profit)
    await sample_position.update_price(Decimal("51500.00"))
    assert sample_position.current["high_water_mark"] == Decimal("52000.00")  # Still highest
    assert sample_position.current["low_water_mark"] == Decimal("49000.00")  # Lowest seen


@pytest.mark.asyncio
async def test_update_price_long_pnl_calculation(sample_position):
    """Test P&L calculation for long position"""
    entry_price = Decimal("50000.00")
    entry_amount = Decimal("0.5")
    current_price = Decimal("51000.00")
    
    await sample_position.update_price(current_price)
    
    # Expected P&L: (51000 - 50000) * 0.5 = 500
    # Minus fees: 500 - 25 = 475
    expected_pnl = (current_price - entry_price) * entry_amount - Decimal("25.00")
    
    assert sample_position.current["unrealized_pnl"] == expected_pnl
    
    # Expected percentage: 475 / 25000 * 100 = 1.9%
    expected_percent = (expected_pnl / Decimal("25000.00")) * Decimal("100")
    assert abs(sample_position.current["unrealized_pnl_percent"] - expected_percent) < Decimal("0.1")


@pytest.mark.asyncio
async def test_update_price_short_pnl_calculation(user_id, wallet_id, sample_entry_data):
    """Test P&L calculation for short position"""
    position = Position(
        user_id=user_id,
        user_wallet_id=wallet_id,
        symbol="BTC/USDT",
        side=PositionSide.SHORT,
        entry=sample_entry_data,
        status=PositionStatus.OPEN
    )
    position.opened_at = datetime.now(timezone.utc)
    
    entry_price = Decimal("50000.00")
    entry_amount = Decimal("0.5")
    current_price = Decimal("49000.00")  # Price went down (profit for short)
    
    await position.update_price(current_price)
    
    # Expected P&L: (50000 - 49000) * 0.5 = 500
    # Minus fees: 500 - 25 = 475
    expected_pnl = (entry_price - current_price) * entry_amount - Decimal("25.00")
    
    assert position.current["unrealized_pnl"] == expected_pnl


@pytest.mark.asyncio
async def test_update_price_risk_level(sample_position):
    """Test risk level calculation"""
    # Small profit - low risk
    await sample_position.update_price(Decimal("50100.00"))
    assert sample_position.current["risk_level"] == "low"
    
    # Small loss - low risk
    await sample_position.update_price(Decimal("49900.00"))
    assert sample_position.current["risk_level"] == "low"
    
    # Medium loss - medium risk
    await sample_position.update_price(Decimal("49000.00"))  # -2%
    assert sample_position.current["risk_level"] == "medium"
    
    # Large loss - high risk
    await sample_position.update_price(Decimal("47500.00"))  # -5%
    assert sample_position.current["risk_level"] == "high"
    
    # Critical loss - critical risk
    await sample_position.update_price(Decimal("45000.00"))  # -10%
    assert sample_position.current["risk_level"] == "critical"


@pytest.mark.asyncio
async def test_update_price_time_held(sample_position):
    """Test time held calculation"""
    from datetime import timedelta
    
    # Set opened_at to 2 hours ago
    sample_position.opened_at = datetime.now(timezone.utc) - timedelta(hours=2)
    
    await sample_position.update_price(Decimal("51000.00"))
    
    assert sample_position.current["time_held_minutes"] == 120  # 2 hours = 120 minutes


@pytest.mark.asyncio
async def test_update_price_closed_position(user_id, wallet_id, sample_entry_data):
    """Test price update doesn't work for closed position"""
    position = Position(
        user_id=user_id,
        user_wallet_id=wallet_id,
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        entry=sample_entry_data,
        status=PositionStatus.CLOSED
    )
    
    # Should not update
    await position.update_price(Decimal("51000.00"))
    
    assert position.current is None or position.current == {}


# ==================== CLOSE POSITION TESTS ====================

@pytest.mark.asyncio
async def test_close_position_profit(sample_position):
    """Test closing position with profit"""
    exit_order_id = ObjectId()
    
    await sample_position.close(
        order_id=exit_order_id,
        price=Decimal("51500.00"),
        reason="take_profit",
        fees=Decimal("25.75"),
        fee_currency="USDT"
    )
    
    assert sample_position.status == PositionStatus.CLOSED
    assert sample_position.exit is not None
    assert sample_position.exit["order_id"] == exit_order_id
    assert sample_position.exit["price"] == Decimal("51500.00")
    assert sample_position.exit["reason"] == "take_profit"
    assert sample_position.exit["realized_pnl"] > 0  # Profit
    assert sample_position.closed_at is not None


@pytest.mark.asyncio
async def test_close_position_loss(sample_position):
    """Test closing position with loss"""
    exit_order_id = ObjectId()
    
    await sample_position.close(
        order_id=exit_order_id,
        price=Decimal("49000.00"),
        reason="stop_loss",
        fees=Decimal("24.50"),
        fee_currency="USDT"
    )
    
    assert sample_position.status == PositionStatus.CLOSED
    assert sample_position.exit["realized_pnl"] < 0  # Loss
    assert sample_position.exit["reason"] == "stop_loss"


@pytest.mark.asyncio
async def test_close_position_long_pnl_calculation(sample_position):
    """Test realized P&L calculation for long position"""
    exit_order_id = ObjectId()
    exit_price = Decimal("51500.00")
    exit_fees = Decimal("25.75")
    
    await sample_position.close(
        order_id=exit_order_id,
        price=exit_price,
        reason="take_profit",
        fees=exit_fees
    )
    
    entry_price = Decimal("50000.00")
    entry_amount = Decimal("0.5")
    entry_fees = Decimal("25.00")
    
    # Expected P&L: (51500 - 50000) * 0.5 = 750
    # Minus all fees: 750 - 25 - 25.75 = 699.25
    expected_pnl = (exit_price - entry_price) * entry_amount - entry_fees - exit_fees
    
    assert sample_position.exit["realized_pnl"] == expected_pnl
    
    # Expected percentage: 699.25 / 25000 * 100 = 2.797%
    expected_percent = (expected_pnl / Decimal("25000.00")) * Decimal("100")
    assert abs(sample_position.exit["realized_pnl_percent"] - expected_percent) < Decimal("0.1")


@pytest.mark.asyncio
async def test_close_position_short_pnl_calculation(user_id, wallet_id, sample_entry_data):
    """Test realized P&L calculation for short position"""
    position = Position(
        user_id=user_id,
        user_wallet_id=wallet_id,
        symbol="BTC/USDT",
        side=PositionSide.SHORT,
        entry=sample_entry_data,
        status=PositionStatus.OPEN
    )
    position.opened_at = datetime.now(timezone.utc)
    
    exit_order_id = ObjectId()
    exit_price = Decimal("49000.00")  # Price went down (profit for short)
    
    await position.close(
        order_id=exit_order_id,
        price=exit_price,
        reason="take_profit",
        fees=Decimal("24.50")
    )
    
    entry_price = Decimal("50000.00")
    entry_amount = Decimal("0.5")
    
    # Expected P&L: (50000 - 49000) * 0.5 = 500
    # Minus fees: 500 - 25 - 24.50 = 450.50
    expected_pnl = (entry_price - exit_price) * entry_amount - Decimal("25.00") - Decimal("24.50")
    
    assert position.exit["realized_pnl"] == expected_pnl


@pytest.mark.asyncio
async def test_close_position_already_closed(sample_position):
    """Test closing already closed position"""
    exit_order_id1 = ObjectId()
    await sample_position.close(
        order_id=exit_order_id1,
        price=Decimal("51000.00"),
        reason="manual"
    )
    
    # Try to close again
    exit_order_id2 = ObjectId()
    await sample_position.close(
        order_id=exit_order_id2,
        price=Decimal("52000.00"),
        reason="manual"
    )
    
    # Should still have first close
    assert sample_position.exit["order_id"] == exit_order_id1
    assert sample_position.exit["price"] == Decimal("51000.00")


# ==================== STATUS CHECK TESTS ====================

def test_is_open_open(sample_position):
    """Test is_open() for open position"""
    sample_position.status = PositionStatus.OPEN
    assert sample_position.is_open() is True


def test_is_open_opening(sample_position):
    """Test is_open() for opening position"""
    sample_position.status = PositionStatus.OPENING
    assert sample_position.is_open() is False  # Not fully open yet


def test_is_open_closed(sample_position):
    """Test is_open() for closed position"""
    sample_position.status = PositionStatus.CLOSED
    assert sample_position.is_open() is False


def test_is_closed_closed(sample_position):
    """Test is_closed() for closed position"""
    sample_position.status = PositionStatus.CLOSED
    assert sample_position.is_closed() is True


def test_is_closed_liquidated(sample_position):
    """Test is_closed() for liquidated position"""
    sample_position.status = PositionStatus.LIQUIDATED
    assert sample_position.is_closed() is True


def test_is_closed_open(sample_position):
    """Test is_closed() for open position"""
    sample_position.status = PositionStatus.OPEN
    assert sample_position.is_closed() is False


# ==================== POSITION UPDATE TESTS ====================

@pytest.mark.asyncio
async def test_position_update_creation(user_id, wallet_id):
    """Test position update creation"""
    position_id = ObjectId()
    
    update = PositionUpdate(
        position_id=position_id,
        price=Decimal("51000.00"),
        unrealized_pnl=Decimal("475.00"),
        unrealized_pnl_percent=Decimal("1.9")
    )
    
    assert update.position_id == position_id
    assert update.price == Decimal("51000.00")
    assert update.unrealized_pnl == Decimal("475.00")
    assert update.unrealized_pnl_percent == Decimal("1.9")
    assert isinstance(update.timestamp, datetime)


@pytest.mark.asyncio
async def test_position_update_with_actions(user_id, wallet_id):
    """Test position update with triggered actions"""
    position_id = ObjectId()
    
    update = PositionUpdate(
        position_id=position_id,
        price=Decimal("51000.00"),
        unrealized_pnl=Decimal("475.00"),
        unrealized_pnl_percent=Decimal("1.9"),
        actions_triggered=[
            {
                "action": "trailing_stop_adjusted",
                "from": Decimal("49800.00"),
                "to": Decimal("49980.00")
            }
        ]
    )
    
    assert len(update.actions_triggered) == 1
    assert update.actions_triggered[0]["action"] == "trailing_stop_adjusted"


# ==================== EDGE CASES ====================

@pytest.mark.asyncio
async def test_update_price_drawdown_calculation(sample_position):
    """Test max drawdown calculation"""
    # Go up first
    await sample_position.update_price(Decimal("52000.00"))
    assert sample_position.current["high_water_mark"] == Decimal("52000.00")
    
    # Then drop
    await sample_position.update_price(Decimal("51000.00"))
    assert sample_position.current["high_water_mark"] == Decimal("52000.00")
    assert sample_position.current["low_water_mark"] == Decimal("51000.00")
    
    # Drawdown: (52000 - 51000) / 52000 * 100 = 1.92%
    max_drawdown = ((Decimal("52000.00") - Decimal("51000.00")) / Decimal("52000.00")) * Decimal("100")
    assert abs(sample_position.current["max_drawdown_percent"] - max_drawdown) < Decimal("0.1")


@pytest.mark.asyncio
async def test_close_position_time_held_calculation(sample_position):
    """Test time held calculation on close"""
    from datetime import timedelta
    
    # Set opened_at to 1 day ago
    sample_position.opened_at = datetime.now(timezone.utc) - timedelta(days=1)
    
    exit_order_id = ObjectId()
    await sample_position.close(
        order_id=exit_order_id,
        price=Decimal("51000.00"),
        reason="manual"
    )
    
    # Should be approximately 1440 minutes (24 hours)
    assert sample_position.exit["time_held_minutes"] == 1440


# ==================== SUMMARY ====================

"""
Test Coverage Summary:
✅ Initialization (2 tests)
✅ Price updates (8 tests)
✅ Close position (5 tests)
✅ Status checks (6 tests)
✅ Position updates (2 tests)
✅ Edge cases (2 tests)

TOTAL: 25 comprehensive tests
"""


