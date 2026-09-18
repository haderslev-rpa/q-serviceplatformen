"""Bagudkompatibel import af Beskedfordeler-klienten."""

from q_serviceplatformen.beskedfordeler_message_broker import (
    TokenCredentials,
    iterate_queue_messages,
)

__all__ = ["TokenCredentials", "iterate_queue_messages"]
