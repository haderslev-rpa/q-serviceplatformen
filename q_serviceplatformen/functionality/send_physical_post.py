"""Offentlig facade til fysisk post gennem SF1601."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from q_serviceplatformen.authentication import KombitAccess
from q_serviceplatformen.configuration import (
    get_physical_post_shipment_type_id,
)
from q_serviceplatformen.functionality.access import (
    get_kombit_access,
)
from q_serviceplatformen.functionality.physical_post_attachments import (
    build_physical_post_attachment_collection,
    validate_physical_post_documents,
)
from q_serviceplatformen.functionality.physical_post_builder import (
    build_physical_post,
)
from q_serviceplatformen.functionality.post_models import (
    PhysicalPostSendResult,
    PostDocument,
)
from q_serviceplatformen.models.physical_mail import (
    ForsendelseI,
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
    attachments: Sequence[PostDocument] | None = None,
    floor: str | None = None,
    door: str | None = None,
    country_code: str = "DK",
) -> str:
    """
    Bygger og returnerer komplet XML uden at sende noget.

    attachments:
        Valgfri rækkefølge af PDF-bilag. Bilagene indsættes i
        BilagSamling i samme rækkefølge, som de modtages.
    """
    shipment = _build_shipment(
        recipient_name=recipient_name,
        street_name=street_name,
        house_number=house_number,
        post_code=post_code,
        city=city,
        document=document,
        attachments=attachments,
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
    attachments: Sequence[PostDocument] | None = None,
    floor: str | None = None,
    door: str | None = None,
    country_code: str = "DK",
    kombit_access: KombitAccess | None = None,
) -> PhysicalPostSendResult:
    """
    Sender fysisk post og returnerer et SUBMITTED-resultat.

    attachments:
        Valgfri rækkefølge af PDF-bilag. Bilagene sendes som
        indlejrede SF1601-bilag efter hoveddokumentet.

    Vigtigt:
        Resultatet dokumenterer, at Serviceplatformen har accepteret
        indsendelsen. Det dokumenterer ikke endelig fysisk levering.
    """
    shipment = _build_shipment(
        recipient_name=recipient_name,
        street_name=street_name,
        house_number=house_number,
        post_code=post_code,
        city=city,
        document=document,
        attachments=attachments,
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
    attachments: Sequence[PostDocument] | None,
    floor: str | None,
    door: str | None,
    country_code: str,
) -> ForsendelseI:
    """
    Valider hoveddokument og bilag og byg den fysiske XML-model.

    Output:
        Et ForsendelseI-objekt med hoveddokument og eventuel
        BilagSamling.

    Fejl:
        TypeError ved forkerte inputtyper.
        ValueError ved ugyldig PDF, for mange bilag eller
        overskridelse af størrelsesgrænsen.
    """
    validated_document, validated_attachments = (
        validate_physical_post_documents(
            document=document,
            attachments=attachments,
        )
    )

    shipment = build_physical_post(
        shipment_type_id=(
            get_physical_post_shipment_type_id()
        ),
        document_content=validated_document.content,
        recipient_name=recipient_name,
        street_name=street_name,
        house_number=house_number,
        post_code=post_code,
        city=city,
        floor=floor,
        door=door,
        country_code=country_code,
    )

    shipment.bilag_samling = (
        build_physical_post_attachment_collection(
            validated_attachments
        )
    )

    return shipment