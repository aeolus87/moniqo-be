"""
Market Health Service

Computes market health metrics like volatility, trend, and crash detection.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from statistics import stdev


def _safe_stdev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(stdev(values))


def compute_market_health(
    closes: List[float],
    indicators: Dict[str, Any],
    ticker_change_percent: float,
    crash_threshold: float,
) -> Dict[str, Any]:
    """
    Compute market health metrics from recent closes and indicators.

    Returns:
        Dict with volatility, trend, strength, crash_detected.
    """
    returns = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        curr = closes[i]
        if prev == 0:
            continue
        returns.append((curr - prev) / prev)

    volatility = _safe_stdev(returns) * 100

    sma_20 = indicators.get("sma_20")
    sma_50 = indicators.get("sma_50")
    trend = "sideways"
    if sma_20 is not None and sma_50 is not None:
        if sma_20 > sma_50:
            trend = "bullish"
        elif sma_20 < sma_50:
            trend = "bearish"

    strength = min(100, abs(ticker_change_percent))
    crash_detected = ticker_change_percent <= -abs(crash_threshold)

    return {
        "volatility": round(volatility, 4),
        "trend": trend,
        "strength": int(strength),
        "crash_detected": crash_detected,
        "crash_threshold": float(crash_threshold),
    }
