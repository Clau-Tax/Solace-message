from datetime import datetime, date

CUTOFF_HOUR = 15  # 3:00 p.m.


def validate_request(payload: dict, now: datetime = None):
    """
    Valida:
    1) pickupDate no puede ser anterior a hoy.
    2) Si pickupDate == hoy, la solicitud debe llegar antes de las 3:00 p.m.
    3) deliveryDate debe ser posterior a pickupDate, con al menos 1 día de diferencia.

    Retorna (True, None) si es válido,
    o (False, "motivo en inglés, como en el ejemplo del enunciado") si no.
    """
    if now is None:
        now = datetime.now()

    try:
        pickup_date = datetime.strptime(payload["pickupDate"], "%Y-%m-%d").date()
        delivery_date = datetime.strptime(payload["deliveryDate"], "%Y-%m-%d").date()
    except (KeyError, ValueError):
        return False, "Invalid or missing pickupDate/deliveryDate in payload."

    today = now.date()

    # Regla 1: pickup no puede ser antes de hoy
    if pickup_date < today:
        return False, "Pickup date cannot be earlier than the current date."

    # Regla 2: si pickup es hoy, la solicitud debe llegar antes de las 3pm
    if pickup_date == today and now.hour >= CUTOFF_HOUR:
        return False, (
            "Pickup date is today, but the request was received after "
            "3:00 p.m. No driver can commit to same-day pickup this late."
        )

    # Regla 3: delivery debe ser al menos 1 día después de pickup
    if (delivery_date - pickup_date).days < 1:
        return False, "Delivery date must be at least one day after the pickup date."

    return True, None
