"""Offentlige input- og resultatmodeller til q-serviceplatformen."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

RecipientIdType = Literal["CPR", "CVR"]
ReceiptStatus = Literal["PENDING", "DELIVERED", "FAILED", "REJECTED", "UNKNOWN"]


@dataclass(frozen=True, slots=True)
class PostDocument:
    """Et PDF-dokument, som kan bruges til digital eller fysisk post."""
    content: bytes
    file_name: str
    document_id: str
    label: str | None = None


DigitalPostDocument = PostDocument


@dataclass(frozen=True, slots=True)
class DigitalPostSendResult:
    """Resultat efter accepteret indsendelse af Digital Post."""
    serviceplatform_transaction_id: str
    memo_message_uuid: str
    submitted_at: datetime


@dataclass(frozen=True, slots=True)
class PhysicalPostSendResult:
    """Resultat efter accepteret indsendelse af fysisk post."""
    serviceplatform_transaction_id: str
    shipment_id: str
    submitted_at: datetime


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    """Beskrivende resultat fra PostForespoerg."""
    recipient_id: str
    recipient_id_type: RecipientIdType
    service: Literal["digitalpost", "nemsms"]
    is_registered: bool


@dataclass(frozen=True, slots=True)
class DigitalPostReceipt:
    """
    Fortolket kvittering fra KOMBIT Beskedfordeleren.

    Felter:
        status:
            Normaliseret status:

            - PENDING
            - DELIVERED
            - FAILED
            - REJECTED
            - UNKNOWN

        is_final:
            True, når status betragtes som afsluttende.

        is_success:
            True ved en endelig positiv status.

        received_at:
            Tidspunktet, hvor beskeden blev leveret til Dueslaget.

        serviceplatform_transaction_id:
            TransmissionId fra PKO_PostStatus.

        memo_message_uuid:
            MessageUUID fra PKO_PostStatus.

        digital_post_id:
            MessageId fra PKO_PostStatus.

            Dette felt er ikke det samme som MessageUUID.

        physical_shipment_id:
            AfsendelseIdentifikator fra PKO_PostStatus.

            Feltet forventes anvendt til at matche fysisk post med
            den shipment_id, som blev gemt ved afsendelsen.

        related_object_id:
            UUID fra den ydre beskedkuvert:

                RelateretObjekt
                / ObjektId
                / UUIDIdentifikator

            Feltet identificerer det systemrelaterede objekt, som
            kvitteringen vedrører.

        correlation_id:
            CorrelationId fra PKO_PostStatus.

        channel:
            Normaliseret kanal, eksempelvis DIGITAL_POST eller
            PHYSICAL_POST.

        actual_delivery:
            Faktisk leveringstidspunkt, når dette findes og kan
            udledes sikkert.

        status_code:
            Den oprindelige TransaktionsStatusKode.

        status_message:
            Fejltekst eller oprindelig statuskode.

        error_code:
            FejlKode eller FejlId fra FejlDetaljer.

        broker_message_id:
            BeskedId fra den ydre Beskedfordeler-kuvert.

        subscription_expression_id:
            ID'et på abonnementsudtrykket, som leverede beskeden.
    """

    status: ReceiptStatus
    is_final: bool
    is_success: bool
    received_at: datetime
    serviceplatform_transaction_id: str | None = None
    memo_message_uuid: str | None = None
    digital_post_id: str | None = None
    physical_shipment_id: str | None = None
    related_object_id: str | None = None
    correlation_id: str | None = None
    channel: str | None = None
    actual_delivery: datetime | None = None
    status_code: str | None = None
    status_message: str | None = None
    error_code: str | None = None
    broker_message_id: str | None = None
    subscription_expression_id: str | None = None


@dataclass(frozen=True, slots=True)
class BrokerMessage:
    """Rå besked og metadata fra Beskedfordeleren."""
    body: bytes
    delivery_tag: int
    routing_key: str | None = None
    redelivered: bool = False
