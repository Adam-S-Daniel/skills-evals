"""Shipping rates. Zones: 1 local, 2 national, 3 international."""

ZONE_RATE = {1: 2.0, 2: 4.5, 3: 11.0}


def calc_fee(weight_kg, zone):
    """Fee in dollars for a parcel of weight_kg going to zone."""
    return round(ZONE_RATE[zone] * weight_kg, 2)
