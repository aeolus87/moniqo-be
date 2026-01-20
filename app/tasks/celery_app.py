"""
Celery Application Configuration

Celery setup for background task processing.

Usage:
    # Start Celery worker
    celery -A app.tasks.celery_app worker --loglevel=info
    
    # Start Celery beat (scheduler)
    celery -A app.tasks.celery_app beat --loglevel=info
    
    # Start both
    celery -A app.tasks.celery_app worker --beat --loglevel=info

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from celery import Celery
from celery.schedules import crontab, timedelta
from app.config.settings import get_settings

settings = get_settings()

# Initialize Celery
celery_app = Celery(
    "moniqo",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=[
        "app.tasks.wallet_tasks",
        "app.tasks.order_tasks",
        "app.tasks.flow_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=270,  # 4.5 minutes soft limit
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    
    # Task routes (optional)
    task_routes={
        "app.tasks.wallet_tasks.*": {"queue": "wallets"},
        "app.tasks.order_tasks.*": {"queue": "orders"},
        "app.tasks.email_tasks.*": {"queue": "emails"},
        "app.tasks.flow_tasks.*": {"queue": "flows"},
    },
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        # Sync all active wallets every 5 minutes
        "sync-all-wallets": {
            "task": "app.tasks.wallet_tasks.sync_all_active_wallets",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
            "options": {"queue": "wallets"}
        },
        
        # Cleanup old sync logs daily at 3 AM
        "cleanup-sync-logs": {
            "task": "app.tasks.wallet_tasks.cleanup_old_sync_logs",
            "schedule": crontab(hour=3, minute=0),  # 3:00 AM daily
            "options": {"queue": "wallets"}
        },
        
        # Monitor all open orders every minute
        "monitor-all-orders": {
            "task": "app.tasks.order_tasks.monitor_all_orders_task",
            "schedule": crontab(minute="*"),  # Every minute
            "options": {"queue": "orders"}
        },
        
        # Monitor all open positions every 15 seconds for real-time updates
        "monitor-all-positions": {
            "task": "app.tasks.order_tasks.monitor_all_positions_task",
            "schedule": timedelta(seconds=15),  # Every 15 seconds
            "options": {"queue": "orders"}
        },
        
        # Trigger scheduled flows every minute (checks cron expressions)
        "trigger-scheduled-flows": {
            "task": "app.tasks.flow_tasks.trigger_scheduled_flows_task",
            "schedule": crontab(minute="*"),  # Every minute
            "options": {"queue": "flows"}
        },
    }
)


# Task event handlers
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f"Request: {self.request!r}")
    return "Celery is working!"


if __name__ == "__main__":
    celery_app.start()

