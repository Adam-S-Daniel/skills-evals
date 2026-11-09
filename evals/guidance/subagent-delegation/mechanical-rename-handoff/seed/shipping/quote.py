from shipping.rates import calc_fee


def quote(weight_kg, zone):
    return {"fee": calc_fee(weight_kg, zone), "currency": "USD"}
