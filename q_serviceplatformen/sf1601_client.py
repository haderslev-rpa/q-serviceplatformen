"""Internt HTTP-klientlag til SF1601 på Serviceplatformen."""

from __future__ import annotations

import urllib.parse
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from xml.etree import ElementTree

import requests
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig

from q_serviceplatformen.authentication import KombitAccess
from q_serviceplatformen.configuration import REQUEST_TIMEOUT_SECONDS
from q_serviceplatformen.date_helper import format_datetime
from q_serviceplatformen.models import xml_util
from q_serviceplatformen.models.message import Message
from q_serviceplatformen.models.physical_mail import (
    ForsendelseI,
    ForsendelseISamling,
    KombiRequest,
)

POSTFORESPOERG_ENTITY_ID = (
    "http://entityid.kombit.dk/service/postforespoerg/1"
)
KOMBI_POST_ENTITY_ID = (
    "http://entityid.kombit.dk/service/kombipostafsend/1"
)


@dataclass(frozen=True, slots=True)
class KombiResponse:
    """Internt fortolket svar fra KombiPostAfsend."""

    transaction_id: str
    transmission_id: str | None
    advis_id: str | None
    advis_text: str | None


def is_registered(
    id_: str,
    service: Literal["digitalpost", "nemsms"],
    kombit_access: KombitAccess,
) -> bool:
    """Returnerer registreringsstatus fra PostForespoerg."""
    url = urllib.parse.urljoin(
        kombit_access.environment,
        f"service/PostForespoerg_1/{service}",
    )
    identifier = "cprNumber" if len(id_) == 10 else "cvrNumber"
    headers = {
        "X-TransaktionsId": str(uuid.uuid4()),
        "X-TransaktionsTid": format_datetime(datetime.now()),
        "Authorization": kombit_access.get_access_token(
            POSTFORESPOERG_ENTITY_ID
        ),
    }
    response = requests.get(
        url,
        params={identifier: id_},
        headers=headers,
        cert=kombit_access.cert_path,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    result = response.json().get("result")
    if not isinstance(result, bool):
        raise RuntimeError("PostForespoerg returnerede ikke en boolsk result-værdi.")
    return result


def send_message(
    message_type: str,
    message: Message,
    kombit_access: KombitAccess,
) -> KombiResponse:
    """Sender en MeMo-besked og returnerer det fortolkede svar."""
    if message_type not in {"Digital Post", "NemSMS"}:
        raise ValueError(
            "message_type skal være 'Digital Post' eller 'NemSMS'."
        )
    if not isinstance(message, Message):
        raise TypeError("message skal være et Message-objekt.")

    message_element = xml_util.dataclass_to_xml(message)
    kombi_request = ElementTree.Element("kombi_request")
    choice_element = ElementTree.SubElement(
        kombi_request,
        "KombiValgKode",
    )
    choice_element.text = message_type
    kombi_request.append(message_element)
    xml_body = ElementTree.tostring(
        kombi_request,
        encoding="utf-8",
        xml_declaration=False,
    )
    return _post_kombi_request(
        xml_body=xml_body,
        kombit_access=kombit_access,
    )


def build_physical_mail_xml(forsendelse: ForsendelseI) -> str:
    """Returnerer komplet fysisk kombi_request XML uden afsendelse."""
    if not isinstance(forsendelse, ForsendelseI):
        raise TypeError("forsendelse skal være et ForsendelseI-objekt.")

    request = KombiRequest(
        kombi_valg_kode="Fysisk Post",
        forsendelse_i_samling=ForsendelseISamling(
            forsendelse_i=forsendelse
        ),
    )
    serializer = XmlSerializer(
        context=XmlContext(),
        config=SerializerConfig(xml_declaration=False),
    )
    return serializer.render(request)


def send_physical_mail(
    *,
    forsendelse: ForsendelseI,
    kombit_access: KombitAccess,
) -> KombiResponse:
    """Sender fysisk post og returnerer det fortolkede svar."""
    xml_body = build_physical_mail_xml(forsendelse)
    return _post_kombi_request(
        xml_body=xml_body.encode("utf-8"),
        kombit_access=kombit_access,
    )


def _post_kombi_request(
    *,
    xml_body: bytes,
    kombit_access: KombitAccess,
) -> KombiResponse:
    """Udfører det fælles HTTP POST-kald til /kombi."""
    request_transaction_id = str(uuid.uuid4())
    url = urllib.parse.urljoin(
        kombit_access.environment,
        "service/KombiPostAfsend_1/kombi",
    )
    headers = {
        "Authorization": kombit_access.get_access_token(
            KOMBI_POST_ENTITY_ID
        ),
        "x-TransaktionsId": request_transaction_id,
        "x-TransaktionsTid": format_datetime(datetime.now()),
        "Content-Type": "application/xml",
        "Accept": "application/xml",
    }
    response = requests.post(
        url=url,
        headers=headers,
        data=xml_body,
        cert=kombit_access.cert_path,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    return _parse_kombi_response(
        response,
        request_transaction_id=request_transaction_id,
    )


def _parse_kombi_response(
    response: requests.Response,
    *,
    request_transaction_id: str,
) -> KombiResponse:
    """Validerer svaret og returnerer data uden at skrive til terminalen."""
    response_text = response.text.strip()

    if not response.ok:
        raise RuntimeError(
            "Serviceplatformen afviste forsendelsen.\n"
            f"HTTP-status: {response.status_code} {response.reason}\n"
            f"Requestens transaktions-ID: {request_transaction_id}\n"
            "Svar fra Serviceplatformen:\n"
            f"{response_text or '[Tomt svar]'}"
        )
    if not response_text:
        raise RuntimeError(
            "Serviceplatformen returnerede HTTP-succes, men svaret var tomt."
        )

    try:
        root = ElementTree.fromstring(response_text)
    except ElementTree.ParseError as error:
        raise RuntimeError(
            "Serviceplatformen returnerede ugyldig XML.\n"
            f"Svar:\n{response_text}"
        ) from error

    values: dict[str, str] = {}
    for element in root.iter():
        local_name = element.tag.rsplit("}", maxsplit=1)[-1]
        if element.text and element.text.strip():
            values[local_name.casefold()] = element.text.strip()

    result_text = values.get("result")
    if result_text is None:
        raise RuntimeError(
            "Serviceplatformens svar mangler Result.\n"
            f"Svar:\n{response_text}"
        )
    if result_text.casefold() != "true":
        error_code = values.get("fejlid") or values.get("fejlkode") or "Ukendt"
        error_text = values.get("fejltekst") or values.get("advistekst") or "Ingen fejltekst"
        raise RuntimeError(
            "Serviceplatformen accepterede ikke forsendelsen.\n"
            f"Fejlkode: {error_code}\n"
            f"Fejltekst: {error_text}\n"
            f"Requestens transaktions-ID: {request_transaction_id}\n"
            f"Svar:\n{response_text}"
        )

    transmission_id = values.get("transmissionid")
    return KombiResponse(
        transaction_id=transmission_id or request_transaction_id,
        transmission_id=transmission_id,
        advis_id=values.get("advisid"),
        advis_text=values.get("advistekst"),
    )
