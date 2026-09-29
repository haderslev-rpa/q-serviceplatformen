"""Direkte adgang til KOMBIT Beskedfordeleren.

Denne fil er en navngivet adgangsfil. Pakken bruger ikke __init__.py
som facade. Ny kode kan importere MessageBroker herfra eller direkte
fra beskedfordeler_message_broker.py.
"""

from q_serviceplatformen.beskedfordeler_message_broker import (
    MessageBroker,
    ReceivedBrokerMessage,
    TokenCredentials,
    iterate_queue_messages,
)
