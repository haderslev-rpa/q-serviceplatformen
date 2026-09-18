"""Bagudkompatibel adgang til det interne SF1601-klientlag."""

from q_serviceplatformen.sf1601_client import (
    KombiResponse,
    build_physical_mail_xml,
    is_registered,
    send_message,
    send_physical_mail,
)

__all__ = [
    "KombiResponse",
    "build_physical_mail_xml",
    "is_registered",
    "send_message",
    "send_physical_mail",
]
