from decimal import Decimal

from app.modules.flows import service as flow_service


def test_aggregate_swarm_results_majority():
    results = [
        {"action": "buy", "confidence": 0.7, "reasoning": "A"},
        {"action": "buy", "confidence": 0.6, "reasoning": "B"},
        {"action": "sell", "confidence": 0.9, "reasoning": "C"},
    ]

    aggregated = flow_service._aggregate_swarm_results(results)

    assert aggregated["action"] == "buy"
    assert aggregated["confidence"] == 0.65
    assert "buy" in aggregated["reasoning"]


def test_resolve_order_quantity_buy_percent():
    quantity, meta = flow_service._resolve_order_quantity(
        action="buy",
        current_price=Decimal("100"),
        base_balance=None,
        quote_balance=Decimal("1000"),
        order_quantity=None,
        order_size_usd=None,
        order_size_percent=Decimal("10"),
        default_balance_percent=Decimal("10"),
    )

    assert quantity == Decimal("1")
    assert meta["quote_balance"] == 1000.0


def test_resolve_order_quantity_sell_default():
    quantity, meta = flow_service._resolve_order_quantity(
        action="sell",
        current_price=Decimal("200"),
        base_balance=Decimal("2"),
        quote_balance=None,
        order_quantity=None,
        order_size_usd=None,
        order_size_percent=None,
        default_balance_percent=Decimal("25"),
    )

    assert quantity == Decimal("0.5")
    assert meta["base_balance"] == 2.0
