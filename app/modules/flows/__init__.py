"""
Flows Module

Trading automation flows management:
- Flow CRUD operations
- Flow execution and triggering
- Execution history tracking

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from app.modules.flows.router import router
from app.modules.flows.repository import FlowRepository, get_flow_repository
from app.modules.flows.execution_repository import ExecutionRepository, get_execution_repository

__all__ = [
    "router",
    "FlowRepository",
    "get_flow_repository",
    "ExecutionRepository",
    "get_execution_repository",
]
