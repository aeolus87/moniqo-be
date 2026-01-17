"""
Risk Manager Agent

Manages risk and validates trading decisions before execution.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone

from app.modules.ai_agents.base_agent import BaseAgent, AgentRole, AgentStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RiskManagerAgent(BaseAgent):
    """
    Risk Manager Agent
    
    Validates trading decisions and manages risk limits.
    
    Responsibilities:
    - Validate order requests against risk limits
    - Check position sizes
    - Monitor daily loss limits
    - Assess portfolio risk
    - Approve or reject trades
    
    Usage:
        agent = RiskManagerAgent(
            model_provider="gemini",
            api_key="your_key"
        )
        
        result = await agent.process({
            "order_request": {...},
            "current_positions": [...],
            "risk_limits": {...}
        })
    """
    
    def __init__(self, **kwargs):
        """Initialize Risk Manager Agent"""
        super().__init__(
            role=AgentRole.RISK_MANAGER,
            **kwargs
        )
        
        logger.info("Risk Manager Agent initialized")
    
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate trading decision against risk limits.
        
        Args:
            context: Context with order request, positions, risk limits
            
        Returns:
            Dict with validation result:
            {
                "approved": True | False,
                "reason": "...",
                "risk_score": 0.0-1.0,
                "adjustments": {...}  # Suggested adjustments if rejected
            }
        """
        try:
            self.status = AgentStatus.ANALYZING
            
            order_request = context.get("order_request", {})
            current_positions = context.get("current_positions", [])
            risk_limits = context.get("risk_limits", {})
            portfolio_balance = context.get("portfolio_balance", Decimal("0"))
            
            # Build risk analysis prompt
            prompt = self._build_risk_analysis_prompt(
                order_request,
                current_positions,
                risk_limits,
                portfolio_balance
            )
            system_prompt = self._get_system_prompt()
            
            # Get structured risk assessment
            schema = {
                "type": "object",
                "properties": {
                    "approved": {
                        "type": "boolean"
                    },
                    "reason": {
                        "type": "string"
                    },
                    "risk_score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "adjustments": {
                        "type": "object",
                        "properties": {
                            "suggested_quantity": {"type": "number"},
                            "suggested_stop_loss": {"type": "number"},
                            "suggested_take_profit": {"type": "number"}
                        }
                    },
                    "risk_factors": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["approved", "reason", "risk_score"]
            }
            
            # Generate risk assessment
            assessment = await self.analyze(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for risk decisions
                structured=True,
                schema=schema
            )
            
            self.status = AgentStatus.COMPLETED
            
            action = "APPROVED" if assessment.get("approved") else "REJECTED"
            logger.info(
                f"Risk Manager: Order {action} "
                f"(risk_score: {assessment.get('risk_score', 0):.2f})"
            )
            
            return {
                "success": True,
                "agent": self.role.value,
                "timestamp": datetime.now(timezone.utc),
                **assessment
            }
        
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Risk Manager validation failed: {str(e)}")
            return {
                "success": False,
                "agent": self.role.value,
                "approved": False,  # Default to reject on error
                "reason": f"Validation error: {str(e)}",
                "timestamp": datetime.now(timezone.utc)
            }
    
    def _build_risk_analysis_prompt(
        self,
        order_request: Dict[str, Any],
        positions: List[Dict[str, Any]],
        risk_limits: Dict[str, Any],
        balance: Decimal
    ) -> str:
        """Build risk analysis prompt"""
        prompt = f"""
Analyze the risk of this trading order request and decide if it should be approved.

**Order Request:**
- Symbol: {order_request.get('symbol', 'N/A')}
- Side: {order_request.get('side', 'N/A')}
- Type: {order_request.get('order_type', 'N/A')}
- Quantity: {order_request.get('quantity', 'N/A')}
- Price: {order_request.get('price', 'N/A')}
- Estimated Value: ${order_request.get('estimated_value', 'N/A')}

**Current Portfolio:**
- Total Balance: ${balance}
- Number of Open Positions: {len(positions)}
"""
        
        if positions:
            total_position_value = sum(
                Decimal(str(p.get("current_value", 0)))
                for p in positions
            )
            prompt += f"- Total Position Value: ${total_position_value}\n"
            utilization = (total_position_value / balance * 100) if balance > 0 else Decimal("0")
            prompt += f"- Portfolio Utilization: {float(utilization):.1f}%\n"
        
        prompt += f"""
**Risk Limits:**
- Max Position Size: ${risk_limits.get('max_position_size_usd', 'N/A')}
- Max Position Percentage: {risk_limits.get('max_position_percent', 'N/A')}%
- Daily Loss Limit: ${risk_limits.get('daily_loss_limit', 'N/A')}
- Max Portfolio Utilization: {risk_limits.get('max_portfolio_utilization', 'N/A')}%
- Max Open Positions: {risk_limits.get('max_open_positions', 'N/A')}

**Your Task:**
1. Validate the order against all risk limits
2. Assess portfolio risk exposure
3. Calculate risk score (0.0 = low risk, 1.0 = high risk)
4. Approve or reject the order
5. If rejected, suggest adjustments

Be strict with risk limits. Safety first.
"""
        
        return prompt
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for risk manager"""
        return """You are a strict risk manager for a cryptocurrency trading platform.

Your responsibilities:
- Enforce all risk limits strictly
- Protect capital at all costs
- Assess portfolio risk comprehensively
- Reject risky trades without hesitation
- Suggest safer alternatives when rejecting trades

Guidelines:
- NEVER approve trades that exceed risk limits
- Consider portfolio concentration risk
- Assess correlation between positions
- Calculate maximum possible loss
- Be conservative with risk scores

Priority: Capital preservation > Profit maximization
"""


