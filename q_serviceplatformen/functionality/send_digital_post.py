"""Offentlig facade til registreringskontrol og Digital Post."""

from __future__ import annotations

from datetime import datetime, timezone

from q_serviceplatformen.authentication import KombitAccess
from q_serviceplatformen.functionality.access import (
    get_kombit_access,
)
from q_serviceplatformen.functionality.digital_post_builder import (
    build_digital_post_message,
)
from q_serviceplatformen.functionality.post_models import (
    DigitalPostSendResult,
    PostDocument,
    RecipientIdType,
)
from q_serviceplatformen.functionality.registration import (
    check_registration as check_recipient_registration,
    normalize_recipient_id,
)
from q_serviceplatformen.sf1601_client import (
    send_message,
)


def send_digital_post(
    *,
    recipient_id: str,
    recipient_id_type: RecipientIdType,
    subject: str,
    main_document: PostDocument,
    attachments: list[PostDocument] | None = None,
    kombit_access: KombitAccess | None = None,
    check_registration: bool = True,
) -> DigitalPostSendResult:
    """
    Sender én Digital Post-forsendelse.

    Input:
        recipient_id:
            Modtagerens CPR- eller CVR-nummer.

            Bindestreger, mellemrum og andre skilletegn fjernes,
            før nummeret bruges.

        recipient_id_type:
            CPR eller CVR.

        subject:
            Emnet, som vises på Digital Post-beskeden.

        main_document:
            Forsendelsens hoveddokument som PostDocument.

        attachments:
            Valgfri liste med PDF-bilag.

        kombit_access:
            Et valgfrit eksisterende KombitAccess-objekt.

            Hvis værdien ikke angives, oprettes adgangen ud fra
            q_serviceplatformens konfiguration.

        check_registration:
            True foretager registreringsopslag gennem
            PostForespoerg før afsendelse.

            False springer registreringsopslaget over.

            Standardværdien er True.

    Output:
        Et DigitalPostSendResult med:

        - serviceplatform_transaction_id
        - memo_message_uuid
        - submitted_at

    Fejl:
        TypeError:
            Hvis check_registration ikke er bool, eller hvis et
            input har en forkert datatype.

        ValueError:
            Hvis CPR/CVR er ugyldigt, dokumentet er ugyldigt, eller
            modtageren ikke er registreret til Digital Post.

        RuntimeError og HTTP-fejl:
            Ved tekniske fejl fra Serviceplatformen.

    Vigtigt:
        Et returneret DigitalPostSendResult betyder, at
        Serviceplatformen har accepteret indsendelsen.

        Det betyder ikke, at beskeden er endeligt leveret.
    """
    if not isinstance(check_registration, bool):
        raise TypeError(
            "check_registration skal være True eller False."
        )

    normalized_id = normalize_recipient_id(
        recipient_id=recipient_id,
        recipient_id_type=recipient_id_type,
    )

    access = kombit_access or get_kombit_access()

    if check_registration:
        recipient_is_registered = (
            check_recipient_registration(
                recipient_id=normalized_id,
                recipient_id_type=recipient_id_type,
                service="digitalpost",
                kombit_access=access,
            )
        )

        if not recipient_is_registered:
            raise ValueError(
                "Modtageren er ikke registreret til Digital Post."
            )

    memo_message = build_digital_post_message(
        recipient_id=normalized_id,
        recipient_id_type=recipient_id_type,
        subject=subject,
        main_document=main_document,
        attachments=attachments,
    )

    response = send_message(
        message_type="Digital Post",
        message=memo_message,
        kombit_access=access,
    )

    return DigitalPostSendResult(
        serviceplatform_transaction_id=(
            response.transaction_id
        ),
        memo_message_uuid=(
            memo_message.messageHeader.messageUUID
        ),
        submitted_at=datetime.now(timezone.utc),
    )