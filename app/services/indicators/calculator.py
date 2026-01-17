"""
Technical Indicators Calculator

Pure Python implementation of common technical indicators.
No heavy dependencies - just basic math operations.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class IndicatorResult:
    """Single indicator result"""
    name: str
    value: float
    signal: Optional[str] = None  # "buy", "sell", "neutral"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "signal": self.signal,
        }


def calculate_sma(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate Simple Moving Average.
    
    Args:
        prices: List of closing prices
        period: Number of periods
        
    Returns:
        SMA value or None if not enough data
    """
    if len(prices) < period:
        return None
    
    return sum(prices[-period:]) / period


def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate Exponential Moving Average.
    
    Args:
        prices: List of closing prices
        period: Number of periods
        
    Returns:
        EMA value or None if not enough data
    """
    if len(prices) < period:
        return None
    
    multiplier = 2 / (period + 1)
    
    # Start with SMA for initial value
    ema = sum(prices[:period]) / period
    
    # Calculate EMA for remaining values
    for price in prices[period:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate Relative Strength Index.
    
    Args:
        prices: List of closing prices
        period: RSI period (default: 14)
        
    Returns:
        RSI value (0-100) or None if not enough data
    """
    if len(prices) < period + 1:
        return None
    
    # Calculate price changes
    changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    # Separate gains and losses
    gains = [max(c, 0) for c in changes]
    losses = [abs(min(c, 0)) for c in changes]
    
    # Calculate average gain/loss
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Optional[Dict[str, float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        prices: List of closing prices
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line period (default: 9)
        
    Returns:
        Dict with macd, signal, histogram or None if not enough data
    """
    if len(prices) < slow_period + signal_period:
        return None
    
    # Calculate EMAs
    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)
    
    if fast_ema is None or slow_ema is None:
        return None
    
    # MACD line
    macd_line = fast_ema - slow_ema
    
    # For signal line, we need MACD history
    # Simplified: calculate recent MACD values
    macd_values = []
    for i in range(signal_period + slow_period, len(prices) + 1):
        subset = prices[:i]
        fast = calculate_ema(subset, fast_period)
        slow = calculate_ema(subset, slow_period)
        if fast is not None and slow is not None:
            macd_values.append(fast - slow)
    
    if len(macd_values) < signal_period:
        return None
    
    # Signal line (EMA of MACD)
    signal_line = calculate_ema(macd_values, signal_period)
    
    if signal_line is None:
        return None
    
    # Histogram
    histogram = macd_line - signal_line
    
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
    }


def calculate_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0
) -> Optional[Dict[str, float]]:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: List of closing prices
        period: SMA period (default: 20)
        std_dev: Standard deviation multiplier (default: 2)
        
    Returns:
        Dict with upper, middle, lower bands or None if not enough data
    """
    if len(prices) < period:
        return None
    
    # Middle band (SMA)
    middle = calculate_sma(prices, period)
    
    if middle is None:
        return None
    
    # Calculate standard deviation
    recent_prices = prices[-period:]
    variance = sum((p - middle) ** 2 for p in recent_prices) / period
    std = variance ** 0.5
    
    # Upper and lower bands
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return {
        "upper": upper,
        "middle": middle,
        "lower": lower,
    }


def calculate_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> Optional[float]:
    """
    Calculate Average True Range.
    
    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        period: ATR period (default: 14)
        
    Returns:
        ATR value or None if not enough data
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return None
    
    # Calculate True Range for each period
    true_ranges = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        true_ranges.append(tr)
    
    if len(true_ranges) < period:
        return None
    
    # ATR is the average of True Range
    return sum(true_ranges[-period:]) / period


def get_signal_from_rsi(rsi: float) -> str:
    """Get trading signal from RSI value"""
    if rsi >= 70:
        return "sell"  # Overbought
    elif rsi <= 30:
        return "buy"   # Oversold
    return "neutral"


def get_signal_from_macd(macd: float, signal: float, histogram: float) -> str:
    """Get trading signal from MACD values"""
    if histogram > 0 and macd > signal:
        return "buy"
    elif histogram < 0 and macd < signal:
        return "sell"
    return "neutral"


def get_signal_from_bollinger(price: float, upper: float, lower: float) -> str:
    """Get trading signal from Bollinger Bands"""
    if price >= upper:
        return "sell"  # At upper band
    elif price <= lower:
        return "buy"   # At lower band
    return "neutral"


def calculate_all_indicators(
    prices: List[float],
    highs: Optional[List[float]] = None,
    lows: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Calculate all available indicators.
    
    Args:
        prices: List of closing prices
        highs: List of high prices (optional, for ATR)
        lows: List of low prices (optional, for ATR)
        
    Returns:
        Dict with all indicator values and signals
    """
    indicators = []
    summary_signals = {"buy": 0, "sell": 0, "neutral": 0}
    
    # Current price
    current_price = prices[-1] if prices else 0
    
    # SMA 20
    sma_20 = calculate_sma(prices, 20)
    if sma_20 is not None:
        signal = "buy" if current_price > sma_20 else "sell" if current_price < sma_20 else "neutral"
        indicators.append(IndicatorResult("SMA(20)", round(sma_20, 2), signal))
        summary_signals[signal] += 1
    
    # SMA 50
    sma_50 = calculate_sma(prices, 50)
    if sma_50 is not None:
        signal = "buy" if current_price > sma_50 else "sell" if current_price < sma_50 else "neutral"
        indicators.append(IndicatorResult("SMA(50)", round(sma_50, 2), signal))
        summary_signals[signal] += 1
    
    # EMA 12
    ema_12 = calculate_ema(prices, 12)
    if ema_12 is not None:
        signal = "buy" if current_price > ema_12 else "sell" if current_price < ema_12 else "neutral"
        indicators.append(IndicatorResult("EMA(12)", round(ema_12, 2), signal))
        summary_signals[signal] += 1
    
    # EMA 26
    ema_26 = calculate_ema(prices, 26)
    if ema_26 is not None:
        signal = "buy" if current_price > ema_26 else "sell" if current_price < ema_26 else "neutral"
        indicators.append(IndicatorResult("EMA(26)", round(ema_26, 2), signal))
        summary_signals[signal] += 1
    
    # RSI
    rsi = calculate_rsi(prices, 14)
    if rsi is not None:
        signal = get_signal_from_rsi(rsi)
        indicators.append(IndicatorResult("RSI(14)", round(rsi, 2), signal))
        summary_signals[signal] += 1
    
    # MACD
    macd_result = calculate_macd(prices)
    if macd_result is not None:
        signal = get_signal_from_macd(
            macd_result["macd"],
            macd_result["signal"],
            macd_result["histogram"]
        )
        indicators.append(IndicatorResult("MACD", round(macd_result["macd"], 4), signal))
        indicators.append(IndicatorResult("MACD_Signal", round(macd_result["signal"], 4), None))
        indicators.append(IndicatorResult("MACD_Histogram", round(macd_result["histogram"], 4), None))
        summary_signals[signal] += 1
    
    # Bollinger Bands
    bb = calculate_bollinger_bands(prices)
    if bb is not None:
        signal = get_signal_from_bollinger(current_price, bb["upper"], bb["lower"])
        indicators.append(IndicatorResult("BB_Upper", round(bb["upper"], 2), None))
        indicators.append(IndicatorResult("BB_Middle", round(bb["middle"], 2), None))
        indicators.append(IndicatorResult("BB_Lower", round(bb["lower"], 2), signal))
        summary_signals[signal] += 1
    
    # ATR (if high/low data available)
    if highs and lows:
        atr = calculate_atr(highs, lows, prices)
        if atr is not None:
            indicators.append(IndicatorResult("ATR(14)", round(atr, 2), None))
    
    # Determine overall summary
    if summary_signals["buy"] > summary_signals["sell"]:
        summary = "bullish"
    elif summary_signals["sell"] > summary_signals["buy"]:
        summary = "bearish"
    else:
        summary = "neutral"
    
    return {
        "indicators": [i.to_dict() for i in indicators],
        "summary": summary,
        "signals": summary_signals,
    }
