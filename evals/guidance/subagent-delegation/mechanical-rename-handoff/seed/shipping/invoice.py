from shipping.rates import calc_fee


def invoice_line(order_id, weight_kg, zone):
    return f"{order_id}: shipping {calc_fee(weight_kg, zone):.2f}"
