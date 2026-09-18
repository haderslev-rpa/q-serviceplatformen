"""Kontrollerer forbindelse til Beskedfordeleren uden acknowledge."""

import logging

from q_serviceplatformen.beskedfordeler_message_broker import (
    iterate_queue_messages,
)
from q_serviceplatformen.configuration import (
    get_message_broker_queue_id,
)
from q_serviceplatformen.functionality.access import get_kombit_access


def main() -> None:
    """Henter højst én besked uden at fjerne den fra Dueslaget."""
    logging.basicConfig(level=logging.DEBUG)
    messages = iterate_queue_messages(
        queue_id=get_message_broker_queue_id(),
        kombit_access=get_kombit_access(),
        auto_acknowledge=False,
    )
    try:
        body = next(messages)
    except StopIteration:
        print("Forbindelsen lykkedes, men Dueslaget var tomt.")
        return
    finally:
        messages.close()

    print("Der blev fundet en besked.")
    print(f"Beskedstørrelse: {len(body)} bytes")
    print("Beskeden blev ikke acknowledged.")


if __name__ == "__main__":
    main()
