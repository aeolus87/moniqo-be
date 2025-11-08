"""Utility functions package."""

from app.utils.logger import setup_logging, get_logger, app_logger
from app.utils.pagination import (
    get_pagination_params,
    calculate_has_more,
    calculate_total_pages,
    calculate_page_number,
    PaginationHelper,
)
from app.utils.validators import (
    validate_password_strength,
    validate_phone_number,
    validate_birthday,
    validate_object_id,
    validate_email_lowercase,
    validate_non_empty_string,
    validate_positive_number,
    validate_non_negative_number,
)
from app.utils.cache import (
    get_redis_client,
    close_redis_connection,
    generate_cache_key,
    get_cache,
    set_cache,
    delete_cache,
    delete_cache_pattern,
    cache_exists,
    get_cache_ttl,
    CacheManager,
)

__all__ = [
    # Logger
    "setup_logging",
    "get_logger",
    "app_logger",
    # Pagination
    "get_pagination_params",
    "calculate_has_more",
    "calculate_total_pages",
    "calculate_page_number",
    "PaginationHelper",
    # Validators
    "validate_password_strength",
    "validate_phone_number",
    "validate_birthday",
    "validate_object_id",
    "validate_email_lowercase",
    "validate_non_empty_string",
    "validate_positive_number",
    "validate_non_negative_number",
    # Cache
    "get_redis_client",
    "close_redis_connection",
    "generate_cache_key",
    "get_cache",
    "set_cache",
    "delete_cache",
    "delete_cache_pattern",
    "cache_exists",
    "get_cache_ttl",
    "CacheManager",
]

