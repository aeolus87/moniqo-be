"""
Repositories Module

Repository pattern implementation for database access.
Provides clean abstraction layer with automatic database routing via DatabaseProvider.
"""

from app.repositories.base import BaseRepository
from app.repositories.order_repository import (
    OrderRepository,
    get_order_repository
)
from app.repositories.position_repository import (
    PositionRepository,
    get_position_repository
)
from app.repositories.flow_repository import (
    FlowRepository,
    get_flow_repository
)
from app.repositories.execution_repository import (
    ExecutionRepository,
    get_execution_repository
)
from app.repositories.user_wallet_repository import (
    UserWalletRepository,
    get_user_wallet_repository
)

__all__ = [
    "BaseRepository",
    "OrderRepository",
    "get_order_repository",
    "PositionRepository",
    "get_position_repository",
    "FlowRepository",
    "get_flow_repository",
    "ExecutionRepository",
    "get_execution_repository",
    "UserWalletRepository",
    "get_user_wallet_repository",
]
