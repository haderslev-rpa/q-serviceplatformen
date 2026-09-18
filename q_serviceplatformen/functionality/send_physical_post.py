"""Offentlig facade til fysisk post gennem SF1601."""

from __future__ import annotations

from datetime import datetime, timezone

from q_serviceplatformen.authentication import KombitAccess
from q_serviceplatformen.configuration import (
    get_physical_post_shipment_type_id,
)
from q_serviceplatformen.functionality.access import get_kombit_access
from q_serviceplatformen.functionality.physical_post_builder import (
    build_physical_post,
)
from q_serviceplatformen.functionality.post_models import (
    PhysicalPostSendResult,
    PostDocument,
)
from q_serviceplatformen.sf1601_client import (
    build_physical_mail_xml,
    send_physical_mail,
)


def preview_physical_post_xml(
    *,
    recipient_name: str,
    street_name: str,
    house_number: str,
    post_code: str,
    city: str,
    document: PostDocument,
    floor: str | None = None,
    door: str | None = None,
    country_code: str = "DK",
) -> str:
    """Bygger og returnerer komplet XML uden at sende noget."""
    shipment = _build_shipment(
        recipient_name=recipient_name,
        street_name=street_name,
        house_number=house_number,
        post_code=post_code,
        city=city,
        document=document,
        floor=floor,
        door=door,
        country_code=country_code,
    )
    return build_physical_mail_xml(shipment)


def send_physical_post(
    *,
    recipient_name: str,
    street_name: str,
    house_number: str,
    post_code: str,
    city: str,
    document: PostDocument,
    floor: str | None = None,
    door: str | None = None,
    country_code: str = "DK",
    kombit_access: KombitAccess | None = None,
) -> PhysicalPostSendResult:
    """Sender fysisk post og returnerer et SUBMITTED-resultat."""
    shipment = _build_shipment(
        recipient_name=recipient_name,
        street_name=street_name,
        house_number=house_number,
        post_code=post_code,
        city=city,
        document=document,
        floor=floor,
        door=door,
        country_code=country_code,
    )
    access = kombit_access or get_kombit_access()
    response = send_physical_mail(
        forsendelse=shipment,
        kombit_access=access,
    )
    return PhysicalPostSendResult(
        serviceplatform_transaction_id=response.transaction_id,
        shipment_id=shipment.afsendelse_identifikator.value,
        submitted_at=datetime.now(timezone.utc),
    )


def _build_shipment(
    *,
    recipient_name: str,
    street_name: str,
    house_number: str,
    post_code: str,
    city: str,
    document: PostDocument,
    floor: str | None,
    door: str | None,
    country_code: str,
):
    """Validerer dokumentet og bygger den fysiske XML-model."""
    if not isinstance(document, PostDocument):
        raise TypeError("document skal være et PostDocument-objekt.")
    if not isinstance(document.content, bytes):
        raise TypeError("document.content skal være bytes.")
    if not document.content.startswith(b"%PDF-"):
        raise ValueError("document.content er ikke genkendt som PDF.")
    if not document.file_name.lower().endswith(".pdf"):
        raise ValueError("document.file_name skal ende på .pdf.")

    return build_physical_post(
        shipment_type_id=get_physical_post_shipment_type_id(),
        document_content=document.content,
        recipient_name=recipient_name,
        street_name=street_name,
        house_number=house_number,
        post_code=post_code,
        city=city,
        floor=floor,
        door=door,
        country_code=country_code,
    )
