"""
Pagination utilities for list endpoints.

Provides helper functions for consistent pagination across all list endpoints.
"""

from typing import Tuple, List, Any, Dict
from app.config.settings import settings


def get_pagination_params(
    limit: int | None = None,
    offset: int | None = None
) -> Tuple[int, int]:
    """
    Get validated pagination parameters.
    
    Ensures limit and offset are within acceptable ranges:
    - limit: Between 1 and MAX_PAGE_SIZE (default: DEFAULT_PAGE_SIZE)
    - offset: Non-negative (default: 0)
    
    Args:
        limit: Number of items per page (optional)
        offset: Number of items to skip (optional)
        
    Returns:
        Tuple[int, int]: Validated (limit, offset) tuple
        
    Example:
        >>> get_pagination_params(10, 0)
        (10, 0)
        >>> get_pagination_params(None, None)
        (10, 0)  # Uses defaults
        >>> get_pagination_params(10000, 0)
        (5000, 0)  # Capped at MAX_PAGE_SIZE
    """
    # Set default limit
    if limit is None:
        limit = settings.DEFAULT_PAGE_SIZE
    
    # Set default offset
    if offset is None:
        offset = 0
    
    # Validate and cap limit
    if limit <= 0:
        limit = settings.DEFAULT_PAGE_SIZE
    elif limit > settings.MAX_PAGE_SIZE:
        limit = settings.MAX_PAGE_SIZE
    
    # Validate offset
    if offset < 0:
        offset = 0
    
    return limit, offset


def calculate_has_more(
    total: int,
    limit: int,
    offset: int
) -> bool:
    """
    Calculate if there are more items beyond current page.
    
    Args:
        total: Total number of items
        limit: Items per page
        offset: Current offset
        
    Returns:
        bool: True if there are more items, False otherwise
        
    Example:
        >>> calculate_has_more(150, 10, 0)
        True
        >>> calculate_has_more(150, 10, 140)
        True
        >>> calculate_has_more(150, 10, 150)
        False
    """
    return (offset + limit) < total


def calculate_total_pages(
    total: int,
    limit: int
) -> int:
    """
    Calculate total number of pages.
    
    Args:
        total: Total number of items
        limit: Items per page
        
    Returns:
        int: Total number of pages
        
    Example:
        >>> calculate_total_pages(150, 10)
        15
        >>> calculate_total_pages(155, 10)
        16
        >>> calculate_total_pages(0, 10)
        0
    """
    if total == 0:
        return 0
    return (total + limit - 1) // limit  # Ceiling division


def calculate_page_number(
    offset: int,
    limit: int
) -> int:
    """
    Calculate current page number from offset.
    
    Args:
        offset: Current offset
        limit: Items per page
        
    Returns:
        int: Current page number (1-indexed)
        
    Example:
        >>> calculate_page_number(0, 10)
        1
        >>> calculate_page_number(10, 10)
        2
        >>> calculate_page_number(25, 10)
        3
    """
    if offset == 0:
        return 1
    return (offset // limit) + 1


def create_paginated_response(
    items: List[Any],
    total: int,
    limit: int,
    offset: int
) -> Dict[str, Any]:
    """
    Create a standardized paginated response.
    
    Args:
        items: List of items for current page
        total: Total number of items
        limit: Items per page
        offset: Current offset
        
    Returns:
        Dict[str, Any]: Paginated response with items and metadata
        
    Example:
        >>> items = [{"id": 1}, {"id": 2}]
        >>> create_paginated_response(items, 150, 10, 0)
        {
            "items": [{"id": 1}, {"id": 2}],
            "total": 150,
            "limit": 10,
            "offset": 0,
            "has_more": True
        }
    """
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": calculate_has_more(total, limit, offset)
    }


class PaginationHelper:
    """
    Helper class for pagination operations.
    
    Provides a convenient interface for working with pagination.
    
    Attributes:
        limit: Items per page
        offset: Items to skip
        total: Total number of items
    """
    
    def __init__(self, limit: int | None = None, offset: int | None = None):
        """
        Initialize PaginationHelper.
        
        Args:
            limit: Items per page (optional)
            offset: Items to skip (optional)
        """
        self.limit, self.offset = get_pagination_params(limit, offset)
        self.total: int = 0
    
    def set_total(self, total: int) -> None:
        """
        Set total number of items.
        
        Args:
            total: Total number of items
        """
        self.total = total
    
    def has_more(self) -> bool:
        """
        Check if there are more items beyond current page.
        
        Returns:
            bool: True if there are more items
        """
        return calculate_has_more(self.total, self.limit, self.offset)
    
    def total_pages(self) -> int:
        """
        Get total number of pages.
        
        Returns:
            int: Total number of pages
        """
        return calculate_total_pages(self.total, self.limit)
    
    def current_page(self) -> int:
        """
        Get current page number.
        
        Returns:
            int: Current page number (1-indexed)
        """
        return calculate_page_number(self.offset, self.limit)
    
    def get_pagination_dict(self) -> dict:
        """
        Get pagination information as dictionary.
        
        Returns:
            dict: Pagination information
            
        Example:
            >>> helper = PaginationHelper(10, 0)
            >>> helper.set_total(150)
            >>> helper.get_pagination_dict()
            {
                "total": 150,
                "limit": 10,
                "offset": 0,
                "has_more": True,
                "total_pages": 15,
                "current_page": 1
            }
        """
        return {
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
            "has_more": self.has_more(),
            "total_pages": self.total_pages(),
            "current_page": self.current_page()
        }

