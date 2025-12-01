"""
DemoWallet Tests

Tests for simulated paper trading wallet.
Covers: balance management, order execution, state persistence.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.integrations.wallets.demo_wallet import DemoWallet
from app.integrations.wallets.base import (
    OrderSide,
    OrderType,
    OrderStatus,
    TimeInForce,
    InsufficientFundsError,
    InvalidOrderError,
    OrderNotFoundError,
    SymbolNotSupportedError
)


# ==================== FIXTURES ====================

@pytest_asyncio.fixture
async def mock_db():
    """Mock MongoDB database"""
    db = AsyncMock(spec=AsyncIOMotorDatabase)
    
    # Mock collections
    db.demo_wallet_state = AsyncMock()
    db.user_wallets = AsyncMock()
    
    return db


@pytest_asyncio.fixture
async def demo_wallet(mock_db):
    """Create DemoWallet instance"""
    wallet = DemoWallet(
        wallet_id="demo-wallet-001",
        user_wallet_id="user_wallet_123",
        credentials={},
        initial_balance={"USDT": 10000.0},
        fee_rate=0.001,  # 0.1%
        slippage_rate=0.0001  # 0.01%
    )
    
    wallet.db = mock_db
    
    # Mock state loading
    mock_state = {
        "_id": "state_123",
        "user_wallet_id": "user_wallet_123",
        "cash_balances": {"USDT": 10000.0},
        "asset_balances": {},
        "locked_balances": {},
        "open_orders": [],
        "transaction_history": [],
        "starting_balance": 10000.0,
        "total_realized_pnl": 0.0,
        "total_fees_paid": 0.0,
        "total_trades": 0,
        "fee_rate": 0.001,
        "slippage_rate": 0.0001,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    mock_db.demo_wallet_state.find_one.return_value = mock_state
    mock_db.demo_wallet_state.insert_one.return_value = MagicMock(inserted_id="state_123")
    mock_db.demo_wallet_state.update_one.return_value = None
    
    return wallet


# ==================== INITIALIZATION TESTS ====================

def test_demo_wallet_init():
    """Test: DemoWallet initialization"""
    wallet = DemoWallet(
        wallet_id="demo-1",
        user_wallet_id="user_wallet_1",
        credentials={},
        initial_balance={"USDT": 5000.0}
    )
    
    assert wallet.wallet_id == "demo-1"
    assert wallet.user_wallet_id == "user_wallet_1"
    assert wallet.initial_balance == {"USDT": 5000.0}
    assert wallet.fee_rate == Decimal("0.001")
    assert wallet.slippage_rate == Decimal("0.0001")


def test_demo_wallet_custom_fees():
    """Test: DemoWallet with custom fees"""
    wallet = DemoWallet(
        wallet_id="demo-1",
        user_wallet_id="user_wallet_1",
        credentials={},
        fee_rate=0.002,  # 0.2%
        slippage_rate=0.0005  # 0.05%
    )
    
    assert wallet.fee_rate == Decimal("0.002")
    assert wallet.slippage_rate == Decimal("0.0005")


# ==================== BALANCE TESTS ====================

@pytest.mark.asyncio
async def test_get_balance_cash(demo_wallet):
    """Test: Get cash balance (USDT)"""
    balance = await demo_wallet.get_balance("USDT")
    
    assert balance == Decimal("10000.0")


@pytest.mark.asyncio
async def test_get_balance_asset_zero(demo_wallet):
    """Test: Get balance for asset not owned"""
    balance = await demo_wallet.get_balance("BTC")
    
    assert balance == Decimal("0")


@pytest.mark.asyncio
async def test_get_all_balances(demo_wallet):
    """Test: Get all balances"""
    balances = await demo_wallet.get_all_balances()
    
    assert "USDT" in balances
    assert balances["USDT"] == Decimal("10000.0")


@pytest.mark.asyncio
async def test_get_all_balances_with_assets(demo_wallet, mock_db):
    """Test: Get all balances when owning assets"""
    # Update mock state to include assets
    mock_state = await demo_wallet._load_state()
    mock_state["asset_balances"] = {"BTC": 0.5, "ETH": 2.0}
    mock_db.demo_wallet_state.find_one.return_value = mock_state
    
    balances = await demo_wallet.get_all_balances()
    
    assert "USDT" in balances
    assert "BTC" in balances
    assert "ETH" in balances
    assert balances["BTC"] == Decimal("0.5")


# ==================== MARKET ORDER TESTS ====================

@pytest.mark.asyncio
async def test_place_market_order_buy_success(demo_wallet):
    """Test: Place market buy order successfully"""
    # Mock market price
    with patch.object(demo_wallet, "_get_market_price_placeholder", return_value=Decimal("50000")):
        result = await demo_wallet.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1")
        )
    
    assert result["success"] is True
    assert result["status"] == OrderStatus.FILLED
    assert result["filled_quantity"] == Decimal("0.1")
    assert result["order_id"].startswith("demo_")
    assert "fee" in result
    assert result["fee"] > 0


@pytest.mark.asyncio
async def test_place_market_order_sell_success(demo_wallet, mock_db):
    """Test: Place market sell order successfully"""
    # Add BTC balance first
    mock_state = await demo_wallet._load_state()
    mock_state["asset_balances"] = {"BTC": 1.0}
    mock_db.demo_wallet_state.find_one.return_value = mock_state
    
    # Mock market price
    with patch.object(demo_wallet, "_get_market_price_placeholder", return_value=Decimal("50000")):
        result = await demo_wallet.place_order(
            symbol="BTC/USDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.5")
        )
    
    assert result["success"] is True
    assert result["status"] == OrderStatus.FILLED
    assert result["filled_quantity"] == Decimal("0.5")


@pytest.mark.asyncio
async def test_place_market_order_insufficient_funds(demo_wallet):
    """Test: Market order with insufficient funds"""
    # Try to buy more than balance allows
    with patch.object(demo_wallet, "_get_market_price_placeholder", return_value=Decimal("50000")):
        with pytest.raises(InsufficientFundsError) as exc_info:
            await demo_wallet.place_order(
                symbol="BTC/USDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("10")  # Too much (10 BTC = $500k)
            )
        
        assert "Insufficient USDT balance" in str(exc_info.value)


@pytest.mark.asyncio
async def test_place_market_order_insufficient_asset(demo_wallet):
    """Test: Sell order with insufficient asset"""
    # Try to sell BTC we don't have
    with patch.object(demo_wallet, "_get_market_price_placeholder", return_value=Decimal("50000")):
        with pytest.raises(InsufficientFundsError) as exc_info:
            await demo_wallet.place_order(
                symbol="BTC/USDT",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=Decimal("1")  # Don't own any BTC
            )
        
        assert "Insufficient BTC balance" in str(exc_info.value)


@pytest.mark.asyncio
async def test_market_order_applies_slippage(demo_wallet):
    """Test: Market order applies slippage"""
    market_price = Decimal("50000")
    
    with patch.object(demo_wallet, "_get_market_price_placeholder", return_value=market_price):
        result = await demo_wallet.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1")
        )
    
    # Buy order: execution price should be higher (worse for buyer)
    execution_price = result["average_price"]
    expected_slippage = market_price * demo_wallet.slippage_rate
    
    assert execution_price > market_price
    assert execution_price == pytest.approx(float(market_price + expected_slippage))


@pytest.mark.asyncio
async def test_market_order_applies_fees(demo_wallet):
    """Test: Market order applies fees"""
    with patch.object(demo_wallet, "_get_market_price_placeholder", return_value=Decimal("50000")):
        result = await demo_wallet.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1")
        )
    
    # Fee should be ~0.1% of notional value
    quantity = Decimal("0.1")
    price = result["average_price"]
    notional = quantity * Decimal(str(price))
    expected_fee = notional * demo_wallet.fee_rate
    
    assert result["fee"] > 0
    assert Decimal(str(result["fee"])) == pytest.approx(expected_fee, rel=1e-6)


# ==================== LIMIT ORDER TESTS ====================

@pytest.mark.asyncio
async def test_place_limit_order_success(demo_wallet):
    """Test: Place limit order (added to open orders)"""
    result = await demo_wallet.place_order(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("0.1"),
        price=Decimal("48000")  # Limit price
    )
    
    assert result["success"] is True
    assert result["status"] == OrderStatus.OPEN
    assert result["filled_quantity"] == Decimal("0")


@pytest.mark.asyncio
async def test_place_limit_order_without_price(demo_wallet):
    """Test: Limit order without price should fail"""
    with pytest.raises(InvalidOrderError) as exc_info:
        await demo_wallet.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1")
            # Missing price!
        )
    
    assert "require a limit price" in str(exc_info.value)


# ==================== ORDER CANCELLATION TESTS ====================

@pytest.mark.asyncio
async def test_cancel_order_success(demo_wallet, mock_db):
    """Test: Cancel open order successfully"""
    # Add order to open orders
    order = {
        "order_id": "demo_test_order_123",
        "symbol": "BTC/USDT",
        "side": "buy",
        "type": "limit",
        "quantity": 0.1,
        "status": "open"
    }
    
    mock_state = await demo_wallet._load_state()
    mock_state["open_orders"] = [order]
    mock_db.demo_wallet_state.find_one.return_value = mock_state
    
    # Cancel order
    result = await demo_wallet.cancel_order("demo_test_order_123", "BTC/USDT")
    
    assert result["success"] is True
    assert result["status"] == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_nonexistent_order(demo_wallet):
    """Test: Cancel order that doesn't exist"""
    with pytest.raises(OrderNotFoundError) as exc_info:
        await demo_wallet.cancel_order("nonexistent_order", "BTC/USDT")
    
    assert "not found" in str(exc_info.value)


