# utils/formatting.py
"""
Formatting utilities for currency, percentages, etc.
"""

import locale
from typing import Optional

try:
    locale.setlocale(locale.LC_MONETARY, "en_IN")
except Exception:
    # Fallback – formatting will still work, just without full Indian locale grouping
    pass


def format_percentage(value: Optional[float]) -> str:
    """Format value as percentage with 2 decimal places."""
    if value is None:
        return "N/A"
    return f"{float(value):.2f}%"


def format_crores(value: Optional[float]) -> str:
    """Format value as crores (Indian currency notation)."""
    if value is None:
        return "₹0 Cr."
    return f"₹{locale.format_string('%d', float(value), grouping=True)} Cr."


def format_currency(value: Optional[float]) -> str:
    """Format value as Indian currency (₹)."""
    if value is None:
        return "₹0"
    return f"₹{locale.format_string('%d', float(value), grouping=True)}"
