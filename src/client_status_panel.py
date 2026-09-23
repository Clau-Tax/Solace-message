"""
Panel de clientes (Paso 6 del proyecto Global Dispatch).

- Consume la cola Q.client.status.
- Muestra en una página web el estado (Accepted/Cancelled) de cada
  solicitud enviada, en tiempo real (la página hace polling).

Cómo correrlo:
    python src/client_status_panel.py
Luego abre http://127.0.0.1:5002 en el navegador.
"""
import json
import threading

from flask import Flask, jsonify, render_template

from solace.messaging.resources.queue import Queue
from solace.messaging.receiver.message_receiver import MessageHandler

import config
from solace_utils import build_messaging_service

app = Flask(__name__)

_lock = threading.Lock()
# shipperOrderId -> último status conocido (se guarda el historial completo,
# más reciente al final, por si un mismo pedido cambia de estado)
status_by_order = {}

messaging_service = None
receiver = None
handler = None


class ClientStatusHandler(MessageHandler):
    """Cada resultado (Accepted/Cancelled) que llega se guarda en memoria."""

    def __init__(self, receiver):
        self.receiver = receiver

    def on_message(self, message):
        raw_text = message.get_payload_as_string()
        try:
            payload = json.loads(raw_text)
            order_id = payload.get("shipperOrderId", "UNKNOWN")
            with _lock:
                status_by_order[order_id] = payload
            print(f"📋 Estado actualizado: {order_id} -> {payload.get('status')}")
        except json.JSONDecodeError:
            print("❌ Mensaje no es JSON válido, se descarta.")
        finally:
            self.receiver.ack(message)


def start_solace_listener():
    global messaging_service, receiver, handler

    messaging_service = build_messaging_service()
    print("✅ Panel de clientes conectado a Solace.")

    queue = Queue.durable_exclusive_queue(config.QUEUE_CLIENT_STATUS)
    receiver = messaging_service.create_persistent_message_receiver_builder().build(queue)
    receiver.start()

    handler = ClientStatusHandler(receiver)
    receiver.receive_async(handler)
    print(f"👂 Escuchando resultados en '{config.QUEUE_CLIENT_STATUS}'...")


@app.route("/")
def index():
    return render_template("client_status_panel.html")


@app.route("/api/status")
def api_status():
    with _lock:
        # Más reciente primero
        results = list(reversed(list(status_by_order.values())))
    return jsonify(results)


if __name__ == "__main__":
    start_solace_listener()
    app.run(host="127.0.0.1", port=5002, debug=False)
