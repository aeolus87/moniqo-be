from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.position_tracker import PositionTrackerService
from app.modules.positions.models import PositionSide, PositionStatus


class DummyPosition:
    def __init__(self):
        self.id = "pos-1"
        self.user_id = "user-1"
        self.user_wallet_id = "wallet-1"
        self.flow_id = "flow-1"
        self.symbol = "BTC/USDT"
        self.side = PositionSide.LONG
        self.status = PositionStatus.OPEN
        self.entry = {"price": 100, "amount": 1, "value": 100}
        self.current = {
            "price": Decimal("110"),
            "unrealized_pnl": Decimal("10"),
            "unrealized_pnl_percent": Decimal("10"),
            "risk_level": "low",
        }
        self.risk_management = {"current_stop_loss": 90, "current_take_profit": 120}
        self.ai_monitoring = {}
        self.exit = {"realized_pnl": 0, "realized_pnl_percent": 0, "amount": 1}

    def is_open(self):
        return self.status == PositionStatus.OPEN

    async def save(self):
        return None

    async def update_price(self, price):
        self.current["price"] = price

    async def close(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_ai_recommendations_update_stops(monkeypatch):
    db = SimpleNamespace()
    tracker = PositionTrackerService(db)

    position = DummyPosition()
    monitor_result = {
        "recommendations": [
            {"position_id": "pos-1", "action": "update_stop_loss", "value": 95},
            {"position_id": "pos-1", "action": "update_take_profit", "value": 130},
        ]
    }

    await tracker._apply_ai_recommendations(position, monitor_result)

    assert position.risk_management["current_stop_loss"] == 95
    assert position.risk_management["current_take_profit"] == 130


@pytest.mark.asyncio
async def test_ai_auto_close_triggers(monkeypatch):
    db = SimpleNamespace()
    tracker = PositionTrackerService(db)

    position = DummyPosition()
    tracker.update_position_price = AsyncMock(return_value={"success": True})

    class DummyWallet:
        async def get_market_price(self, symbol):
            return Decimal("110")

    dummy_wallet = DummyWallet()
    monkeypatch.setattr(
        "app.services.position_tracker.create_wallet_from_db",
        AsyncMock(return_value=dummy_wallet),
    )

    tracker.signal_aggregator.get_signal = AsyncMock(return_value=SimpleNamespace(to_dict=lambda: {"classification": "bullish"}))

    class DummyAgent:
        async def process(self, context):
            return {
                "recommendations": [
                    {"position_id": "pos-1", "action": "close", "reason": "risk"}
                ]
            }

    monkeypatch.setattr("app.services.position_tracker.MonitorAgent", lambda **kwargs: DummyAgent())

    close_mock = AsyncMock()
    tracker._close_position_with_order = close_mock
    monkeypatch.setattr("app.services.position_tracker.Position.get", AsyncMock(return_value=position))

    await tracker.monitor_position("pos-1")

    close_mock.assert_awaited()
