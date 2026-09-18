"""AMQP-klient til KOMBIT Beskedfordeleren."""

from __future__ import annotations

import base64
import ssl
from collections.abc import Generator

import pika
from pika.credentials import ExternalCredentials

from q_serviceplatformen.authentication import KombitAccess

PORT = 5671
VIRTUAL_HOST = "BF"
PROD_HOST = "beskedfordeler.stoettesystemerne.dk"
TEST_HOST = "beskedfordeler.eksterntest-stoettesystemerne.dk"
PROD_ENTITY_ID = (
    "http://beskedfordeler.prod-stoettesystemerne.dk/service/afhent/1"
)
TEST_ENTITY_ID = (
    "http://beskedfordeler.eksterntest-stoettesystemerne.dk/service/afhent/1"
)


class TokenCredentials(ExternalCredentials):
    """AMQP EXTERNAL credentials med SAML-token."""

    def __init__(self, token: bytes):
        super().__init__()
        self.token = token

    def response_for(self, start):
        """Returnerer token ved AMQP authentication challenge."""
        return self.TYPE, self.token


def _setup_pika_params(
    kombit_access: KombitAccess,
) -> pika.ConnectionParameters:
    """Returnerer TLS- og tokenkonfiguration til Beskedfordeleren."""
    entity_id = TEST_ENTITY_ID if kombit_access.test else PROD_ENTITY_ID
    saml_token = kombit_access.get_saml_token(entity_id)
    token = base64.b64decode(saml_token, validate=True)
    host = TEST_HOST if kombit_access.test else PROD_HOST
    ssl_context = ssl.create_default_context()
    return pika.ConnectionParameters(
        host=host,
        port=PORT,
        virtual_host=VIRTUAL_HOST,
        ssl_options=pika.SSLOptions(
            context=ssl_context,
            server_hostname=host,
        ),
        credentials=TokenCredentials(token=token),
        connection_attempts=1,
        retry_delay=0,
        socket_timeout=15,
        stack_timeout=20,
        blocked_connection_timeout=20,
        heartbeat=60,
    )


def iterate_queue_messages(
    queue_id: str,
    kombit_access: KombitAccess,
    auto_acknowledge: bool = True,
) -> Generator[bytes, None, None]:
    """Yielder beskeder fra det Dueslag, som queue_id peger på."""
    params = _setup_pika_params(kombit_access)
    with pika.BlockingConnection(parameters=params) as connection:
        channel = connection.channel()
        while True:
            method_frame, header_frame, body = channel.basic_get(
                queue_id,
                auto_ack=auto_acknowledge,
            )
            if not any((method_frame, header_frame, body)):
                return
            yield body