# ==================== ORDER STATUS TESTS ====================

@pytest.mark.asyncio
async def test_get_order_status_open_order(demo_wallet, mock_db):
    """Test: Get status of open order"""
    order = {
        "order_id": "demo_order_123",
        "symbol": "BTC/USDT",
        "side": "buy",
        "type": "limit",
        "quantity": 0.1,
        "filled_quantity": 0.0,
        "remaining_quantity": 0.1,
        "status": "open",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    mock_state = await demo_wallet._load_state()
    mock_state["open_orders"] = [order]
    mock_db.demo_wallet_state.find_one.return_value = mock_state
    
    # Get status
    status = await demo_wallet.get_order_status("demo_order_123", "BTC/USDT")
    
    assert status["order_id"] == "demo_order_123"
    assert status["status"] == OrderStatus.OPEN
    assert status["symbol"] == "BTC/USDT"


@pytest.mark.asyncio
async def test_get_order_status_nonexistent(demo_wallet):
    """Test: Get status of nonexistent order"""
    with pytest.raises(OrderNotFoundError):
        await demo_wallet.get_order_status("nonexistent", "BTC/USDT")


# ==================== MARKET DATA TESTS ====================

@pytest.mark.asyncio
async def test_get_market_price(demo_wallet):
    """Test: Get market price for symbol"""
    with patch.object(demo_wallet, "_get_market_price_placeholder", return_value=Decimal("50000")):
        price = await demo_wallet.get_market_price("BTC/USDT")
    
    assert price == Decimal("50000")


@pytest.mark.asyncio
async def test_get_market_price_unsupported_symbol(demo_wallet):
    """Test: Get price for unsupported symbol"""
    with patch.object(demo_wallet, "_get_market_price_placeholder", return_value=None):
        with pytest.raises(SymbolNotSupportedError):
            await demo_wallet.get_market_price("UNSUPPORTED/USDT")


@pytest.mark.asyncio
async def test_get_ticker(demo_wallet):
    """Test: Get ticker data"""
    with patch.object(demo_wallet, "_get_market_price_placeholder", return_value=Decimal("50000")):
        ticker = await demo_wallet.get_ticker("BTC/USDT")
    
    assert "symbol" in ticker
    assert "bid" in ticker
    assert "ask" in ticker
    assert "last" in ticker
    assert ticker["symbol"] == "BTC/USDT"


# ==================== SYMBOL FORMATTING TESTS ====================

def test_format_symbol(demo_wallet):
    """Test: Format symbol (demo wallet uses universal format)"""
    formatted = demo_wallet.format_symbol("BTC/USDT")
    assert formatted == "BTC/USDT"


def test_parse_symbol(demo_wallet):
    """Test: Parse symbol (demo wallet uses universal format)"""
    parsed = demo_wallet.parse_symbol("BTC/USDT")
    assert parsed == "BTC/USDT"


def test_format_price(demo_wallet):
    """Test: Format price to 2 decimals"""
    formatted = demo_wallet.format_price("BTC/USDT", Decimal("50000.123456"))
    assert formatted == Decimal("50000.12")


def test_format_quantity(demo_wallet):
    """Test: Format quantity to 8 decimals"""
    formatted = demo_wallet.format_quantity("BTC/USDT", Decimal("0.123456789"))
    assert formatted == Decimal("0.12345678")


# ==================== CONNECTION TESTS ====================

@pytest.mark.asyncio
async def test_test_connection(demo_wallet):
    """Test: Test connection (always succeeds for demo)"""
    result = await demo_wallet.test_connection()
    
    assert result["success"] is True
    assert result["latency_ms"] == 0
    assert "server_time" in result


@pytest.mark.asyncio
async def test_get_exchange_info(demo_wallet):
    """Test: Get exchange info"""
    info = await demo_wallet.get_exchange_info()
    
    assert "symbols" in info
    assert "rate_limits" in info
    assert len(info["symbols"]) > 0


# ==================== TRADE HISTORY TESTS ====================

@pytest.mark.asyncio
async def test_get_trade_history_empty(demo_wallet):
    """Test: Get trade history when no trades"""
    history = await demo_wallet.get_trade_history()
    
    assert isinstance(history, list)
    assert len(history) == 0


@pytest.mark.asyncio
async def test_get_trade_history_with_trades(demo_wallet, mock_db):
    """Test: Get trade history with transactions"""
    transactions = [
        {
            "order_id": "order_1",
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 50000.0,
            "timestamp": datetime.now(timezone.utc)
        },
        {
            "order_id": "order_2",
            "symbol": "ETH/USDT",
            "side": "sell",
            "quantity": 1.0,
            "price": 3000.0,
            "timestamp": datetime.now(timezone.utc)
        }
    ]
    
    mock_state = await demo_wallet._load_state()
    mock_state["transaction_history"] = transactions
    mock_db.demo_wallet_state.find_one.return_value = mock_state
    
    history = await demo_wallet.get_trade_history()
    
    assert len(history) == 2


@pytest.mark.asyncio
async def test_get_trade_history_filter_by_symbol(demo_wallet, mock_db):
    """Test: Get trade history filtered by symbol"""
    transactions = [
        {"symbol": "BTC/USDT", "order_id": "1"},
        {"symbol": "ETH/USDT", "order_id": "2"},
        {"symbol": "BTC/USDT", "order_id": "3"}
    ]
    
    mock_state = await demo_wallet._load_state()
    mock_state["transaction_history"] = transactions
    mock_db.demo_wallet_state.find_one.return_value = mock_state
    
    history = await demo_wallet.get_trade_history(symbol="BTC/USDT")
    
    assert len(history) == 2
    assert all(tx["symbol"] == "BTC/USDT" for tx in history)


# ==================== INTEGRATION TESTS ====================

@pytest.mark.asyncio
async def test_full_trading_workflow(demo_wallet):
    """Test: Complete trading workflow"""
    # 1. Check initial balance
    initial_balance = await demo_wallet.get_balance("USDT")
    assert initial_balance == Decimal("10000")
    
    # 2. Place buy order
    with patch.object(demo_wallet, "_get_market_price_placeholder", return_value=Decimal("50000")):
        buy_result = await demo_wallet.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1")
        )
    
    assert buy_result["success"] is True
    
    # 3. Check BTC balance
    btc_balance = await demo_wallet.get_balance("BTC")
    assert btc_balance == Decimal("0.1")
    
    # 4. Sell BTC
    with patch.object(demo_wallet, "_get_market_price_placeholder", return_value=Decimal("51000")):
        sell_result = await demo_wallet.place_order(
            symbol="BTC/USDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1")
        )
    
    assert sell_result["success"] is True
    
    # 5. Check final balances
    final_btc = await demo_wallet.get_balance("BTC")
    assert final_btc == Decimal("0")
    
    final_usdt = await demo_wallet.get_balance("USDT")
    # Should have made profit (bought at $50k, sold at $51k)
    # Minus fees
    assert final_usdt > initial_balance  # Profit!


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

