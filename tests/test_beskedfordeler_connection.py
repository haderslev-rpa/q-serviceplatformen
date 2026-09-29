"""Diagnosetest af forbindelsen til KOMBIT Beskedfordeleren.

Testen læser eller fjerner ingen beskeder.
Den kontrollerer:

1. Dueslagets UUID-format.
2. Hentning af SAML-token til BeskedModtag 2.0.
3. DNS og TCP-forbindelse til port 5671.
4. TLS-handshake.
5. AMQP-login.
"""

from __future__ import annotations

import socket
import ssl
import uuid

import pika

from q_serviceplatformen.beskedfordeler_message_broker import (
    BESKEDMODTAG_ENTITY_ID,
    PORT,
    PROD_HOST,
    TEST_HOST,
    _setup_pika_params,
)
from q_serviceplatformen.configuration import (
    get_message_broker_queue_id,
)
from q_serviceplatformen.functionality.access import (
    get_kombit_access,
)

TCP_TIMEOUT_SECONDS = 15


def _validate_queue_id(queue_id: str) -> str:
    """Validerer UUID-formatet og returnerer en normaliseret værdi.

    Output:
        Dueslagets UUID som normaliseret tekst.

    Vigtigt:
        Funktionen kan kun validere UUID-formatet. Funktionen kan ikke
        bevise, at værdien tilhører et konkret Dueslag.
    """
    try:
        return str(uuid.UUID(queue_id))
    except (TypeError, ValueError, AttributeError) as error:
        raise RuntimeError(
            "MESSAGE_BROKER_QUEUE_ID er ikke et gyldigt UUID. "
            f"Den aktuelle værdi er {queue_id!r}."
        ) from error


def _test_tcp_connection(host: str) -> str:
    """Tester DNS og TCP 5671.

    Output:
        Den IP-adresse, som forbindelsen blev etableret til.
    """
    addresses = socket.getaddrinfo(
        host,
        PORT,
        type=socket.SOCK_STREAM,
    )

    if not addresses:
        raise RuntimeError(
            f"DNS-opslaget returnerede ingen adresser for {host}."
        )

    ip_address = addresses[0][4][0]

    with socket.create_connection(
        (host, PORT),
        timeout=TCP_TIMEOUT_SECONDS,
    ):
        return ip_address


def _test_tls_connection(host: str) -> dict[str, str | None]:
    """Tester TLS-handshake.

    Output:
        En dictionary med TLS-version, cipher og servercertifikatets
        udløbsdato. Private oplysninger udskrives ikke.
    """
    context = ssl.create_default_context()

    with socket.create_connection(
        (host, PORT),
        timeout=TCP_TIMEOUT_SECONDS,
    ) as tcp_socket:
        with context.wrap_socket(
            tcp_socket,
            server_hostname=host,
        ) as tls_socket:
            certificate = tls_socket.getpeercert()
            cipher = tls_socket.cipher()

            return {
                "tls_version": tls_socket.version(),
                "cipher": cipher[0] if cipher else None,
                "not_after": certificate.get("notAfter"),
            }


def _test_amqp_login(kombit_access) -> None:
    """Tester AMQP-login uden at åbne et Dueslag.

    Output:
        Ingen returværdi, når login lykkes.
    """
    parameters = _setup_pika_params(kombit_access)
    connection = pika.BlockingConnection(parameters)

    try:
        if not connection.is_open:
            raise RuntimeError(
                "AMQP-forbindelsen blev oprettet, men er ikke åben."
            )
    finally:
        if connection.is_open:
            connection.close()


def main() -> None:
    """Kører forbindelsestesten og udskriver resultatet pr. trin."""
    print("Diagnosetest af Beskedfordeleren")
    print("================================")
    print("Testen læser eller fjerner ingen beskeder.")
    print("")

    kombit_access = get_kombit_access()
    configured_queue_id = _validate_queue_id(
        get_message_broker_queue_id()
    )

    host = TEST_HOST if kombit_access.test else PROD_HOST
    environment_name = (
        "Eksternt testmiljø"
        if kombit_access.test
        else "Produktion"
    )

    print(f"Miljø: {environment_name}")
    print(f"Broker: {host}:{PORT}")
    print(f"Entity-ID: {BESKEDMODTAG_ENTITY_ID}")
    print(
        "Konfigureret queue-ID har gyldigt UUID-format: "
        f"{configured_queue_id}"
    )
    print(
        "Bemærk: UUID-formatet beviser ikke, at værdien er "
        "Dueslagets UUID."
    )
    print("")

    print("[1/4] Henter SAML-token til BeskedModtag 2.0...")
    saml_token = kombit_access.get_saml_token(
        BESKEDMODTAG_ENTITY_ID
    )

    if not saml_token:
        raise RuntimeError("STS returnerede et tomt SAML-token.")

    print("OK: SAML-token blev udstedt.")
    print("Tokenets indhold udskrives ikke.")
    print("")

    print("[2/4] Tester DNS og TCP 5671...")
    ip_address = _test_tcp_connection(host)
    print(f"OK: TCP-forbindelse etableret til {ip_address}:{PORT}.")
    print("")

    print("[3/4] Tester TLS-handshake...")
    tls_info = _test_tls_connection(host)
    print(
        "OK: TLS-handshake gennemført med "
        f"{tls_info['tls_version']}."
    )
    print(f"Cipher: {tls_info['cipher']}")
    print(f"Servercertifikat udløber: {tls_info['not_after']}")
    print("")

    print("[4/4] Tester AMQP-login...")

    try:
        _test_amqp_login(kombit_access)
    except pika.exceptions.ProbableAuthenticationError as error:
        print("FEJL: TCP og TLS virker, men AMQP-login blev afvist.")
        print("Brokerens svar:")
        print(str(error))
        print("")
        print("Konklusion:")
        print(
            "Netværket virker. Kontrollér serviceaftalen til "
            "BeskedModtag 2.0, anvendersystemet og AMQP-adgangen."
        )
        print(
            "Dueslagets UUID er endnu ikke afprøvet, fordi login "
            "afvises før køen åbnes."
        )
        raise SystemExit(2) from error
    except pika.exceptions.AMQPConnectionError as error:
        print("FEJL: AMQP-forbindelsen kunne ikke etableres.")
        print(str(error))
        raise SystemExit(3) from error

    print("OK: AMQP-login lykkedes.")
    print("")
    print("Samlet resultat:")
    print("SAML-token til BeskedModtag 2.0: OK")
    print("TCP 5671: OK")
    print("TLS: OK")
    print("AMQP-login: OK")
    print("")
    print(
        "Kør nu test_check_message_broker.py for at kontrollere, "
        "om det konfigurerede UUID er et tilgængeligt Dueslag."
    )


if __name__ == "__main__":
    main()
