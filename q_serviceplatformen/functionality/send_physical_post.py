"""
Offentlig facade til afsendelse af fysisk post gennem SF1601.

Kaldende processer skal bruge send_physical_post() og skal ikke
selv kende de underliggende XML-modeller eller lavniveaukald.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from q_serviceplatformen import digital_post
from q_serviceplatformen.authentication import KombitAccess
from q_serviceplatformen.configuration import (
    get_physical_post_shipment_type_id,
)
from q_serviceplatformen.functionality.access import (
    get_kombit_access,
)
from q_serviceplatformen.functionality.digital_post_models import (
    DigitalPostDocument,
)
from q_serviceplatformen.models.physical_mail import (
    create_physical_mail,
)


@dataclass(frozen=True, slots=True)
class PhysicalPostSendResult:
    """
    Resultat af en accepteret fysisk post-indsendelse.

    Felter:
        serviceplatform_transaction_id:
            ID'et, som kan bruges til teknisk sporing af requesten.

            Fysisk post returnerer ikke altid et TransmissionID.
            I så fald er dette requestens x-TransaktionsId.

        shipment_id:
            Det unikke AfsendelseIdentifikator, som blev sendt i
            den fysiske post-XML.

        submitted_at:
            Tidspunktet for den accepterede indsendelse i UTC.

    Vigtigt:
        Resultatet betyder, at Serviceplatformen accepterede
        indsendelsen. Resultatet dokumenterer ikke endelig print,
        distribution eller levering.
    """

    serviceplatform_transaction_id: str
    shipment_id: str
    submitted_at: datetime


def send_physical_post(
    *,
    recipient_name: str,
    street_name: str,
    house_number: str,
    post_code: str,
    city: str,
    document: DigitalPostDocument,
    floor: str | None = None,
    door: str | None = None,
    country_code: str = "DK",
    kombit_access: KombitAccess | None = None,
    dry_run: bool = False,
) -> PhysicalPostSendResult | str:
    """
    Bygger og eventuelt sender én fysisk postforsendelse.

    Input:
        recipient_name:
            Modtagerens fulde navn.

        street_name:
            Vejnavn uden husnummer.

        house_number:
            Husnummer med eventuelt bogstav, eksempelvis "12A".

        post_code:
            Postnummer. Danske postnumre skal indeholde fire cifre.

        city:
            By eller postdistrikt.

        document:
            PDF-dokumentet, som skal sendes.

        floor:
            Valgfri etage, eksempelvis "st", "1" eller "2".

        door:
            Valgfri sidedør, eksempelvis "tv", "th" eller "3".

        country_code:
            ISO-landekode på to bogstaver. Standardværdien er DK.

        kombit_access:
            Et valgfrit eksisterende KombitAccess-objekt.

            Hvis værdien ikke angives, oprettes adgangen ud fra
            q_serviceplatformens konfiguration.

        dry_run:
            False sender fysisk post.

            True bygger og returnerer den komplette XML-request,
            men sender ikke noget.

    Output ved dry_run=False:
        Et PhysicalPostSendResult med:

        - Serviceplatformens eller requestens transaktions-ID
        - fysisk AfsendelseIdentifikator
        - indsendelsestidspunkt i UTC

    Output ved dry_run=True:
        Den komplette XML-request som tekst.

    Fejl:
        TypeError eller ValueError ved ugyldige input.

        HTTP-, adgangs- og Serviceplatform-fejl fortsætter som
        exceptions til den kaldende proces.

    Vigtigt:
        Et PhysicalPostSendResult betyder SUBMITTED.

        Det betyder ikke, at brevet er endeligt printet, distribueret
        eller leveret.
    """
    if not isinstance(document, DigitalPostDocument):
        raise TypeError(
            "document skal være et DigitalPostDocument-objekt."
        )

    if not isinstance(dry_run, bool):
        raise TypeError(
            "dry_run skal være True eller False."
        )

    if not isinstance(document.content, bytes):
        raise TypeError(
            "document.content skal være bytes."
        )

    if not document.content:
        raise ValueError(
            "document.content må ikke være tom."
        )

    if not document.content.startswith(b"%PDF-"):
        raise ValueError(
            "document.content er ikke genkendt som en PDF."
        )

    if not isinstance(document.file_name, str):
        raise TypeError(
            "document.file_name skal være tekst."
        )

    if not document.file_name.strip().lower().endswith(".pdf"):
        raise ValueError(
            "document.file_name skal ende på .pdf."
        )

    shipment_type_id = (
        get_physical_post_shipment_type_id()
    )

    forsendelse = create_physical_mail(
        forsendelse_type_identifikator=shipment_type_id,
        file_content=document.content,
        recipient_name=recipient_name,
        street_name=street_name,
        house_number=house_number,
        floor=floor,
        door=door,
        post_code=post_code,
        city=city,
        country_code=country_code,
    )

    access = kombit_access or get_kombit_access()

    send_result = digital_post.send_physical_mail(
        forsendelse=forsendelse,
        kombit_access=access,
        dry_run=dry_run,
    )

    if dry_run:
        return send_result

    shipment_id = (
        forsendelse.afsendelse_identifikator.value
    )

    return PhysicalPostSendResult(
        serviceplatform_transaction_id=send_result,
        shipment_id=shipment_id,
        submitted_at=datetime.now(timezone.utc),
    )