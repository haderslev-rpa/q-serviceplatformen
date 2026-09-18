"""This module contains helper functions to use the SF1601 Kombit API.
https://digitaliseringskataloget.dk/integration/sf1601
"""

import urllib.parse
import uuid
from datetime import datetime
from typing import Literal
from xml.etree import ElementTree


import requests
from q_serviceplatformen.configuration import REQUEST_TIMEOUT_SECONDS
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig

from q_serviceplatformen.authentication import KombitAccess
from q_serviceplatformen.date_helper import format_datetime
from q_serviceplatformen.models import xml_util

from q_serviceplatformen.models.message import Message
from q_serviceplatformen.models.physical_mail import ForsendelseI, ForsendelseISamling, KombiRequest


def is_registered(id_: str, service: Literal['digitalpost', 'nemsms'], kombit_access: KombitAccess) -> bool:
    """Check if the entity with the given id number is registered for
    either Digital Post or NemSMS.

    Args:
        id_: The id number of the entity to look up.
        service: The service to look up for.
        kombit_access: The KombitAccess object used to authenticate.

    Returns:
        True if the person is registered for the selected service.
    """
    url = urllib.parse.urljoin(kombit_access.environment, "service/PostForespoerg_1/")
    url = urllib.parse.urljoin(url, service)

    identifier = "cprNumber" if len(id_) == 10 else "cvrNumber"
    parameters = {
        identifier: id_
    }

    headers = {
        "X-TransaktionsId": str(uuid.uuid4()),
        "X-TransaktionsTid": format_datetime(datetime.now()),
        "authorization": kombit_access.get_access_token("http://entityid.kombit.dk/service/postforespoerg/1")
    }

    response = requests.get(url, params=parameters, headers=headers, cert=kombit_access.cert_path, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()['result']

def _parse_kombi_response(
    response: requests.Response,
    *,
    request_transaction_id: str,
) -> str:
    """
    Kontrollerer det synkrone svar fra KombiPostAfsend.

    Output:
        Hvis Serviceplatformens svar indeholder TransmissionID,
        returneres dette ID.

        Hvis svaret har Result=true, men ikke indeholder
        TransmissionID, returneres requestens x-TransaktionsId.

        Digital Post returnerer normalt TransmissionID.

        Fysisk post kan returnere Result=true og en advisering uden
        TransmissionID. I det tilfælde bruges requestens ID som
        reference.

    Vigtigt:
        Et positivt svar dokumenterer accepteret indsendelse.
        Det dokumenterer ikke endelig levering.
    """
    response_text = response.text.strip()

    if not response.ok:
        raise RuntimeError(
            "Serviceplatformen afviste forsendelsen.\n"
            f"HTTP-status: {response.status_code} "
            f"{response.reason}\n"
            f"Requestens transaktions-ID: {request_transaction_id}\n"
            "Svar fra Serviceplatformen:\n"
            f"{response_text or '[Tomt svar]'}"
        )

    if not response_text:
        raise RuntimeError(
            "Serviceplatformen returnerede HTTP-succes, "
            "men response body var tom.\n"
            f"Requestens transaktions-ID: {request_transaction_id}"
        )

    try:
        root = ElementTree.fromstring(
            response_text
        )
    except ElementTree.ParseError as error:
        raise RuntimeError(
            "Serviceplatformen returnerede HTTP-succes, "
            "men response body var ikke gyldig XML.\n"
            f"Svar:\n{response_text}"
        ) from error

    values: dict[str, str] = {}

    for element in root.iter():
        local_name = element.tag.rsplit(
            "}",
            maxsplit=1,
        )[-1]

        if element.text and element.text.strip():
            values[local_name.casefold()] = (
                element.text.strip()
            )

    result_text = values.get("result")

    if result_text is None:
        raise RuntimeError(
            "Serviceplatformens svar mangler Result.\n"
            f"Requestens transaktions-ID: "
            f"{request_transaction_id}\n"
            f"Svar:\n{response_text}"
        )

    if result_text.casefold() != "true":
        error_code = (
            values.get("fejlid")
            or values.get("fejlkode")
            or "Ukendt"
        )

        error_text = (
            values.get("fejltekst")
            or values.get("advistekst")
            or "Ingen fejltekst"
        )

        raise RuntimeError(
            "Serviceplatformen accepterede ikke forsendelsen.\n"
            f"Fejlkode: {error_code}\n"
            f"Fejltekst: {error_text}\n"
            f"Requestens transaktions-ID: "
            f"{request_transaction_id}\n"
            f"Svar:\n{response_text}"
        )

    transmission_id = values.get(
        "transmissionid"
    )

    advis_id = values.get(
        "advisid"
    )

    advis_text = values.get(
        "advistekst"
    )

    # Digital Post returnerer normalt TransmissionID.
    # Fysisk post kan returnere Result=true uden TransmissionID.
    response_transaction_id = (
        transmission_id
        or request_transaction_id
    )

    print("")
    print("Svar fra Serviceplatformen:")
    print(f"Result: {result_text}")

    if transmission_id:
        print(
            f"TransmissionID: {transmission_id}"
        )
    else:
        print(
            "TransmissionID: Ikke returneret "
            "af Serviceplatformen"
        )
        print(
            "Requestens transaktions-ID: "
            f"{request_transaction_id}"
        )

    print(
        f"AdvisId: {advis_id or 'Ikke angivet'}"
    )

    print(
        f"AdvisTekst: {advis_text or 'Ikke angivet'}"
    )

    return response_transaction_id


def send_message(
    message_type: str,
    message: Message,
    kombit_access: KombitAccess,
) -> str:
    """
    Sender en MeMo-besked gennem SF1601 KombiPostAfsend.

    Output:
        Serviceplatformens TransmissionID som tekst.

    Et positivt svar betyder, at Serviceplatformen har accepteret
    indsendelsen. Det betyder ikke, at brevet er endeligt leveret.
    """
    if message_type not in {
        "Digital Post",
        "NemSMS",
    }:
        raise ValueError(
            "message_type skal være 'Digital Post' eller 'NemSMS'."
        )

    if not isinstance(message, Message):
        raise TypeError(
            "message skal være et Message-objekt."
        )

    request_transaction_id = str(uuid.uuid4())

    url = urllib.parse.urljoin(
        kombit_access.environment,
        "service/KombiPostAfsend_1/kombi",
    )

    headers = {
        "Authorization": kombit_access.get_access_token(
            "http://entityid.kombit.dk/service/kombipostafsend/1"
        ),
        "x-TransaktionsId": request_transaction_id,
        "x-TransaktionsTid": format_datetime(
            datetime.now()
        ),
        "Content-Type": "application/xml",
        "Accept": "application/xml",
    }

    # MeMo-modellerne skal konverteres med projektets eksisterende
    # XML-funktion. xsdata XmlSerializer kan ikke serialisere
    # MessageHeader.messageType, fordi feltet bruger Literal.
    message_element = xml_util.dataclass_to_xml(
        message
    )

    kombi_request = ElementTree.Element(
        "kombi_request"
    )

    kombi_valg_kode_element = ElementTree.SubElement(
        kombi_request,
        "KombiValgKode",
    )

    kombi_valg_kode_element.text = message_type

    # Den færdige MeMo Message indsættes direkte i kombi_request.
    kombi_request.append(
        message_element
    )

    xml_body = ElementTree.tostring(
        kombi_request,
        encoding="utf-8",
        xml_declaration=False,
    )

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


def send_physical_mail(
    *,
    forsendelse: ForsendelseI,
    kombit_access: KombitAccess,
    dry_run: bool = False,
) -> str:
    """
    Bygger og eventuelt sender fysisk post gennem SF1601.

    Output ved dry_run=True:
        Den komplette XML-request som tekst. Intet sendes.

    Output ved dry_run=False:
        Serviceplatformens TransmissionID som tekst.

    Vigtigt:
        TransmissionID dokumenterer indsendelse, ikke endelig levering.
    """
    if not isinstance(forsendelse, ForsendelseI):
        raise TypeError(
            "forsendelse skal være et ForsendelseI-objekt."
        )

    if not isinstance(dry_run, bool):
        raise TypeError(
            "dry_run skal være True eller False."
        )

    kombi_request = KombiRequest(
        kombi_valg_kode="Fysisk Post",
        forsendelse_i_samling=ForsendelseISamling(
            forsendelse_i=forsendelse
        ),
    )

    serializer = XmlSerializer(
        context=XmlContext(),
        config=SerializerConfig(
            xml_declaration=False,
        ),
    )

    xml_body = serializer.render(kombi_request)

    if dry_run:
        return xml_body

    request_transaction_id = str(uuid.uuid4())

    url = urllib.parse.urljoin(
        kombit_access.environment,
        "service/KombiPostAfsend_1/kombi",
    )

    headers = {
        "Authorization": kombit_access.get_access_token(
            "http://entityid.kombit.dk/service/kombipostafsend/1"
        ),
        "x-TransaktionsId": request_transaction_id,
        "x-TransaktionsTid": format_datetime(
            datetime.now()
        ),
        "Content-Type": "application/xml",
        "Accept": "application/xml",
    }

    response = requests.post(
        url=url,
        headers=headers,
        data=xml_body.encode("utf-8"),
        cert=kombit_access.cert_path,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    return _parse_kombi_response(
        response,
        request_transaction_id=request_transaction_id,
    )

