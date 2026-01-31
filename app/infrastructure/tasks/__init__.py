"""
Celery Tasks Package

Background tasks for asynchronous operations:
- Wallet balance synchronization
- Email notifications
- Data cleanup
- Scheduled jobs

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from app.infrastructure.tasks.celery_app import celery_app

__all__ = ["celery_app"]
