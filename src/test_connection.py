import os
from solace.messaging.messaging_service import MessagingService

import config


def main():
    config.validate_config()

    print(f"Conectando a {config.SOLACE_HOST} (VPN: {config.SOLACE_VPN})...")
    print("Trust store path:", config.SOLACE_TRUST_STORE_PATH)
    print("Existe la carpeta?:", os.path.exists(config.SOLACE_TRUST_STORE_PATH))

    messaging_service = MessagingService.builder().from_properties({
        "solace.messaging.transport.host": config.SOLACE_HOST,
        "solace.messaging.service.vpn-name": config.SOLACE_VPN,
        "solace.messaging.authentication.scheme.basic.username": config.SOLACE_USERNAME,
        "solace.messaging.authentication.scheme.basic.password": config.SOLACE_PASSWORD,
        "solace.messaging.tls.trust-store-path": config.SOLACE_TRUST_STORE_PATH,
    }).build()

    try:
        messaging_service.connect()
        print("¡Conexión exitosa al broker de Solace Cloud!")
    except Exception as e:
        print(f" Error al conectar: {e}")
    finally:
        messaging_service.disconnect()
        print("Conexión cerrada.")


if __name__ == "__main__":
    main()