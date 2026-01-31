"""
Semantic Indicator Enricher

Adds human-readable semantic meaning to technical indicators.
Transforms raw numbers into actionable insights for AI agents.

Author: Moniqo Team
Last Updated: 2026-01-30
"""

from typing import Dict, Any, Optional, List


def enrich_indicator_with_semantics(
    name: str,
    value: float,
    signal: Optional[str] = None,
    current_price: Optional[float] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Add semantic meaning to an indicator value.
    
    Args:
        name: Indicator name (e.g., "RSI(14)")
        value: Indicator value
        signal: Trading signal ("buy", "sell", "neutral")
        current_price: Current market price (for context)
        context: Additional context (e.g., MACD histogram, BB bands)
        
    Returns:
        Human-readable indicator description with semantic meaning
    """
    name_lower = name.lower()
    
    # RSI Semantic Enrichment
    if "rsi" in name_lower:
        if value >= 70:
            return f"RSI: {value:.2f} (Overbought condition - strong sell signal, potential reversal)"
        elif value >= 60:
            return f"RSI: {value:.2f} (Approaching overbought - caution for longs)"
        elif value <= 30:
            return f"RSI: {value:.2f} (Oversold condition - strong buy signal, potential bullish reversal)"
        elif value <= 40:
            return f"RSI: {value:.2f} (Approaching oversold - potential buying opportunity)"
        else:
            return f"RSI: {value:.2f} (Neutral range - no extreme conditions)"
    
    # MACD Semantic Enrichment
    if "macd" in name_lower:
        if context and "histogram" in context:
            histogram = context.get("histogram", 0)
            macd_line = context.get("macd", value)
            signal_line = context.get("signal", 0)
            
            if histogram > 0 and macd_line > signal_line:
                strength = "strong" if histogram > abs(macd_line) * 0.1 else "moderate"
                return f"MACD: {value:.4f} (Bullish crossover - {strength} momentum, histogram: {histogram:.4f})"
            elif histogram < 0 and macd_line < signal_line:
                strength = "strong" if abs(histogram) > abs(macd_line) * 0.1 else "moderate"
                return f"MACD: {value:.4f} (Bearish crossover - {strength} momentum, histogram: {histogram:.4f})"
            else:
                return f"MACD: {value:.4f} (Neutral - no clear crossover signal)"
        return f"MACD: {value:.4f} ({signal or 'neutral'} signal)"
    
    # Bollinger Bands Semantic Enrichment
    if "bb_" in name_lower or "bollinger" in name_lower:
        if context and current_price:
            upper = context.get("upper")
            lower = context.get("lower")
            middle = context.get("middle")
            
            if upper and lower and middle:
                if current_price >= upper:
                    return f"BB {name.split('_')[-1]}: {value:.2f} (Price at upper band - overbought, potential sell)"
                elif current_price <= lower:
                    return f"BB {name.split('_')[-1]}: {value:.2f} (Price at lower band - oversold, potential buy)"
                elif current_price > middle:
                    return f"BB {name.split('_')[-1]}: {value:.2f} (Price above middle band - bullish bias)"
                else:
                    return f"BB {name.split('_')[-1]}: {value:.2f} (Price below middle band - bearish bias)"
        return f"{name}: {value:.2f} ({signal or 'neutral'} signal)"
    
    # Moving Averages Semantic Enrichment
    if "sma" in name_lower or "ema" in name_lower:
        if current_price:
            if current_price > value:
                return f"{name}: {value:.2f} (Price above MA - bullish trend)"
            elif current_price < value:
                return f"{name}: {value:.2f} (Price below MA - bearish trend)"
            else:
                return f"{name}: {value:.2f} (Price at MA - neutral, potential reversal)"
        return f"{name}: {value:.2f} ({signal or 'neutral'} signal)"
    
    # ATR Semantic Enrichment
    if "atr" in name_lower:
        if context and current_price:
            atr_pct = (value / current_price) * 100 if current_price > 0 else 0
            if atr_pct > 3:
                return f"ATR: {value:.2f} (High volatility - {atr_pct:.1f}% of price, increased risk)"
            elif atr_pct > 1.5:
                return f"ATR: {value:.2f} (Moderate volatility - {atr_pct:.1f}% of price)"
            else:
                return f"ATR: {value:.2f} (Low volatility - {atr_pct:.1f}% of price, stable conditions)"
        return f"ATR: {value:.2f} (Volatility measure)"
    
    # Default: Return with signal if available
    if signal:
        return f"{name}: {value:.2f} ({signal} signal)"
    return f"{name}: {value:.2f}"


def enrich_indicators_dict(
    indicators_dict: Dict[str, Any],
    current_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Enrich all indicators in a dictionary with semantic meaning.
    
    Args:
        indicators_dict: Dict from calculate_all_indicators()
        current_price: Current market price
        
    Returns:
        Enriched indicators dict with semantic descriptions
    """
    enriched = {
        "indicators": [],
        "summary": indicators_dict.get("summary", "neutral"),
        "signals": indicators_dict.get("signals", {}),
        "semantic_indicators": [],  # New: human-readable descriptions
    }
    
    # Extract MACD context for enrichment
    macd_context = None
    for ind in indicators_dict.get("indicators", []):
        if "macd" in ind.get("name", "").lower():
            if macd_context is None:
                macd_context = {}
            if ind["name"] == "MACD":
                macd_context["macd"] = ind["value"]
            elif ind["name"] == "MACD_Signal":
                macd_context["signal"] = ind["value"]
            elif ind["name"] == "MACD_Histogram":
                macd_context["histogram"] = ind["value"]
    
    # Extract Bollinger Bands context
    bb_context = None
    for ind in indicators_dict.get("indicators", []):
        if "bb_" in ind.get("name", "").lower():
            if bb_context is None:
                bb_context = {}
            if ind["name"] == "BB_Upper":
                bb_context["upper"] = ind["value"]
            elif ind["name"] == "BB_Middle":
                bb_context["middle"] = ind["value"]
            elif ind["name"] == "BB_Lower":
                bb_context["lower"] = ind["value"]
    
    # Enrich each indicator
    for ind in indicators_dict.get("indicators", []):
        name = ind.get("name", "")
        value = ind.get("value", 0)
        signal = ind.get("signal")
        
        # Build context for this indicator
        context = {}
        if "macd" in name.lower():
            context = macd_context or {}
        elif "bb_" in name.lower():
            context = bb_context or {}
        
        # Create semantic description
        semantic_desc = enrich_indicator_with_semantics(
            name=name,
            value=value,
            signal=signal,
            current_price=current_price,
            context=context
        )
        
        enriched["indicators"].append({
            **ind,
            "semantic": semantic_desc,  # Add semantic description
        })
        enriched["semantic_indicators"].append(semantic_desc)
    
    return enriched
