"""Facade til registreringskontrol og afsendelse af Digital Post."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from q_serviceplatformen import digital_post
from q_serviceplatformen.authentication import KombitAccess
from q_serviceplatformen.functionality.access import (
    get_kombit_access,
)
from q_serviceplatformen.functionality.digital_post_builder import (
    build_digital_post_message,
)
from q_serviceplatformen.functionality.digital_post_models import (
    DigitalPostDocument,
    DigitalPostSendResult,
)


RecipientIdType = Literal["CPR", "CVR"]


def send_digital_post(
    *,
    recipient_id: str,
    recipient_id_type: RecipientIdType,
    subject: str,
    main_document: DigitalPostDocument,
    attachments: list[DigitalPostDocument] | None = None,
    kombit_access: KombitAccess | None = None,
    check_registration: bool = True,
) -> DigitalPostSendResult:
    """
    Sender én Digital Post-forsendelse.

    Input:
        recipient_id:
            Modtagerens CPR- eller CVR-nummer.

            Nummeret må indeholde skilletegn som bindestreg og
            mellemrum. Skilletegn fjernes før brug.

        recipient_id_type:
            CPR eller CVR.

        subject:
            Emnet, som vises på Digital Post-beskeden.

        main_document:
            Forsendelsens hoveddokument.

        attachments:
            En valgfri liste med PDF-bilag.

        kombit_access:
            Et valgfrit eksisterende KombitAccess-objekt.

            Hvis værdien ikke angives, oprettes adgangen ud fra
            q_serviceplatformen.configuration.

        check_registration:
            True udfører opslag via PostForespoerg før afsendelse.

            False springer registreringsopslaget over og sender
            direkte via KombiPostAfsend.

            Standardværdien er True.

    Output:
        Et DigitalPostSendResult med:

        - Serviceplatformens transaktions-ID.
        - MeMo-beskedens UUID.
        - Indsendelsestidspunktet.

    Fejl:
        TypeError, hvis check_registration ikke er en bool.

        ValueError, hvis modtager-ID'et er ugyldigt, eller hvis
        modtageren ikke er registreret til Digital Post.

        HTTP- og autentificeringsfejl sendes videre til den
        kaldende proces.

    Bemærkning:
        En succesfuld returværdi betyder, at Serviceplatformen
        accepterede afsendelseskaldet.

        Det betyder ikke, at beskeden er endeligt leveret.
    """

    if not isinstance(check_registration, bool):
        raise TypeError(
            "check_registration skal være True eller False."
        )

    normalized_recipient_id = _normalize_recipient_id(
        recipient_id=recipient_id,
        recipient_id_type=recipient_id_type,
    )

    access = kombit_access or get_kombit_access()

    if check_registration:
        is_registered = digital_post.is_registered(
            id_=normalized_recipient_id,
            service="digitalpost",
            kombit_access=access,
        )

        if not is_registered:
            raise ValueError(
                "Modtageren er ikke registreret til Digital Post."
            )

    memo_message = build_digital_post_message(
        recipient_id=normalized_recipient_id,
        recipient_id_type=recipient_id_type,
        subject=subject,
        main_document=main_document,
        attachments=attachments,
    )

    transaction_id = digital_post.send_message(
        message_type="Digital Post",
        message=memo_message,
        kombit_access=access,
    )

    submitted_at = datetime.now(timezone.utc)

    return DigitalPostSendResult(
        serviceplatform_transaction_id=transaction_id,
        memo_message_uuid=(
            memo_message.messageHeader.messageUUID
        ),
        submitted_at=submitted_at,
    )


def _normalize_recipient_id(
    *,
    recipient_id: str,
    recipient_id_type: RecipientIdType,
) -> str:
    """
    Normaliserer og validerer et CPR- eller CVR-nummer.

    Input:
        recipient_id:
            CPR- eller CVR-nummer med eller uden skilletegn.

        recipient_id_type:
            CPR eller CVR.

    Output:
        Nummeret som en tekstværdi, der kun indeholder cifre.

    Fejl:
        TypeError, hvis recipient_id ikke er tekst.

        ValueError, hvis typen ikke er CPR eller CVR, eller hvis
        antallet af cifre ikke passer til den valgte type.
    """

    if not isinstance(recipient_id, str):
        raise TypeError(
            "recipient_id skal være tekst."
        )

    normalized_recipient_id = "".join(
        character
        for character in recipient_id
        if character.isdigit()
    )

    if recipient_id_type == "CPR":
        expected_length = 10
    elif recipient_id_type == "CVR":
        expected_length = 8
    else:
        raise ValueError(
            "recipient_id_type skal være CPR eller CVR."
        )

    if len(normalized_recipient_id) != expected_length:
        raise ValueError(
            f"{recipient_id_type} skal indeholde "
            f"{expected_length} cifre."
        )

    return normalized_recipient_id