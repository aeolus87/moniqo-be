"""
Monitor Agent

Monitors open positions and market conditions.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone

from app.modules.ai_agents.base_agent import BaseAgent, AgentRole, AgentStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MonitorAgent(BaseAgent):
    """
    Monitor Agent
    
    Monitors positions and market conditions in real-time.
    
    Responsibilities:
    - Monitor open positions
    - Assess position health
    - Trigger stop-loss/take-profit decisions
    - Alert on risk breaches
    - Recommend position adjustments
    
    Usage:
        agent = MonitorAgent(
            model_provider="gemini",
            api_key="your_key"
        )
        
        result = await agent.process({
            "positions": [...],
            "market_data": {...}
        })
    """
    
    def __init__(self, **kwargs):
        """Initialize Monitor Agent"""
        super().__init__(
            role=AgentRole.MONITOR,
            **kwargs
        )
        
        logger.info("Monitor Agent initialized")
    
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor positions and generate recommendations.
        
        Args:
            context: Context with positions, market data
            
        Returns:
            Dict with monitoring result:
            {
                "positions_checked": 3,
                "alerts": [...],
                "recommendations": [...],
                "risk_breaches": [...]
            }
        """
        try:
            self.status = AgentStatus.ANALYZING
            
            positions = context.get("positions", [])
            market_data = context.get("market_data", {})
            
            # Build monitoring prompt
            prompt = self._build_monitoring_prompt(positions, market_data)
            system_prompt = self._get_system_prompt()
            
            # Get structured monitoring result
            schema = {
                "type": "object",
                "properties": {
                    "positions_checked": {
                        "type": "integer"
                    },
                    "alerts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "position_id": {"type": "string"},
                                "alert_type": {"type": "string"},
                                "message": {"type": "string"},
                                "urgency": {"type": "string"}
                            }
                        }
                    },
                    "recommendations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "position_id": {"type": "string"},
                                "action": {"type": "string"},
                                "reason": {"type": "string"}
                            }
                        }
                    },
                    "risk_breaches": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["positions_checked"]
            }
            
            # Generate monitoring result
            result = await self.analyze(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                structured=True,
                schema=schema
            )
            
            self.status = AgentStatus.COMPLETED
            
            alerts_count = len(result.get("alerts", []))
            logger.info(
                f"Monitor: Checked {result.get('positions_checked', 0)} positions, "
                f"{alerts_count} alerts"
            )
            
            return {
                "success": True,
                "agent": self.role.value,
                "timestamp": datetime.now(timezone.utc),
                **result
            }
        
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Monitor agent failed: {str(e)}")
            return {
                "success": False,
                "agent": self.role.value,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            }
    
    def _build_monitoring_prompt(
        self,
        positions: List[Dict[str, Any]],
        market_data: Dict[str, Any]
    ) -> str:
        """Build monitoring prompt"""
        prompt = f"""
Monitor the following positions and identify any issues or opportunities.

**Open Positions ({len(positions)}):**
"""
        
        for pos in positions:
            prompt += f"""
- Position ID: {pos.get('id', 'N/A')}
  Symbol: {pos.get('symbol', 'N/A')}
  Side: {pos.get('side', 'N/A')}
  Entry Price: ${pos.get('entry_price', 'N/A')}
  Current Price: ${pos.get('current_price', 'N/A')}
  Unrealized P&L: ${pos.get('unrealized_pnl', 'N/A')} ({pos.get('unrealized_pnl_percent', 0)}%)
  Risk Level: {pos.get('risk_level', 'N/A')}
  Stop Loss: ${pos.get('stop_loss', 'N/A')}
  Take Profit: ${pos.get('take_profit', 'N/A')}
"""
        
        prompt += f"""
**Market Data:**
- Current Market Conditions: {market_data.get('summary', 'N/A')}

**Your Task:**
1. Check each position for risk breaches
2. Identify stop-loss/take-profit triggers
3. Assess position health
4. Generate alerts for urgent issues
5. Provide recommendations for position adjustments

Be vigilant about risk management.
"""
        
        return prompt
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for monitor agent"""
        return """You are a vigilant position monitor for a cryptocurrency trading platform.

Your responsibilities:
- Continuously monitor all open positions
- Identify risk breaches immediately
- Alert on stop-loss/take-profit triggers
- Assess position health
- Recommend position adjustments

Guidelines:
- Be proactive with alerts
- Prioritize risk management
- Consider market conditions
- Be specific with recommendations
- Mark urgency levels appropriately

Priority: Risk prevention > Profit optimization
"""


