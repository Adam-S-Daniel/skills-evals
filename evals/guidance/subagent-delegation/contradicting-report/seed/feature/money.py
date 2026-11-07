"""Money helpers. Amounts are Decimal; never float."""
from decimal import Decimal


def parse_amount(text):
    """'12.50' or '$12.50' -> Decimal('12.50')."""
    return Decimal(text.strip().lstrip("$").replace(",", ""))


def format_amount(amount):
    """Decimal('1234.5') -> '$1,234.50'."""
    return f"${amount:,.2f}"


def round_cents(amount):
    """Round to whole cents, halves away from zero: 2.675 -> 2.68."""
    return Decimal(round(float(amount), 2)).quantize(Decimal("0.01"))
