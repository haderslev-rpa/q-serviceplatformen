"""Sikker test af et Dueslag i KOMBIT Beskedfordeleren.

Testen henter højst én besked med auto_ack=False.

Hvis der findes en besked:
    1. Beskeden lægges straks tilbage med requeue=True.
    2. Kun sikre filteroplysninger udskrives i terminalen.
    3. Den formaterede XML gemmes under tests/test_local.

Beskeden bliver dermed ikke markeret som behandlet.

Vigtigt:
    Preview-filen kan indeholde personoplysninger og andre fortrolige
    oplysninger. Filen må ikke lægges i Git.
"""

from __future__ import annotations

import base64
import logging
import uuid
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree
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
    """Hent og validér Dueslagets UUID.

    Output:
        UUID som normaliseret tekst.
    """
    queue_id = get_message_broker_queue_id()

    try:
        return str(
            uuid.UUID(queue_id)
        )
    except (
        TypeError,
        ValueError,
        AttributeError,
    ) as error:
        raise RuntimeError(
            "message_broker_queue_id skal være UUID'et "
            "på det konkrete Dueslag."
        ) from error


def _decode_message_body(
    body: bytes,
) -> str:
    """Afkod beskeden som UTF-8.

    Output:
        Beskedens XML som tekst.
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
        return body.decode(
            "utf-8"
        )
    except UnicodeDecodeError as error:
        raise RuntimeError(
            "Beskeden kunne ikke afkodes som UTF-8."
        ) from error


def _format_message_text(
    message_text: str,
) -> str:
    """Formatér XML til preview-filen.

    Output:
        Formateret XML eller den oprindelige tekst.
    """
    try:
        parsed_xml = minidom.parseString(
            message_text.encode(
                "utf-8"
            )
        )
    except ExpatError:
        return message_text

    formatted_xml = parsed_xml.toprettyxml(
        indent="    ",
        encoding=None,
    )

    return "\n".join(
        line
        for line in formatted_xml.splitlines()
        if line.strip()
    )


def _save_message_preview(
    message_text: str,
) -> Path:
    """Gem beskeden lokalt.

    Output:
        Stien til preview-filen.
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


def _local_name(
    tag: str,
) -> str:
    """Returnér XML-navnet uden namespace."""
    return tag.rsplit(
        "}",
        maxsplit=1,
    )[-1]


def _find_text_by_path(
    root: ElementTree.Element,
    *path_names: str,
) -> str | None:
    """Find første tekstværdi på en strukturel XML-sti.

    Output:
        Tekstværdien eller None.
    """
    if not path_names:
        raise ValueError(
            "Der skal angives mindst ét elementnavn."
        )

    current_elements = [
        element
        for element in root.iter()
        if _local_name(
            element.tag
        ) == path_names[0]
    ]

    for path_name in path_names[1:]:
        next_elements = []

        for current_element in current_elements:
            next_elements.extend(
                child
                for child in list(
                    current_element
                )
                if _local_name(
                    child.tag
                ) == path_name
            )

        current_elements = next_elements

        if not current_elements:
            return None

    for element in current_elements:
        if (
            element.text
            and element.text.strip()
        ):
            return element.text.strip()

    return None


def _find_payload_values(
    envelope: ElementTree.Element,
) -> dict[str, str | None]:
    """Læs identifikatorer fra den base64-kodede poststatus.

    Output:
        Dictionary med de vigtigste afsendelsesfelter.
    """
    field_names = (
        "TransmissionId",
        "MessageUUID",
        "MessageId",
        "CorrelationId",
        "KanalKode",
        "TransaktionsStatusKode",
    )

    empty_result = {
        field_name: None
        for field_name in field_names
    }

    base64_element = next(
        (
            element
            for element in envelope.iter()
            if _local_name(
                element.tag
            ) == "Base64"
        ),
        None,
    )

    if (
        base64_element is None
        or not (
            base64_element.text
            or ""
        ).strip()
    ):
        return empty_result

    try:
        payload_bytes = base64.b64decode(
            base64_element.text.strip(),
            validate=True,
        )

        payload = ElementTree.fromstring(
            payload_bytes
        )
    except (
        ValueError,
        TypeError,
        ElementTree.ParseError,
    ):
        return empty_result

    values = {
        _local_name(
            element.tag
        ): element.text.strip()
        for element in payload.iter()
        if (
            element.text
            and element.text.strip()
        )
    }

    return {
        field_name: values.get(
            field_name
        )
        for field_name in field_names
    }


