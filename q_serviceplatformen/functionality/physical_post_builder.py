"""Builder til fysisk post, adskilt fra de genererede XML-modeller."""

from __future__ import annotations

from q_serviceplatformen.models.physical_mail import (
    ForsendelseI,
    create_physical_mail,
)


def build_physical_post(
    *,
    shipment_type_id: int,
    document_content: bytes,
    recipient_name: str,
    street_name: str,
    house_number: str,
    post_code: str,
    city: str,
    floor: str | None = None,
    door: str | None = None,
    country_code: str = "DK",
    shipment_id: str | None = None,
) -> ForsendelseI:
    """Bygger et valideret ForsendelseI-objekt uden at sende noget."""

    return create_physical_mail(
        forsendelse_type_identifikator=shipment_type_id,
        file_content=document_content,
        recipient_name=recipient_name,
        street_name=street_name,
        house_number=house_number,
        post_code=post_code,
        city=city,
        floor=floor,
        door=door,
        country_code=country_code,
        afsendelse_identifikator=shipment_id,
    )
