import json
import time

from solace.messaging.resources.queue import Queue
from solace.messaging.resources.topic import Topic
from solace.messaging.receiver.message_receiver import MessageHandler

import config
from solace_utils import build_messaging_service
from validation import validate_request


class ValidatorMessageHandler(MessageHandler):
    def __init__(self, receiver, publisher, messaging_service):
        self.receiver = receiver
        self.publisher = publisher
        self.messaging_service = messaging_service

    def on_message(self, message):
        raw_text = message.get_payload_as_string()
        print(f"\n Solicitud recibida: {raw_text}")

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            print("Payload no es JSON válido, se descarta.")
            self.receiver.ack(message)
            return

        shipper_order_id = payload.get("shipperOrderId", "UNKNOWN")
        is_valid, reason = validate_request(payload)

        if is_valid:
            print(f" Solicitud {shipper_order_id} VÁLIDA. Publicando a transportistas...")

            # 1) Publicar la carga disponible para los transportistas
            self._publish_json(config.TOPIC_CARRIER_AVAILABLE, payload)

            # 2) Avisar al cliente que fue aceptada
            self._publish_json(config.TOPIC_CLIENT_STATUS, {
                "shipperOrderId": shipper_order_id,
                "status": "Accepted",
                "notes": "You will receive an email when a carrier accepts this dispatch request",
            })
        else:
            print(f"Solicitud {shipper_order_id} INVÁLIDA: {reason}")

            self._publish_json(config.TOPIC_CLIENT_STATUS, {
                "shipperOrderId": shipper_order_id,
                "status": "Cancelled",
                "notes": reason,
            })

        # Confirmamos que procesamos el mensaje (se borra de la cola)
        self.receiver.ack(message)

    def _publish_json(self, topic_name: str, data: dict):
        outbound_message = self.messaging_service.message_builder().build(json.dumps(data))
        self.publisher.publish(destination=Topic.of(topic_name), message=outbound_message)


def main():
    messaging_service = build_messaging_service()
    print(" Conectado a Solace. Iniciando validador...")

    # Publisher para mandar resultados a los tópicos
    publisher = messaging_service.create_direct_message_publisher_builder().build()
    publisher.start()

    # Receiver (consumidor) atado a la cola del validador
    queue = Queue.durable_exclusive_queue(config.QUEUE_VALIDATOR_INCOMING)
    receiver = messaging_service.create_persistent_message_receiver_builder().build(queue)
    receiver.start()

    handler = ValidatorMessageHandler(receiver, publisher, messaging_service)
    receiver.receive_async(handler)

    print(f" Escuchando solicitudes en la cola '{config.QUEUE_VALIDATOR_INCOMING}'...")
    print("Presiona Ctrl+C para detener.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCerrando validador...")
    finally:
        receiver.terminate()
        publisher.terminate()
        messaging_service.disconnect()


if __name__ == "__main__":
    main()
