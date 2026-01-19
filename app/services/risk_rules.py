"""
Risk Rules Engine

Validates a proposed trade against configured risk limits.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from typing import Any, Dict, List, Optional


def _get_number(value: Optional[Any], default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def evaluate_risk_limits(
    order_request: Dict[str, Any],
    risk_limits: Dict[str, Any],
    portfolio_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluate proposed order against risk limits.

    Returns:
        {
            "approved": bool,
            "violations": [str, ...],
            "summary": { ... }
        }
    """
    portfolio_state = portfolio_state or {}
    violations: List[str] = []

    order_size_usd = _get_number(order_request.get("size_usd"), 0.0)
    portfolio_value_usd = _get_number(portfolio_state.get("portfolio_value_usd"), 10000.0)
    open_positions = int(_get_number(portfolio_state.get("open_positions"), 0))
    daily_loss_usd = _get_number(portfolio_state.get("daily_loss_usd"), 0.0)

    max_position_size_usd = _get_number(risk_limits.get("max_position_size_usd"), 0.0)
    max_position_percent = _get_number(risk_limits.get("max_position_percent"), 0.0)
    daily_loss_limit = _get_number(risk_limits.get("daily_loss_limit"), 0.0)
    max_portfolio_utilization = _get_number(risk_limits.get("max_portfolio_utilization"), 0.0)
    max_open_positions = _get_number(risk_limits.get("max_open_positions"), 0.0)

    position_percent = (order_size_usd / portfolio_value_usd * 100) if portfolio_value_usd else 0.0
    projected_utilization = (
        _get_number(portfolio_state.get("portfolio_utilization_percent"), 0.0)
        + position_percent
    )

    if max_position_size_usd and order_size_usd > max_position_size_usd:
        violations.append(
            f"Order size ${order_size_usd:.2f} exceeds max_position_size_usd ${max_position_size_usd:.2f}."
        )

    if max_position_percent and position_percent > max_position_percent:
        violations.append(
            f"Order size {position_percent:.2f}% exceeds max_position_percent {max_position_percent:.2f}%."
        )

    if daily_loss_limit and daily_loss_usd > daily_loss_limit:
        violations.append(
            f"Daily loss ${daily_loss_usd:.2f} exceeds daily_loss_limit ${daily_loss_limit:.2f}."
        )

    if max_portfolio_utilization and projected_utilization > max_portfolio_utilization:
        violations.append(
            "Projected utilization "
            f"{projected_utilization:.2f}% exceeds max_portfolio_utilization "
            f"{max_portfolio_utilization:.2f}%."
        )

    if max_open_positions and open_positions >= max_open_positions:
        violations.append(
            f"Open positions {open_positions} exceeds max_open_positions {int(max_open_positions)}."
        )

    approved = len(violations) == 0

    return {
        "approved": approved,
        "violations": violations,
        "summary": {
            "order_size_usd": order_size_usd,
            "position_percent": round(position_percent, 4),
            "portfolio_value_usd": portfolio_value_usd,
            "open_positions": open_positions,
            "daily_loss_usd": daily_loss_usd,
            "projected_utilization_percent": round(projected_utilization, 4),
        },
    }
