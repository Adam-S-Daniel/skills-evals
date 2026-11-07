"""Money helpers. Amounts are Decimal; never float."""
from decimal import Decimal


def parse_amount(text):
    """'12.50' or '$12.50' -> Decimal('12.50')."""
    return Decimal(text.strip().lstrip("$").replace(",", ""))


def format_amount(amount):
    """Decimal('1234.5') -> '$1,234.50'."""
    return f"${amount:,.2f}"
