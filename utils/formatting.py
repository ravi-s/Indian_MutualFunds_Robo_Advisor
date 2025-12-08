# utils/formatting.py
"""
Formatting utilities for currency, percentages, etc.
"""

import locale

try:
    locale.setlocale(locale.LC_MONETARY, "en_IN")
except Exception:
    # Fallback – formatting will still work, just without full Indian locale grouping
    pass


def format_percentage(value: float) -> str:
    """Format value as percentage with 2 decimal places."""
    return f"{float(value):.2f}%"


def format_crores(value: float) -> str:
    """Format value as crores (Indian currency notation)."""
    return f"₹{locale.format_string('%d', float(value), grouping=True)} Cr."


def format_currency(value: float) -> str:
    """Format value as Indian currency (₹)."""
    return f"₹{locale.format_string('%d', float(value), grouping=True)}"
