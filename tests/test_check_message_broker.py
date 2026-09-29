"""Sikker test af et Dueslag i KOMBIT Beskedfordeleren.

Testen henter højst én besked med auto_ack=False.

Hvis der findes en besked:
    1. Beskeden lægges tilbage i køen med requeue=True.
    2. Beskedens indhold udskrives i terminalen.
    3. Beskeden gemmes under tests/test_local.

Beskeden bliver dermed ikke bevidst markeret som behandlet.

Vigtigt:
    Beskedindholdet kan indeholde personoplysninger og andre
    fortrolige oplysninger. Preview-filen må ikke lægges i Git.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from xml.dom import minidom
from xml.parsers.expat import ExpatError

import pika

from q_serviceplatformen.beskedfordeler_message_broker import (
    _setup_pika_params,
)
from q_serviceplatformen.configuration import (
    get_message_broker_queue_id,
)
from q_serviceplatformen.functionality.access import (
    get_kombit_access,
)


TEST_LOCAL_DIRECTORY = (
    Path(__file__).resolve().parent
    / "test_local"
)

MESSAGE_PREVIEW_PATH = (
    TEST_LOCAL_DIRECTORY
    / "beskedfordeler_message_preview.xml"
)


def _get_validated_queue_id() -> str:
    """
    Henter og validerer det konfigurerede Dueslags UUID.

    Output:
        Dueslagets UUID som normaliseret tekst.

    Fejl:
        RuntimeError, hvis den konfigurerede værdi ikke er et
        gyldigt UUID.

    Vigtigt:
        Et gyldigt UUID-format beviser ikke alene, at værdien
        tilhører et Dueslag. Det kontrolleres ved brokerkaldet.
    """
    queue_id = get_message_broker_queue_id()

    try:
        return str(uuid.UUID(queue_id))
    except (
        TypeError,
        ValueError,
        AttributeError,
    ) as error:
        raise RuntimeError(
            "message_broker_queue_id skal være UUID'et på det "
            "konkrete Dueslag. Den aktuelle værdi er ikke et "
            "gyldigt UUID."
        ) from error


def _decode_message_body(
    body: bytes,
) -> str:
    """
    Afkoder beskedens body som UTF-8.

    Output:
        Beskedindholdet som tekst.

    Fejl:
        RuntimeError, hvis beskeden ikke kan afkodes som UTF-8.
    """
    if not isinstance(body, bytes):
        raise TypeError(
            "Beskedens body skal være bytes."
        )

    if not body:
        raise ValueError(
            "Beskedens body er tom."
        )

    try:
        return body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError(
            "Beskeden kunne ikke afkodes som UTF-8. "
            "Det rå beskedindhold udskrives derfor ikke."
        ) from error


def _format_message_text(
    message_text: str,
) -> str:
    """
    Formaterer beskedindholdet, hvis indholdet er XML.

    Output:
        Formateret XML, hvis teksten er gyldig XML.

        Den oprindelige tekst, hvis indholdet ikke er XML.
    """
    try:
        parsed_xml = minidom.parseString(
            message_text.encode("utf-8")
        )
    except ExpatError:
        return message_text

    formatted_xml = parsed_xml.toprettyxml(
        indent="    ",
        encoding=None,
    )

    # minidom kan indsætte tomme linjer mellem elementerne.
    # De fjernes for at gøre terminaludskriften lettere at læse.
    return "\n".join(
        line
        for line in formatted_xml.splitlines()
        if line.strip()
    )


def _save_message_preview(
    message_text: str,
) -> Path:
    """
    Gemmer beskedens formaterede indhold under tests/test_local.

    Output:
        Stien til den gemte preview-fil.

    Vigtigt:
        Filen kan indeholde personoplysninger og må ikke lægges
        i Git.
    """
    TEST_LOCAL_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    MESSAGE_PREVIEW_PATH.write_text(
        message_text,
        encoding="utf-8",
    )

    return MESSAGE_PREVIEW_PATH


def main() -> None:
    """
    Tester adgang til Dueslaget og viser højst én besked.

    Output ved tomt Dueslag:
        Der udskrives, at broker og Dueslag kunne åbnes,
        men at Dueslaget er tomt.

    Output ved fundet besked:
        - beskedstørrelse
        - routing key
        - redelivery-status
        - delivery tag
        - beskedens formaterede indhold
        - stien til den gemte preview-fil

    Beskeden lægges tilbage i køen før indholdet behandles.
    """
    queue_id = _get_validated_queue_id()
    kombit_access = get_kombit_access()
    parameters = _setup_pika_params(
        kombit_access
    )

    print("Test af Dueslag i Beskedfordeleren")
    print("==================================")
    print(f"Konfigureret queue-ID: {queue_id}")
    print("auto_acknowledge: False")
    print(
        "En fundet besked bliver lagt tilbage i køen."
    )
    print("")

    try:
        connection = pika.BlockingConnection(
            parameters
        )
    except pika.exceptions.ProbableAuthenticationError as error:
        raise RuntimeError(
            "AMQP-login blev afvist. Kør først "
            "test_beskedfordeler_connection.py og løs "
            "loginfejlen."
        ) from error

    try:
        channel = connection.channel()

        method_frame, _header_frame, body = (
            channel.basic_get(
                queue=queue_id,
                auto_ack=False,
            )
        )

        if method_frame is None:
            print("OK: Broker og Dueslag kunne åbnes.")
            print("Dueslaget er tomt.")
            return

        print("OK: Broker og Dueslag kunne åbnes.")
        print(
            "Dueslaget indeholder mindst én besked."
        )
        print(
            f"Beskedstørrelse: {len(body or b'')} bytes"
        )
        print(
            f"Routing key: {method_frame.routing_key}"
        )
        print(
            f"Redelivered: {method_frame.redelivered}"
        )
        print(
            f"Delivery tag: {method_frame.delivery_tag}"
        )

        # Beskeden returneres til køen med det samme.
        # Dermed risikerer efterfølgende formatering eller
        # filskrivning ikke at efterlade beskeden uafklaret.
        channel.basic_nack(
            delivery_tag=method_frame.delivery_tag,
            requeue=True,
        )

        print("Beskeden blev lagt tilbage i køen.")
        print("")

        if body is None:
            raise RuntimeError(
                "Brokerens svar indeholdt metadata, "
                "men ingen besked-body."
            )

        message_text = _decode_message_body(
            body
        )

        formatted_message = _format_message_text(
            message_text
        )

        saved_path = _save_message_preview(
            formatted_message
        )

        print("BESKEDINDHOLD")
        print("=============")
        print(formatted_message)
        print("")
        print("Beskedens indhold er også gemt her:")
        print(saved_path)
        print("")
        print(
            "Filen kan indeholde personoplysninger "
            "og må ikke lægges i Git."
        )

    except pika.exceptions.ChannelClosedByBroker as error:
        raise RuntimeError(
            "AMQP-login lykkedes, men brokerens kanal "
            "blev lukket. Det konfigurerede UUID er "
            "muligvis ikke Dueslagets UUID, Dueslaget "
            "findes i et andet miljø, eller "
            "anvendersystemet mangler adgang.\n"
            f"Brokerens svar: {error}"
        ) from error
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    main()