def _print_filter_information(
    body: bytes,
) -> None:
    """Udskriv sikre filteroplysninger til IT.

    Output:
        Udskriver kun relevante filter- og afsendelses-ID'er.

        Rå XML, IP-adresse, akkreditiver og persondata
        udskrives ikke.
    """
    try:
        envelope = ElementTree.fromstring(
            body
        )
    except ElementTree.ParseError as error:
        raise RuntimeError(
            "Brokerbeskeden er ikke gyldig XML."
        ) from error

    payload = _find_payload_values(
        envelope
    )

    values = (
        (
            "Besked-ID",
            _find_text_by_path(
                envelope,
                "BeskedId",
                "UUIDIdentifikator",
            ),
        ),
        (
            "Beskedtype",
            _find_text_by_path(
                envelope,
                "Beskedtype",
                "UUIDIdentifikator",
            ),
        ),
        (
            "Beskedansvarlig aktør",
            _find_text_by_path(
                envelope,
                "BeskedAnsvarligAktoer",
                "UUIDIdentifikator",
            ),
        ),
        (
            "Tilladt modtager",
            _find_text_by_path(
                envelope,
                "TilladtModtager",
                "URNIdentifikator",
            ),
        ),
        (
            "Relateret objekt-ID",
            _find_text_by_path(
                envelope,
                "RelateretObjekt",
                "ObjektId",
                "UUIDIdentifikator",
            ),
        ),
        (
            "Relateret objekttype",
            _find_text_by_path(
                envelope,
                "RelateretObjekt",
                "ObjektType",
                "UUIDIdentifikator",
            ),
        ),
        (
            "Registreringsaktør",
            _find_text_by_path(
                envelope,
                "ObjektRegistrering",
                "RegistreringsAktoer",
                "UUIDIdentifikator",
            ),
        ),
        (
            "Registreret objekt-ID",
            _find_text_by_path(
                envelope,
                "ObjektRegistrering",
                "ObjektId",
                "UUIDIdentifikator",
            ),
        ),
        (
            "Kildesystem",
            _find_text_by_path(
                envelope,
                "Kildesystem",
                "UUIDIdentifikator",
            ),
        ),
        (
            "Abonnementsudtryk",
            _find_text_by_path(
                envelope,
                "ErLeveretIHenholdTil",
                "UUIDIdentifikator",
            ),
        ),
    )

    print(
        "FILTEROPLYSNINGER TIL IT"
    )
    print(
        "========================="
    )

    for label, value in values:
        print(
            f"{label}: "
            f"{value or 'Ikke oplyst'}"
        )

    print("")
    print(
        "INDLEJRET POSTSTATUS"
    )
    print(
        "===================="
    )
    print(
        "TransmissionId: "
        f"{payload['TransmissionId'] or 'Ikke oplyst'}"
    )
    print(
        "MessageUUID: "
        f"{payload['MessageUUID'] or 'Ikke oplyst'}"
    )
    print(
        "MessageId: "
        f"{payload['MessageId'] or 'Ikke oplyst'}"
    )
    print(
        "CorrelationId: "
        f"{payload['CorrelationId'] or 'Ikke oplyst'}"
    )
    print(
        "Kanal: "
        f"{payload['KanalKode'] or 'Ikke oplyst'}"
    )
    print(
        "Status: "
        f"{payload['TransaktionsStatusKode'] or 'Ikke oplyst'}"
    )


def main() -> None:
    """Hent, requeue og undersøg højst én brokerbesked.

    Output:
        Udskriver filteroplysninger og gemmer en
        lokal XML-preview.
    """
    # Skjul Pikas oplysninger om sockets, IP-adresser og TLS.
    logging.getLogger(
        "pika"
    ).setLevel(
        logging.WARNING
    )

    queue_id = _get_validated_queue_id()

    parameters = _setup_pika_params(
        get_kombit_access()
    )

    print(
        "Test af Dueslag i Beskedfordeleren"
    )
    print(
        "=================================="
    )
    print(
        f"Konfigureret queue-ID: {queue_id}"
    )
    print(
        "auto_acknowledge: False"
    )
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
            "AMQP-login blev afvist. "
            "Kontrollér brokeradgangen."
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
            print(
                "OK: Broker og Dueslag kunne åbnes."
            )
            print(
                "Dueslaget er tomt."
            )
            return

        print(
            "OK: Broker og Dueslag kunne åbnes."
        )
        print(
            "Dueslaget indeholder mindst én besked."
        )
        print(
            f"Beskedstørrelse: "
            f"{len(body or b'')} bytes"
        )
        print(
            f"Routing key: "
            f"{method_frame.routing_key}"
        )
        print(
            f"Redelivered: "
            f"{method_frame.redelivered}"
        )
        print(
            f"Delivery tag: "
            f"{method_frame.delivery_tag}"
        )

        # Returnér beskeden før parsing og filskrivning.
        channel.basic_nack(
            delivery_tag=(
                method_frame.delivery_tag
            ),
            requeue=True,
        )

        print(
            "Beskeden blev lagt tilbage i køen."
        )
        print("")

        if body is None:
            raise RuntimeError(
                "Brokerens svar indeholdt metadata, "
                "men ingen body."
            )

        _print_filter_information(
            body
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

        print("")
        print(
            "Preview er gemt her:"
        )
        print(
            saved_path
        )
        print(
            "Filen kan indeholde personoplysninger "
            "og må ikke lægges i Git."
        )

    except pika.exceptions.ChannelClosedByBroker as error:
        raise RuntimeError(
            "Brokerens kanal blev lukket. Kontrollér "
            "queue-ID, miljø og anvendersystemets adgang. "
            f"Brokerens svar: {error}"
        ) from error
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    main()