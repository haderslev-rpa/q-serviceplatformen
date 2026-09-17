"""
Fælles konfiguration til Serviceplatformen.

Filen indeholder ikke certifikatets adgangskode eller andre
hemmeligheder. Selve certifikatfilen skal ligge i den angivne mappe
både lokalt og på Automation Server.
"""

from pathlib import Path


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

# Det navn, der skal anvendes som afsender i MeMo.
SENDER_LABEL = "Haderslev Kommune"


# ------------------------------------------------------------
# SERVICEPLATFORM-MILJØ
# ------------------------------------------------------------

# True anvender Serviceplatformens eksterne testmiljø.
# False anvender Serviceplatformens driftsmiljø.
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
# BESKEDFORDELER
# ------------------------------------------------------------

# Kø-ID'et udleveres som en del af opsætningen af Beskedfordeleren.
# Værdien kan være tom, indtil køen er oprettet.
MESSAGE_BROKER_QUEUE_ID = "d343e45d-8d0b-4a5d-fd43-40f4e3b3a40b"


# ------------------------------------------------------------
# VALIDERING
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

    Output:
        None, når konfigurationen er gyldig.

    Fejl:
        ValueError eller FileNotFoundError ved manglende opsætning.
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