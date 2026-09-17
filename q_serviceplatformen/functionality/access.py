"""Opretter adgang til Serviceplatformen ud fra fælles konfiguration."""

from q_serviceplatformen.authentication import KombitAccess
from q_serviceplatformen.configuration import (
    SENDER_CVR,
    USE_TEST_ENVIRONMENT,
    get_certificate_path,
    validate_configuration,
)


def get_kombit_access() -> KombitAccess:
    """
    Validerer konfigurationen og opretter Serviceplatform-adgang.

    Output:
        Et KombitAccess-objekt med:

        - Haderslev Kommunes CVR-nummer.
        - Stien til klientcertifikatet.
        - Det valgte Serviceplatform-miljø.

        Funktionen foretager ikke selv et netværkskald.
    """

    validate_configuration()

    certificate_path = get_certificate_path()

    return KombitAccess(
        cvr=SENDER_CVR,
        cert_path=certificate_path,
        test=USE_TEST_ENVIRONMENT,
    )