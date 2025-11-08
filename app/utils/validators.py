"""
Custom Pydantic validators for application models.

Provides reusable validators for common validation scenarios.
"""

import re
from typing import Any
from datetime import datetime


def validate_password_strength(password: str) -> str:
    """
    Validate password strength.
    
    Requirements:
    - At least 8 characters
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    
    Args:
        password: Password to validate
        
    Returns:
        str: Validated password
        
    Raises:
        ValueError: If password doesn't meet requirements
        
    Example:
        >>> validate_password_strength("StrongPass123!")
        "StrongPass123!"
        >>> validate_password_strength("weak")
        ValueError: Password must be at least 8 characters long
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("Password must contain at least one special character")
    
    return password


def validate_phone_number(phone_data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate phone number data.
    
    Ensures that country_code and mobile_number are both present or both absent.
    
    Args:
        phone_data: Dictionary with country_code and mobile_number
        
    Returns:
        dict: Validated phone data
        
    Raises:
        ValueError: If only one of country_code/mobile_number is provided
        
    Example:
        >>> validate_phone_number({"country_code": "+63", "mobile_number": "9171234567"})
        {"country_code": "+63", "mobile_number": "9171234567"}
        >>> validate_phone_number({"country_code": "+63", "mobile_number": None})
        ValueError: Both country_code and mobile_number must be provided together
    """
    country_code = phone_data.get("country_code")
    mobile_number = phone_data.get("mobile_number")
    
    # Both must be present or both must be absent
    if (country_code and not mobile_number) or (mobile_number and not country_code):
        raise ValueError(
            "Both country_code and mobile_number must be provided together or both omitted"
        )
    
    return phone_data


def validate_birthday(birthday_data: dict[str, int]) -> dict[str, int]:
    """
    Validate birthday data.
    
    Ensures day, month, and year are valid date values.
    
    Args:
        birthday_data: Dictionary with day, month, year
        
    Returns:
        dict: Validated birthday data
        
    Raises:
        ValueError: If birthday values are invalid
        
    Example:
        >>> validate_birthday({"day": 15, "month": 6, "year": 1990})
        {"day": 15, "month": 6, "year": 1990}
        >>> validate_birthday({"day": 32, "month": 6, "year": 1990})
        ValueError: Invalid day: must be between 1 and 31
    """
    day = birthday_data.get("day")
    month = birthday_data.get("month")
    year = birthday_data.get("year")
    
    # Validate month
    if month is None or month < 1 or month > 12:
        raise ValueError("Invalid month: must be between 1 and 12")
    
    # Validate day
    if day is None or day < 1 or day > 31:
        raise ValueError("Invalid day: must be between 1 and 31")
    
    # Validate year (reasonable range)
    current_year = datetime.now().year
    if year is None or year < 1900 or year > current_year:
        raise ValueError(f"Invalid year: must be between 1900 and {current_year}")
    
    # Additional validation: check if date is valid
    try:
        datetime(year=year, month=month, day=day)
    except ValueError as e:
        raise ValueError(f"Invalid date: {str(e)}")
    
    # Check if user is at least 13 years old (COPPA compliance)
    age = current_year - year
    birth_date = datetime(year=year, month=month, day=day)
    today = datetime.now()
    
    if birth_date.month > today.month or (birth_date.month == today.month and birth_date.day > today.day):
        age -= 1
    
    if age < 13:
        raise ValueError("User must be at least 13 years old")
    
    return birthday_data


def validate_object_id(value: str) -> str:
    """
    Validate MongoDB ObjectId format.
    
    Args:
        value: ObjectId string to validate
        
    Returns:
        str: Validated ObjectId string
        
    Raises:
        ValueError: If ObjectId format is invalid
        
    Example:
        >>> validate_object_id("507f1f77bcf86cd799439011")
        "507f1f77bcf86cd799439011"
        >>> validate_object_id("invalid")
        ValueError: Invalid ObjectId format
    """
    # ObjectId is a 24-character hexadecimal string
    if not re.match(r"^[a-f0-9]{24}$", value):
        raise ValueError("Invalid ObjectId format")
    
    return value


def validate_email_lowercase(email: str) -> str:
    """
    Convert email to lowercase for consistency.
    
    Args:
        email: Email address
        
    Returns:
        str: Lowercase email address
        
    Example:
        >>> validate_email_lowercase("User@Example.COM")
        "user@example.com"
    """
    return email.lower().strip()


def validate_non_empty_string(value: str, field_name: str = "Field") -> str:
    """
    Validate that string is not empty or whitespace-only.
    
    Args:
        value: String to validate
        field_name: Name of the field (for error message)
        
    Returns:
        str: Validated string (stripped)
        
    Raises:
        ValueError: If string is empty or whitespace-only
        
    Example:
        >>> validate_non_empty_string("  hello  ", "name")
        "hello"
        >>> validate_non_empty_string("   ", "name")
        ValueError: name cannot be empty
    """
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} cannot be empty")
    return stripped


def validate_positive_number(value: int | float, field_name: str = "Field") -> int | float:
    """
    Validate that number is positive.
    
    Args:
        value: Number to validate
        field_name: Name of the field (for error message)
        
    Returns:
        int | float: Validated number
        
    Raises:
        ValueError: If number is not positive
        
    Example:
        >>> validate_positive_number(10, "price")
        10
        >>> validate_positive_number(-5, "price")
        ValueError: price must be positive
    """
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value


def validate_non_negative_number(value: int | float, field_name: str = "Field") -> int | float:
    """
    Validate that number is non-negative (>= 0).
    
    Args:
        value: Number to validate
        field_name: Name of the field (for error message)
        
    Returns:
        int | float: Validated number
        
    Raises:
        ValueError: If number is negative
        
    Example:
        >>> validate_non_negative_number(0, "quantity")
        0
        >>> validate_non_negative_number(-5, "quantity")
        ValueError: quantity cannot be negative
    """
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return value

