"""Datamodeller til den offentlige funktionalitet i q-serviceplatformen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


RecipientIdType = Literal["CPR", "CVR"]

ReceiptStatus = Literal[
    "PENDING",
    "DELIVERED",
    "FAILED",
    "REJECTED",
    "UNKNOWN",
]


@dataclass(frozen=True, slots=True)
class DigitalPostDocument:
    """
    Ét PDF-dokument til en Digital Post-forsendelse.

    Felter:
        content:
            PDF-filens binære indhold.

        file_name:
            Det filnavn, som modtageren skal kunne se.

        document_id:
            Haderslevs dokument-ID fra SharePoint og ATS.

        label:
            En valgfri beskrivelse af dokumentet.

    Output:
        Et uforanderligt dokumentobjekt, som kan bruges til at
        opbygge et MainDocument eller AdditionalDocument i MeMo.
    """

    content: bytes
    file_name: str
    document_id: str
    label: str | None = None


@dataclass(frozen=True, slots=True)
class DigitalPostSendResult:
    """
    Resultatet efter indsendelse af Digital Post til SF1601.

    Felter:
        serviceplatform_transaction_id:
            Transaktions-ID'et fra X-TransaktionsId.

        memo_message_uuid:
            MeMo-beskedens messageUUID.

        submitted_at:
            Tidspunktet, hvor beskeden blev indsendt.

    Output:
        De oplysninger, som workeren senere skal gemme på
        ATS-itemet efter indsendelse.
    """

    serviceplatform_transaction_id: str
    memo_message_uuid: str
    submitted_at: datetime


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    """
    Resultatet af et registreringsopslag.

    Felter:
        recipient_id:
            Det normaliserede CPR- eller CVR-nummer.

        recipient_id_type:
            Modtagertypen CPR eller CVR.

        service:
            Den undersøgte tjeneste, digitalpost eller nemsms.

        is_registered:
            True, hvis modtageren er registreret til tjenesten.

    Output:
        Et resultatobjekt, som beskriver både opslaget og svaret.
    """

    recipient_id: str
    recipient_id_type: RecipientIdType
    service: Literal["digitalpost", "nemsms"]
    is_registered: bool


@dataclass(frozen=True, slots=True)
class DigitalPostReceipt:
    """
    En fortolket kvittering fra Beskedfordeleren.

    Felter:
        status:
            Den normaliserede kvitteringsstatus.

        is_final:
            True, når kvitteringen afslutter forsendelsen.

        is_success:
            True, når den endelige levering er gennemført.

        received_at:
            Tidspunktet, hvor kvitteringen blev modtaget.

        serviceplatform_transaction_id:
            Serviceplatformens transaktions-ID, hvis det findes.

        memo_message_uuid:
            MeMo-beskedens UUID, hvis det findes.

        digital_post_id:
            Digital Posts ID for beskeden, hvis det findes.

        actual_delivery:
            Det faktiske leveringstidspunkt, hvis det findes.

        status_code:
            Den oprindelige statuskode fra kvitteringen.

        status_message:
            Kvitteringens statusbeskrivelse.

    Output:
        Et normaliseret kvitteringsobjekt, som workeren senere
        kan bruge til at vælge mellem defer, complete og failed.
    """

    status: ReceiptStatus
    is_final: bool
    is_success: bool
    received_at: datetime
    serviceplatform_transaction_id: str | None = None
    memo_message_uuid: str | None = None
    digital_post_id: str | None = None
    actual_delivery: datetime | None = None
    status_code: str | None = None
    status_message: str | None = None


@dataclass(frozen=True, slots=True)
class BrokerMessage:
    """
    Én besked hentet fra Beskedfordeleren.

    Felter:
        body:
            Beskedens rå indhold.

        delivery_tag:
            AMQP-leverings-ID'et, som bruges til acknowledge
            eller reject.

        routing_key:
            Beskedens routing key, hvis den findes.

        redelivered:
            True, hvis beskeden tidligere er blevet leveret.

    Output:
        En broker-besked med de metadata, der senere kræves for
        at godkende eller afvise beskeden eksplicit.
    """

    body: bytes
    delivery_tag: int
    routing_key: str | None = None
    redelivered: bool = False