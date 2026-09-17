"""
Kontrollerer adgang til Beskedfordeleren og forsøger at hente én besked.

Beskeden hentes uden automatisk acknowledge. Det betyder, at den
ikke markeres som færdig eller slettes af dette program.
"""

from __future__ import annotations

from q_serviceplatformen.configuration import (
    MESSAGE_BROKER_QUEUE_ID,
)
from q_serviceplatformen.functionality.access import (
    get_kombit_access,
)
from q_serviceplatformen.message_broker import (
    iterate_queue_messages,
)


def main() -> None:
    """
    Forsøger at hente én besked fra den konfigurerede kø.

    Output:
        Udskriver, om forbindelsen lykkedes, og om køen indeholdt
        en besked.

        Beskedens indhold udskrives ikke.

        Beskeden hentes med auto_acknowledge=False. Når forbindelsen
        lukkes uden acknowledge, bør beskeden derfor blive liggende
        eller blive leveret igen.
    """

    queue_id = MESSAGE_BROKER_QUEUE_ID.strip()

    if not queue_id:
        raise RuntimeError(
            "MESSAGE_BROKER_QUEUE_ID mangler i configuration.py."
        )

    kombit_access = get_kombit_access()

    print("Forbinder til Beskedfordeleren...")
    print(f"Miljø: {kombit_access.environment}")
    print("Kø-ID er indlæst, men udskrives ikke.")

    messages = iterate_queue_messages(
        queue_id=queue_id,
        kombit_access=kombit_access,
        auto_acknowledge=False,
    )

    try:
        message_body = next(messages)
    except StopIteration:
        print("Forbindelsen lykkedes, men køen var tom.")
        return
    finally:
        messages.close()

    print("Der blev fundet en besked.")
    print(f"Beskedstørrelse: {len(message_body)} bytes")
    print("Beskedens indhold blev ikke udskrevet.")
    print("Beskeden blev ikke acknowledged.")


if __name__ == "__main__":
    main()