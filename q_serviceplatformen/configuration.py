"""
Fælles konfiguration til Serviceplatformen.

Almindelige, ikke-følsomme standardværdier findes direkte i filen.

Miljøbestemte ID'er hentes fra Automation Server Credentials:
    - physical_post_shipment_type_id
    - message_broker_queue_id

Credential-navn:
    SERVICEPLATFORMEN
"""

from pathlib import Path
from typing import Any

from automation_server_client import AutomationServer, Credential


# ------------------------------------------------------------
# AUTOMATION SERVER CREDENTIAL
# ------------------------------------------------------------

SERVICEPLATFORMEN_CREDENTIAL_NAME = "SERVICEPLATFORMEN"

_credential_data: dict[str, Any] | None = None


# ------------------------------------------------------------
# CERTIFIKAT
# ------------------------------------------------------------

CERTIFICATE_DIRECTORY = Path(
    "/usr/local/share/client-certificates"
)

CERTIFICATE_FILE_NAME = "Serviceplatformen-digitalpost.pem"

CERTIFICATE_PATH = (
    CERTIFICATE_DIRECTORY
    / CERTIFICATE_FILE_NAME
)


# ------------------------------------------------------------
# ORGANISATION
# ------------------------------------------------------------

# Haderslev Kommunes CVR-nummer.
SENDER_CVR = "29189757"

# Det navn, der anvendes som afsender i MeMo.
SENDER_LABEL = "Haderslev Kommune"


# ------------------------------------------------------------
# SERVICEPLATFORM-MILJØ
# ------------------------------------------------------------

# True anvender Serviceplatformens eksterne testmiljø.
# False anvender Serviceplatformens produktionsmiljø.
USE_TEST_ENVIRONMENT = False


# ------------------------------------------------------------
# STANDARDVÆRDIER TIL DIGITAL POST
# ------------------------------------------------------------

DEFAULT_LANGUAGE = "da"
DEFAULT_MIME_TYPE = "application/pdf"
DEFAULT_POST_TYPE = "MYNDIGHEDSPOST"
DEFAULT_LEGAL_NOTIFICATION = False
DEFAULT_MANDATORY = False


# ------------------------------------------------------------
# NETVÆRK
# ------------------------------------------------------------

REQUEST_TIMEOUT_SECONDS = 30


# ------------------------------------------------------------
# AUTOMATION SERVER
# ------------------------------------------------------------

def _get_credential_data() -> dict[str, Any]:
    """
    Henter Serviceplatform-konfigurationen fra Automation Server.

    Credentialen hentes kun første gang funktionen kaldes. Dataene
    gemmes derefter i hukommelsen og genbruges.

    Output:
        En dictionary med data fra credentialen SERVICEPLATFORMEN.

        Forventede felter:
            physical_post_shipment_type_id
            message_broker_queue_id

    Fejl:
        RuntimeError, hvis credentialen ikke indeholder en dictionary.
        Andre forbindelses- eller credentialfejl fortsætter fra
        automation_server_client.
    """
    global _credential_data

    if _credential_data is not None:
        return _credential_data

    AutomationServer.from_environment()

    credential = Credential.get_credential(
        SERVICEPLATFORMEN_CREDENTIAL_NAME
    )

    if not isinstance(credential.data, dict):
        raise RuntimeError(
            "Automation Server-credentialen "
            f"{SERVICEPLATFORMEN_CREDENTIAL_NAME!r} skal indeholde "
            "et dataobjekt."
        )

    _credential_data = credential.data

    return _credential_data


def get_physical_post_shipment_type_id() -> int:
    """
    Henter ForsendelseTypeIdentifikator til fysisk post.

    Output:
        Et positivt heltal, eksempelvis 13979.

    Fejl:
        KeyError, hvis feltet mangler i credentialen.
        TypeError eller ValueError, hvis værdien er ugyldig.
    """
    credential_data = _get_credential_data()

    raw_value = credential_data[
        "physical_post_shipment_type_id"
    ]

    if isinstance(raw_value, bool):
        raise TypeError(
            "physical_post_shipment_type_id må ikke være "
            "True eller False."
        )

    try:
        shipment_type_id = int(raw_value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "physical_post_shipment_type_id skal være "
            "et positivt heltal."
        ) from error

    if shipment_type_id <= 0:
        raise ValueError(
            "physical_post_shipment_type_id skal være "
            "større end 0."
        )

    return shipment_type_id


def get_message_broker_queue_id() -> str:
    """
    Henter UUID'et på Dueslaget i Beskedfordeleren.

    Output:
        Dueslagets UUID som tekst.

    Fejl:
        KeyError, hvis feltet mangler i credentialen.
        TypeError eller ValueError, hvis værdien er ugyldig.
    """
    credential_data = _get_credential_data()

    raw_value = credential_data[
        "message_broker_queue_id"
    ]

    if not isinstance(raw_value, str):
        raise TypeError(
            "message_broker_queue_id skal være tekst."
        )

    queue_id = raw_value.strip()

    if not queue_id:
        raise ValueError(
            "message_broker_queue_id må ikke være tom."
        )

    return queue_id


# ------------------------------------------------------------
# CERTIFIKATVALIDERING
# ------------------------------------------------------------

def get_certificate_path() -> str:
    """
    Kontrollerer certifikatplaceringen.

    Output:
        Certifikatets fulde sti som tekst.

    Fejl:
        FileNotFoundError, hvis certifikatmappen eller
        certifikatfilen ikke findes.
    """
    if not CERTIFICATE_DIRECTORY.is_dir():
        raise FileNotFoundError(
            "Certifikatmappen blev ikke fundet: "
            f"{CERTIFICATE_DIRECTORY}"
        )

    if not CERTIFICATE_PATH.is_file():
        raise FileNotFoundError(
            "Serviceplatform-certifikatet blev ikke fundet: "
            f"{CERTIFICATE_PATH}"
        )

    return str(CERTIFICATE_PATH)


def validate_configuration() -> None:
    """
    Kontrollerer den grundlæggende Serviceplatform-konfiguration.

    Funktionen henter ikke fysisk post-ID eller Dueslag-ID.
    De valideres først, når deres respektive funktioner kaldes.

    Output:
        None, når konfigurationen er gyldig.

    Fejl:
        ValueError, TypeError eller FileNotFoundError ved
        ugyldig opsætning.
    """
    get_certificate_path()

    normalized_cvr = "".join(
        character
        for character in SENDER_CVR
        if character.isdigit()
    )

    if len(normalized_cvr) != 8:
        raise ValueError(
            "SENDER_CVR skal indeholde præcis otte cifre."
        )

    if not SENDER_LABEL.strip():
        raise ValueError(
            "SENDER_LABEL må ikke være tom."
        )

    if not isinstance(USE_TEST_ENVIRONMENT, bool):
        raise TypeError(
            "USE_TEST_ENVIRONMENT skal være True eller False."
        )

    if isinstance(REQUEST_TIMEOUT_SECONDS, bool):
        raise TypeError(
            "REQUEST_TIMEOUT_SECONDS må ikke være bool."
        )

    if not isinstance(REQUEST_TIMEOUT_SECONDS, int):
        raise TypeError(
            "REQUEST_TIMEOUT_SECONDS skal være et helt tal."
        )

    if REQUEST_TIMEOUT_SECONDS <= 0:
        raise ValueError(
            "REQUEST_TIMEOUT_SECONDS skal være større end 0."
        )