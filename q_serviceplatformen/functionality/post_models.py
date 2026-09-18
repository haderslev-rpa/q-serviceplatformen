"""Offentlige input- og resultatmodeller til q-serviceplatformen."""

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
class PostDocument:
    """Ét PDF-dokument, som kan bruges til digital eller fysisk post."""

    content: bytes
    file_name: str
    document_id: str
    label: str | None = None


# Bagudkompatibelt navn. Ny kode bør bruge PostDocument.
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
    """Fortolket kvittering fra Beskedfordeleren."""

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
    """Rå besked og metadata fra Beskedfordeleren."""

    body: bytes
    delivery_tag: int
    routing_key: str | None = None
    redelivered: bool = False
