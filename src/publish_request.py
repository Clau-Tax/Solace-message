import json
from datetime import date, timedelta

from solace.messaging.resources.topic import Topic

import config
from solace_utils import build_messaging_service

# Payload de ejemplo (ajusta fechas para probar casos válidos/inválidos)
today = date.today()
sample_payload = {
    "shipperOrderId": "6600111",
    "pickupDate": str(today + timedelta(days=1)),      # mañana -> válido
    "deliveryDate": str(today + timedelta(days=2)),     # 1 día después de pickup -> válido
    "price": 900,
    "stops": [
        {"stopNumber": 1, "city": "Milford", "state": "MA", "postalCode": "01757"},
        {"stopNumber": 2, "city": "Shippensburg", "state": "PA", "postalCode": "17257"},
    ],
    "vehicles": [
        {"year": "2010", "make": "Toyota", "model": "Corolla"}
    ],
    "transportationReleaseNotes": (
        "Verify the pickup date; shipments cannot be delivered after 3:00 "
        "p.m. on the current date or on previous days."
    ),
}


def main():
    messaging_service = build_messaging_service()
    publisher = messaging_service.create_direct_message_publisher_builder().build()
    publisher.start()

    message = messaging_service.message_builder().build(json.dumps(sample_payload))
    publisher.publish(destination=Topic.of(config.TOPIC_REQUEST_NEW), message=message)

    print(f" Solicitud publicada en '{config.TOPIC_REQUEST_NEW}':")
    print(json.dumps(sample_payload, indent=2))

    publisher.terminate()
    messaging_service.disconnect()


if __name__ == "__main__":
    main()
