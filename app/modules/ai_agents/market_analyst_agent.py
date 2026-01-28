"""
Market Analyst Agent

Analyzes market conditions and generates trading signals.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Dict, Optional, Any
from datetime import datetime, timezone

from app.modules.ai_agents.base_agent import BaseAgent, AgentRole, AgentStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MarketAnalystAgent(BaseAgent):
    """
    Market Analyst Agent
    
    Analyzes market data and generates trading recommendations.
    
    Responsibilities:
    - Analyze market trends
    - Evaluate technical indicators
    - Assess market sentiment
    - Generate buy/sell/hold signals
    
    Usage:
        agent = MarketAnalystAgent(
            model_provider="gemini",
            api_key="your_key"
        )
        
        result = await agent.process({
            "symbol": "BTC/USDT",
            "market_data": {...},
            "indicators": {...}
        })
    """
    
    def __init__(self, **kwargs):
        """Initialize Market Analyst Agent"""
        super().__init__(
            role=AgentRole.MARKET_ANALYST,
            **kwargs
        )
        
        logger.info("Market Analyst Agent initialized")
    
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market and generate recommendation.
        
        Args:
            context: Context with market data, indicators, etc.
            
        Returns:
            Dict with analysis result:
            {
                "action": "buy" | "sell" | "hold",
                "confidence": 0.0-1.0,
                "reasoning": "...",
                "price_target": 50000.00,
                "stop_loss": 49000.00,
                "take_profit": 52000.00,
                "risk_level": "low" | "medium" | "high"
            }
        """
        try:
            self.status = AgentStatus.ANALYZING
            
            symbol = context.get("symbol", "BTC/USDT")
            market_data = context.get("market_data", {})
            indicators = context.get("indicators", {})
            
            # Build analysis prompt
            prompt = self._build_analysis_prompt(symbol, market_data, indicators)
            system_prompt = self._get_system_prompt()
            
            # Get structured analysis
            schema = {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["buy", "sell", "hold"]
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "reasoning": {
                        "type": "string"
                    },
                    "price_target": {
                        "type": "number"
                    },
                    "stop_loss": {
                        "type": "number"
                    },
                    "take_profit": {
                        "type": "number"
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high"]
                    }
                },
                "required": ["action", "confidence", "reasoning"]
            }
            
            # Generate analysis
            analysis = await self.analyze(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                structured=True,
                schema=schema
            )

            # Apply AI Blindness Safeguard
            original_confidence = analysis.get('confidence', 0.0)
            adjusted_confidence = original_confidence
            blindness_applied = False

            # Check if any sentiment sources are unavailable
            reddit_sentiment = market_data.get("reddit_sentiment")
            polymarket_odds = market_data.get("polymarket_odds")

            sentiment_sources_available = 0
            if reddit_sentiment:
                sentiment_sources_available += 1
            if polymarket_odds:
                sentiment_sources_available += 1

            # If any sentiment source is unavailable, reduce confidence by 15%
            if sentiment_sources_available < 2:
                blindness_applied = True
                adjusted_confidence = original_confidence * 0.85  # Reduce by 15%
                analysis['confidence'] = adjusted_confidence

                # Update reasoning to reflect blindness safeguard
                current_reasoning = analysis.get('reasoning', '')
                blindness_note = f" [AI Blindness Safeguard: {sentiment_sources_available}/2 sentiment sources available, confidence reduced from {original_confidence:.2f} to {adjusted_confidence:.2f}]"
                analysis['reasoning'] = current_reasoning + blindness_note

                logger.info(
                    f"AI Blindness Safeguard applied: {sentiment_sources_available}/2 sources available, "
                    f"confidence {original_confidence:.2f} -> {adjusted_confidence:.2f}"
                )

            self.status = AgentStatus.COMPLETED

            logger.info(
                f"Market Analyst: {symbol} -> {analysis.get('action')} "
                f"(confidence: {adjusted_confidence:.2f})"
                f"{' [Blindness Applied]' if blindness_applied else ''}"
            )

            return {
                "success": True,
                "agent": self.role.value,
                "timestamp": datetime.now(timezone.utc),
                **analysis
            }
        
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Market Analyst analysis failed: {str(e)}")
            return {
                "success": False,
                "agent": self.role.value,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            }
    
    def _build_analysis_prompt(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> str:
        """Build analysis prompt from market data"""
        prompt = f"""
Analyze the market for {symbol} and provide a trading recommendation.

**Market Data:**
- Current Price: ${market_data.get('current_price', 'N/A')}
- 24h High: ${market_data.get('high_24h', 'N/A')}
- 24h Low: ${market_data.get('low_24h', 'N/A')}
- 24h Volume: {market_data.get('volume_24h', 'N/A')}
- 24h Change: {market_data.get('change_24h_percent', 'N/A')}%

**Technical Indicators:**
"""
        
        if indicators:
            prompt += "\n".join([
                f"- {key}: {value}"
                for key, value in indicators.items()
            ])
        else:
            prompt += "- No indicators provided"
        
        # Add external social & prediction signals section
        prompt += "\n\n**External Social & Prediction Signals:**\n"
        
        reddit_sentiment = market_data.get("reddit_sentiment")
        if reddit_sentiment:
            sentiment = reddit_sentiment.get('sentiment', 'N/A')
            score = reddit_sentiment.get('sentiment_score', 0)
            mentions = reddit_sentiment.get('mention_volume', 0)
            upvotes = reddit_sentiment.get('total_upvotes', 0)
            posts = reddit_sentiment.get('posts', [])
            
            prompt += f"- Reddit Overall: {sentiment} (Score: {score:.2f})\n"
            prompt += f"- Total Mentions: {mentions} posts, {upvotes} upvotes\n"
            
            # Include actual headlines for the AI to analyze
            if posts:
                prompt += "- Reddit Headlines (read these to gauge community mood):\n"
                for i, post in enumerate(posts[:5], 1):
                    title = post.get('title', 'N/A')
                    post_upvotes = post.get('upvotes', 0)
                    selftext = post.get('selftext_preview', '')
                    prompt += f"  {i}. \"{title}\" ({post_upvotes} upvotes)\n"
                    if selftext and len(selftext) > 10:
                        # Truncate selftext for prompt efficiency
                        preview = selftext[:150] + "..." if len(selftext) > 150 else selftext
                        prompt += f"     Preview: {preview}\n"
        else:
            prompt += "- Reddit Sentiment: Not Available\n"
        
        polymarket_odds = market_data.get("polymarket_odds")
        if polymarket_odds:
            prob = polymarket_odds.get("probability", 0) * 100
            tf = polymarket_odds.get("timeframe", "N/A")
            yes_price = polymarket_odds.get("yes_price", 0) * 100
            no_price = polymarket_odds.get("no_price", 0) * 100
            question = polymarket_odds.get("question", "")
            
            prompt += f"- Polymarket Prediction Market ({tf} timeframe):\n"
            prompt += f"  - BTC Price Up Probability: {prob:.1f}%\n"
            prompt += f"  - Yes: {yes_price:.1f}%, No: {no_price:.1f}%\n"
            if question:
                prompt += f"  - Market Question: \"{question}\"\n"
        else:
            prompt += "- Polymarket Odds: Not Available\n"
        
        prompt += """
**Your Task:**
1. Analyze the current market conditions using technical indicators
2. READ the Reddit headlines above - look for news about hacks, regulations, FUD, or bullish catalysts
3. Consider Polymarket odds as "smart money" - real money is betting on price direction
4. Cross-reference technical signals with Reddit sentiment and Polymarket odds
5. Provide a clear trading recommendation (buy/sell/hold)
6. Suggest price targets, stop loss, and take profit levels

**Critical Instructions:**
- If Reddit headlines mention HACKS, EXPLOITS, or MAJOR NEGATIVE NEWS, strongly consider HOLD regardless of technicals
- If Polymarket "BTC Up" odds are below 40%, treat this as a strong bearish signal
- If Polymarket "BTC Up" odds are above 60%, treat this as a strong bullish confirmation
- Use the headlines to confirm or QUESTION your technical analysis - don't ignore social signals
- Be concise but thorough in your analysis
"""
        
        return prompt
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for market analyst"""
        return """You are a professional cryptocurrency market analyst with expertise in technical analysis, market trends, and risk assessment.

Your responsibilities:
- Analyze market data objectively
- Evaluate technical indicators accurately
- Assess risk/reward ratios
- Provide clear, actionable trading recommendations
- Set appropriate stop-loss and take-profit levels
- Cross-reference technical indicators with external sentiment signals

Guidelines:
- Be conservative with confidence scores
- Always recommend stop-loss and take-profit levels
- Consider market volatility in your analysis
- Focus on data-driven decisions, not emotions

External Social & Prediction Signals - READ CAREFULLY:
1. Reddit Headlines Analysis:
   - READ the actual Reddit headlines provided - they contain real-time community sentiment
   - Look for mentions of: hacks, exploits, regulations, FUD, partnerships, adoption news
   - Headlines mentioning "hack", "exploit", "stolen", "crash" = STRONG SELL/HOLD signal
   - Headlines mentioning "ATH", "moon", "adoption", "institutional" = bullish confirmation
   - Use headlines to CONFIRM or QUESTION your technical analysis

2. Polymarket Prediction Market:
   - Polymarket odds represent REAL MONEY bets on price direction
   - This is "smart money" - prediction markets often lead price moves by 15-60 minutes
   - BTC Up odds > 60% = bullish confirmation, increase confidence
   - BTC Up odds < 40% = bearish warning, reduce confidence or consider HOLD
   - BTC Up odds 40-60% = neutral, rely more on technicals

3. Cross-Validation Rules:
   - If technicals and external signals ALIGN: increase confidence by 10%
   - If technicals and external signals CONFLICT: reduce confidence by 15%, favor HOLD
   - Never ignore strong external signals just because technicals look favorable
   - Example: RSI suggests oversold (buy signal) but Reddit shows hack news = HOLD

AI Blindness Safeguard:
- If any external sentiment source (Reddit/Polymarket) is marked as "Not Available":
  - REDUCE your trade confidence by 15% automatically
  - FAVOR HOLD unless technical indicators are overwhelming (RSI < 20 for buys or RSI > 80 for sells)
  - This prevents overconfidence when external data sources are unavailable
  - Example: If Reddit shows "Not Available", reduce confidence from 0.8 to 0.68 (0.8 * 0.85)
"""


