"""
Repository implementations

All repositories with automatic database routing.
"""

from app.modules.orders.repository import (
    OrderRepository,
    get_order_repository
)
from app.modules.positions.repository import (
    PositionRepository,
    get_position_repository
)
from app.modules.flows.repository import (
    FlowRepository,
    get_flow_repository
)
from app.modules.flows.execution_repository import (
    ExecutionRepository,
    get_execution_repository
)
from app.modules.user_wallets.repository import (
    UserWalletRepository,
    get_user_wallet_repository
)

__all__ = [
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
