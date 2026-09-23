import os
from dotenv import load_dotenv

load_dotenv()

SOLACE_HOST = os.getenv("SOLACE_HOST")
SOLACE_VPN = os.getenv("SOLACE_VPN")
SOLACE_USERNAME = os.getenv("SOLACE_USERNAME")
SOLACE_PASSWORD = os.getenv("SOLACE_PASSWORD")

# Carpeta donde vas a poner el certificado Root CA PEM que descargaste
# de la pantalla "Connect with Python" de Solace Cloud.
SOLACE_TRUST_STORE_PATH = os.getenv(
    "SOLACE_TRUST_STORE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "certs")
)

# --- Nombres de tópicos (deben coincidir con las suscripciones en Solace Cloud) ---
TOPIC_REQUEST_NEW = "dispatch/request/new"          # cliente -> validador
TOPIC_CARRIER_AVAILABLE = "dispatch/carrier/available"  # validador -> dashboard transportistas
TOPIC_CLIENT_STATUS = "dispatch/client/status"          # validador -> panel cliente
TOPIC_CARRIER_ACCEPTED = "dispatch/carrier/accepted"    # dashboard -> aviso de carga aceptada

# --- Nombres de colas (deben coincidir EXACTO con las que creaste en Solace Cloud) ---
QUEUE_VALIDATOR_INCOMING = "Q.validator.incoming"
QUEUE_CARRIER_AVAILABLE_LOADS = "Q.carrier.available.loads"
QUEUE_CLIENT_STATUS = "Q.client.status"


def validate_config():
    missing = [
        name for name, value in [
            ("SOLACE_HOST", SOLACE_HOST),
            ("SOLACE_VPN", SOLACE_VPN),
            ("SOLACE_USERNAME", SOLACE_USERNAME),
            ("SOLACE_PASSWORD", SOLACE_PASSWORD),
        ] if not value
    ]
    if missing:
        raise RuntimeError(
            f"Faltan variables de entorno: {', '.join(missing)}. "
            f"Revisa tu archivo .env (usa .env.example como base)."
        )
