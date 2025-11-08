"""Configuration package for application settings and database connections."""

from app.config.settings import settings, Settings
from app.config.database import (
    connect_to_mongodb,
    close_mongodb_connection,
    get_database,
    get_db,
)

__all__ = [
    "settings",
    "Settings",
    "connect_to_mongodb",
    "close_mongodb_connection",
    "get_database",
    "get_db",
]

