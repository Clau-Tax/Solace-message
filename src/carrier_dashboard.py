import json
import threading

from flask import Flask, jsonify, render_template, request

from solace.messaging.resources.queue import Queue
from solace.messaging.resources.topic import Topic
from solace.messaging.receiver.message_receiver import MessageHandler

import config
from solace_utils import build_messaging_service

app = Flask(__name__)

# Estado en memoria compartido entre el hilo de Solace y las rutas Flask
_lock = threading.Lock()
available_loads = {}  # shipperOrderId -> payload dict

# Se inicializan en main()
messaging_service = None
publisher = None
receiver = None  # se guarda en global para que no lo recoja el garbage collector
handler = None


class CarrierLoadsHandler(MessageHandler):
    """Cada carga válida que llega a la cola se guarda en memoria."""

    def __init__(self, receiver):
        self.receiver = receiver

    def on_message(self, message):
        raw_text = message.get_payload_as_string()
        try:
            payload = json.loads(raw_text)
            order_id = payload.get("shipperOrderId", "UNKNOWN")
            with _lock:
                available_loads[order_id] = payload
            print(f" Nueva carga disponible: {order_id}")
        except json.JSONDecodeError:
            print("❌ Mensaje no es JSON válido, se descarta.")
        finally:
            self.receiver.ack(message)


def start_solace_listener():
    """Conecta a Solace y arranca el consumidor de cargas disponibles."""
    global messaging_service, publisher, receiver, handler

    messaging_service = build_messaging_service()
    print(" Dashboard conectado a Solace.")

    publisher = messaging_service.create_direct_message_publisher_builder().build()
    publisher.start()

    queue = Queue.durable_exclusive_queue(config.QUEUE_CARRIER_AVAILABLE_LOADS)
    receiver = messaging_service.create_persistent_message_receiver_builder().build(queue)
    receiver.start()

    handler = CarrierLoadsHandler(receiver)
    receiver.receive_async(handler)
    print(f"👂 Escuchando cargas disponibles en '{config.QUEUE_CARRIER_AVAILABLE_LOADS}'...")


@app.route("/")
def index():
    return render_template("carrier_dashboard.html")


@app.route("/api/loads")
def api_loads():
    with _lock:
        loads = list(available_loads.values())
    return jsonify(loads)


@app.route("/api/loads/<order_id>/accept", methods=["POST"])
def accept_load(order_id):
    carrier_name = request.json.get("carrierName", "Unknown carrier") if request.is_json else "Unknown carrier"

    with _lock:
        payload = available_loads.pop(order_id, None)

    if payload is None:
        return jsonify({"error": "Load not found or already taken"}), 404

    # Avisar por Solace que esta carga fue aceptada por un transportista
    accepted_event = {
        "shipperOrderId": order_id,
        "status": "CarrierAccepted",
        "carrierName": carrier_name,
        "notes": f"Load accepted by {carrier_name}",
    }
    outbound_message = messaging_service.message_builder().build(json.dumps(accepted_event))
    publisher.publish(destination=Topic.of(config.TOPIC_CARRIER_ACCEPTED), message=outbound_message)

    print(f" Carga {order_id} aceptada por {carrier_name}. Evento publicado a Solace.")
    return jsonify({"ok": True})


if __name__ == "__main__":
    start_solace_listener()
    app.run(host="127.0.0.1", port=5001, debug=False)