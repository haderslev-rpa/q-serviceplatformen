"""Sikker AMQP-klient til KOMBIT Beskedfordeleren."""
from __future__ import annotations

import base64
import ssl
import uuid
from collections.abc import Generator
from typing import Any

import pika
from pika.credentials import ExternalCredentials

from q_serviceplatformen.authentication import KombitAccess
from q_serviceplatformen.configuration import get_message_broker_queue_id
from q_serviceplatformen.functionality.access import get_kombit_access
from q_serviceplatformen.functionality.post_models import BrokerMessage
from q_serviceplatformen.functionality.post_receipt import parse_post_receipt

PORT = 5671
VIRTUAL_HOST = "BF"
PROD_HOST = "beskedfordeler.stoettesystemerne.dk"
TEST_HOST = "beskedfordeler.eksterntest-stoettesystemerne.dk"
BESKEDMODTAG_ENTITY_ID = "http://entityid.kombit.dk/service/bfo_modtag/2"


class TokenCredentials(ExternalCredentials):
    """AMQP EXTERNAL credentials med SAML-token."""
    def __init__(self, token: bytes) -> None:
        super().__init__()
        self.token = token

    def response_for(self, start) -> tuple[str, bytes]:
        return self.TYPE, self.token


def _setup_pika_params(kombit_access: KombitAccess) -> pika.ConnectionParameters:
    """Byg interne Pika-parametre til Beskedfordeleren."""
    saml_token = kombit_access.get_saml_token(BESKEDMODTAG_ENTITY_ID)
    try:
        decoded_token = base64.b64decode(saml_token, validate=True)
    except (ValueError, TypeError) as error:
        raise RuntimeError("SAML-tokenet kunne ikke base64-dekodes.") from error
    if not decoded_token:
        raise RuntimeError("Det base64-dekodede SAML-token var tomt.")
    host = TEST_HOST if kombit_access.test else PROD_HOST
    ssl_options = pika.SSLOptions(ssl.create_default_context(), host)
    return pika.ConnectionParameters(
        host=host,
        port=PORT,
        virtual_host=VIRTUAL_HOST,
        ssl_options=ssl_options,
        credentials=TokenCredentials(decoded_token),
        connection_attempts=1,
        retry_delay=0,
        socket_timeout=15,
        stack_timeout=20,
        blocked_connection_timeout=20,
        heartbeat=60,
    )


class ReceivedBrokerMessage:
    """En hentet besked, som kan parses, godkendes eller lægges tilbage."""
    def __init__(self, channel: Any, message: BrokerMessage) -> None:
        self._channel = channel
        self._message = message
        self._settled = False

    @property
    def body(self) -> bytes:
        return self._message.body

    @property
    def delivery_tag(self) -> int:
        return self._message.delivery_tag

    @property
    def routing_key(self) -> str | None:
        return self._message.routing_key

    @property
    def redelivered(self) -> bool:
        return self._message.redelivered

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "delivery_tag": self.delivery_tag,
            "routing_key": self.routing_key,
            "redelivered": self.redelivered,
        }

    def parse_receipt(self):
        """Returnér beskedens body som en DigitalPostReceipt."""
        return parse_post_receipt(self.body)

    def ack(self) -> None:
        """Markér beskeden som færdigbehandlet og fjern den fra Dueslaget."""
        self._ensure_unsettled()
        self._channel.basic_ack(delivery_tag=self.delivery_tag)
        self._settled = True

    def requeue(self) -> None:
        """Læg beskeden tilbage i Dueslaget til senere behandling."""
        self._ensure_unsettled()
        self._channel.basic_nack(delivery_tag=self.delivery_tag, requeue=True)
        self._settled = True

    def reject(self) -> None:
        """Afvis beskeden uden at lægge den tilbage i Dueslaget."""
        self._ensure_unsettled()
        self._channel.basic_nack(delivery_tag=self.delivery_tag, requeue=False)
        self._settled = True

    def _ensure_unsettled(self) -> None:
        if self._settled:
            raise RuntimeError("Brokerbeskeden er allerede afsluttet.")


class MessageBroker:
    """Context manager, som ejer én kortlivet forbindelse til Dueslaget."""
    def __init__(
        self,
        queue_id: str | None = None,
        kombit_access: KombitAccess | None = None,
    ) -> None:
        self.queue_id = _validate_queue_id(queue_id or get_message_broker_queue_id())
        self.kombit_access = kombit_access or get_kombit_access()
        self._connection = None
        self._channel = None
        self._active_message: ReceivedBrokerMessage | None = None

    def __enter__(self) -> "MessageBroker":
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def open(self) -> None:
        """Åbn AMQP-forbindelsen og kanalen. Output er None."""
        if self._connection is not None:
            raise RuntimeError("MessageBroker er allerede åben.")
        self._connection = pika.BlockingConnection(_setup_pika_params(self.kombit_access))
        self._channel = self._connection.channel()

    def get_message(self) -> ReceivedBrokerMessage | None:
        """Hent næste besked eller returnér None, hvis Dueslaget er tomt."""
        if self._channel is None:
            raise RuntimeError("MessageBroker skal åbnes med 'with MessageBroker()'.")
        if self._active_message is not None and not self._active_message._settled:
            raise RuntimeError("Den forrige besked skal ackes eller requeues først.")
        method, _header, body = self._channel.basic_get(queue=self.queue_id, auto_ack=False)
        if method is None:
            self._active_message = None
            return None
        if body is None:
            self._channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            raise RuntimeError("Brokeren returnerede metadata uden body.")
        message = BrokerMessage(
            body=body,
            delivery_tag=method.delivery_tag,
            routing_key=method.routing_key,
            redelivered=bool(method.redelivered),
        )
        self._active_message = ReceivedBrokerMessage(self._channel, message)
        return self._active_message

    def close(self) -> None:
        """Requeue en uafsluttet besked og luk kanal og forbindelse."""
        if self._active_message is not None and not self._active_message._settled:
            try:
                self._active_message.requeue()
            except Exception:
                pass
        if self._channel is not None and getattr(self._channel, "is_open", False):
            self._channel.close()
        if self._connection is not None and getattr(self._connection, "is_open", False):
            self._connection.close()
        self._active_message = None
        self._channel = None
        self._connection = None


def iterate_queue_messages(
    queue_id: str,
    kombit_access: KombitAccess,
    auto_acknowledge: bool = True,
) -> Generator[bytes, None, None]:
    """Bagudkompatibel generator. Ny proceskode bør bruge MessageBroker."""
    parameters = _setup_pika_params(kombit_access)
    with pika.BlockingConnection(parameters=parameters) as connection:
        channel = connection.channel()
        while True:
            method, header, body = channel.basic_get(
                queue=_validate_queue_id(queue_id), auto_ack=auto_acknowledge
            )
            if not any((method, header, body)):
                return
            yield body


def _validate_queue_id(queue_id: str) -> str:
    if not isinstance(queue_id, str):
        raise TypeError("queue_id skal være tekst.")
    try:
        return str(uuid.UUID(queue_id.strip()))
    except (ValueError, AttributeError) as error:
        raise ValueError("queue_id skal være et gyldigt UUID.") from error
