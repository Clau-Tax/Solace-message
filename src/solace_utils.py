from solace.messaging.messaging_service import MessagingService

import config


def build_messaging_service() -> MessagingService:
    config.validate_config()

    messaging_service = MessagingService.builder().from_properties({
        "solace.messaging.transport.host": config.SOLACE_HOST,
        "solace.messaging.service.vpn-name": config.SOLACE_VPN,
        "solace.messaging.authentication.scheme.basic.username": config.SOLACE_USERNAME,
        "solace.messaging.authentication.scheme.basic.password": config.SOLACE_PASSWORD,
        "solace.messaging.tls.trust-store-path": config.SOLACE_TRUST_STORE_PATH,
    }).build()

    messaging_service.connect()
    return messaging_service
