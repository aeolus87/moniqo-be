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

__all__ = ["router"]
