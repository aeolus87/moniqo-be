"""
Position Service

Business logic for position management.
Uses repositories for data access - no direct database access.
"""

from typing import Optional, List
from decimal import Decimal

from app.domain.models.position import Position, PositionStatus, PositionSide
from app.modules.positions.repository import PositionRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PositionService:
    """
    Position Service
    
    Handles position business logic:
    - Position creation
    - Price updates
    - Position closing
    - P&L calculations
    """
    
    def __init__(self, repository: PositionRepository):
        """
        Initialize position service.
        
        Args:
            repository: Position repository instance
        """
        self.repository = repository
    
    async def create_position(
        self,
        user_id: str,
        user_wallet_id: str,
        symbol: str,
        side: PositionSide,
        entry: dict,
        flow_id: Optional[str] = None,
        risk_management: Optional[dict] = None,
        ai_monitoring: Optional[dict] = None
    ) -> Position:
        """
        Create a new position.
        
        Args:
            user_id: User ID
            user_wallet_id: User wallet ID
            symbol: Trading pair (e.g., "BTC/USDT")
            side: Position side (LONG/SHORT)
            entry: Entry data dictionary with price, amount, value, etc.
            flow_id: Optional flow ID
            risk_management: Optional risk management settings
            ai_monitoring: Optional AI monitoring settings
            
        Returns:
            Created Position
        """
        position = Position(
            user_id=user_id,
            user_wallet_id=user_wallet_id,
            symbol=symbol,
            side=side,
            entry=entry,
            flow_id=flow_id,
            risk_management=risk_management or {},
            ai_monitoring=ai_monitoring or {},
            status=PositionStatus.OPENING
        )
        
        # Save via repository (automatically routes to correct DB)
        position = await self.repository.save(position)
        
        logger.info(f"Position {position.id} created for user {user_id}")
        
        return position
    
    async def get_position(self, position_id: str) -> Optional[Position]:
        """
        Get position by ID.
        
        Args:
            position_id: Position ID
            
        Returns:
            Position or None if not found
        """
        return await self.repository.find_by_id(position_id)
    
    async def get_user_positions(
        self,
        user_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Position]:
        """
        Get positions for a user.
        
        Args:
            user_id: User ID
            status: Optional status filter
            symbol: Optional symbol filter
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            
        Returns:
            List of positions
        """
        return await self.repository.find_by_user(
            user_id=user_id,
            status=status,
            symbol=symbol,
            skip=skip,
            limit=limit
        )
    
    async def get_open_positions(self, user_id: str) -> List[Position]:
        """
        Get all open positions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of open positions
        """
        return await self.repository.find_open_positions(user_id)
    
    async def update_price(
        self,
        position_id: str,
        current_price: Decimal
    ) -> Position:
        """
        Update position price and recalculate P&L.
        
        Args:
            position_id: Position ID
            current_price: Current market price
            
        Returns:
            Updated position
            
        Raises:
            ValueError: If position not found
        """
        position = await self.repository.find_by_id(position_id)
        if not position:
            raise ValueError(f"Position not found: {position_id}")
        
        # Update price (domain logic)
        position.update_price(current_price)
        
        # Save via repository
        position = await self.repository.save(position)
        
        logger.debug(f"Position {position_id} price updated to {current_price}")
        
        return position
    
    async def close_position(
        self,
        position_id: str,
        order_id: str,
        price: Decimal,
        reason: str,
        fees: Decimal = Decimal("0"),
        fee_currency: str = "USDT"
    ) -> Position:
        """
        Close a position.
        
        Args:
            position_id: Position ID
            order_id: Exit order ID
            price: Exit price
            reason: Close reason ("take_profit", "stop_loss", "manual", etc.)
            fees: Exit fees
            fee_currency: Fee currency
            
        Returns:
            Updated position
            
        Raises:
            ValueError: If position not found
        """
        position = await self.repository.find_by_id(position_id)
        if not position:
            raise ValueError(f"Position not found: {position_id}")
        
        # Close position (domain logic)
        position.close(
            order_id=order_id,
            price=price,
            reason=reason,
            fees=fees,
            fee_currency=fee_currency
        )
        
        # Save via repository
        position = await self.repository.save(position)
        
        logger.info(
            f"Position {position_id} closed: reason={reason}, "
            f"realized_pnl={position.exit.get('realized_pnl') if position.exit else 0}"
        )
        
        return position
    
    async def mark_as_open(self, position_id: str) -> Position:
        """
        Mark position as open (entry order filled).
        
        Args:
            position_id: Position ID
            
        Returns:
            Updated position
            
        Raises:
            ValueError: If position not found
        """
        position = await self.repository.find_by_id(position_id)
        if not position:
            raise ValueError(f"Position not found: {position_id}")
        
        position.status = PositionStatus.OPEN
        position.opened_at = position.created_at
        position.updated_at = position.created_at
        
        position = await self.repository.save(position)
        
        logger.info(f"Position {position_id} marked as open")
        
        return position
