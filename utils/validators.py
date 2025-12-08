# utils/validators.py
"""
Validation utilities for email, etc.
"""

import re

EMAIL_REGEX = re.compile(r"^[^\@\s]+@[^\@\s]+\.[^\@\s]+$")


def is_valid_email(email: str) -> bool:
    """Validate email format (basic regex check)."""
    return bool(EMAIL_REGEX.match(email.strip()))
