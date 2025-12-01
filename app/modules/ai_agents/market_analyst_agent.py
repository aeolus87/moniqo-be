"""
Market Analyst Agent

Analyzes market conditions and generates trading signals.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
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
            
            self.status = AgentStatus.COMPLETED
            
            logger.info(
                f"Market Analyst: {symbol} -> {analysis.get('action')} "
                f"(confidence: {analysis.get('confidence', 0):.2f})"
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
        
        prompt += """

**Your Task:**
1. Analyze the current market conditions
2. Evaluate technical indicators
3. Assess risk/reward ratio
4. Provide a clear trading recommendation (buy/sell/hold)
5. Suggest price targets, stop loss, and take profit levels

Be concise but thorough in your analysis.
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

Guidelines:
- Be conservative with confidence scores
- Always recommend stop-loss and take-profit levels
- Consider market volatility in your analysis
- Focus on data-driven decisions, not emotions
"""


