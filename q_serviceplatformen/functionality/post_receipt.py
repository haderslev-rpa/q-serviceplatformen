"""Parser kvitteringer fra KOMBIT Beskedfordeleren."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from xml.etree import ElementTree

from q_serviceplatformen.functionality.post_models import DigitalPostReceipt


def parse_post_receipt(raw_xml: bytes) -> DigitalPostReceipt:
    """Fortolk en Haendelsesbesked og returnér en DigitalPostReceipt.

    Output:
        En normaliseret kvittering. Den ydre Beskedfordeler-kuvert og den
        base64-kodede PKO_PostStatus læses begge.
    """
    if not isinstance(raw_xml, bytes):
        raise TypeError("raw_xml skal være bytes.")
    if not raw_xml:
        raise ValueError("raw_xml må ikke være tom.")

    try:
        envelope = ElementTree.fromstring(raw_xml)
    except ElementTree.ParseError as error:
        raise ValueError("Brokerbeskeden er ikke gyldig XML.") from error

    broker_message_id = _first_text_below(envelope, "BeskedId", "UUIDIdentifikator")
    subscription_expression_id = _first_text_below(
        envelope, "ErLeveretIHenholdTil", "UUIDIdentifikator"
    )
    received_at = _parse_datetime(
        _first_text_below(envelope, "LeveranceTidspunkt", "TidsstempelDatoTid")
        or _first_text_below(envelope, "Dannelsestidspunkt", "TidsstempelDatoTid")
    )

    base64_element = next(
        (element for element in envelope.iter() if _local_name(element.tag) == "Base64"),
        None,
    )
    if base64_element is None or not (base64_element.text or "").strip():
        raise ValueError("Brokerbeskeden mangler Beskeddata/Base64.")

    try:
        payload_bytes = base64.b64decode(base64_element.text.strip(), validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("Beskeddata/Base64 er ikke gyldig base64.") from error

    try:
        payload = ElementTree.fromstring(payload_bytes)
    except ElementTree.ParseError as error:
        raise ValueError("Den indlejrede kvittering er ikke gyldig XML.") from error

    values = {
        _local_name(element.tag): element.text.strip()
        for element in payload.iter()
        if element.text and element.text.strip()
    }
    status_code = values.get("TransaktionsStatusKode")
    error_code, error_message = _read_error_details(payload)
    status = _normalize_status(status_code, error_code)
    channel = _normalize_channel(values.get("KanalKode"))
    transaction_time = _parse_datetime(values.get("TransaktionsDatoTid"))

    return DigitalPostReceipt(
        status=status,
        is_final=status in {"DELIVERED", "FAILED", "REJECTED"},
        is_success=status == "DELIVERED",
        received_at=received_at or transaction_time or datetime.now(timezone.utc),
        serviceplatform_transaction_id=values.get("TransmissionId"),
        memo_message_uuid=values.get("MessageUUID"),
        digital_post_id=values.get("MessageUUID"),
        physical_shipment_id=values.get("AfsendelseIdentifikator"),
        correlation_id=values.get("CorrelationId"),
        channel=channel,
        actual_delivery=transaction_time if status == "DELIVERED" else None,
        status_code=status_code,
        status_message=error_message or status_code,
        error_code=error_code,
        broker_message_id=broker_message_id,
        subscription_expression_id=subscription_expression_id,
    )


def _normalize_status(status_code: str | None, error_code: str | None) -> str:
    text = (status_code or "").strip().casefold()
    if error_code:
        return "FAILED"
    if any(word in text for word in ("afleveret", "leveret", "delivered")):
        return "DELIVERED"
    if any(word in text for word in ("afvist", "rejected")):
        return "REJECTED"
    if any(word in text for word in ("fejl", "failed")):
        return "FAILED"
    if any(word in text for word in ("afventer", "behandles", "pending")):
        return "PENDING"
    return "UNKNOWN"


def _normalize_channel(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    if "digital" in normalized:
        return "DIGITAL_POST"
    if "fysisk" in normalized or "physical" in normalized:
        return "PHYSICAL_POST"
    return value.strip()


def _read_error_details(root: ElementTree.Element) -> tuple[str | None, str | None]:
    error_element = next(
        (element for element in root.iter() if _local_name(element.tag) == "FejlDetaljer"),
        None,
    )
    if error_element is None or len(error_element) == 0:
        return None, None
    values = {
        _local_name(element.tag): element.text.strip()
        for element in error_element.iter()
        if element.text and element.text.strip()
    }
    code = values.get("FejlKode") or values.get("FejlId")
    message = values.get("FejlTekst") or values.get("FejlBeskrivelse")
    return code, message


def _first_text_below(root: ElementTree.Element, parent_name: str, child_name: str) -> str | None:
    for parent in root.iter():
        if _local_name(parent.tag) != parent_name:
            continue
        for child in parent.iter():
            if _local_name(child.tag) == child_name and child.text:
                value = child.text.strip()
                if value:
                    return value
    return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip().replace("Z", "+00:00")
    try:
        result = datetime.fromisoformat(cleaned)
    except ValueError as error:
        raise ValueError(f"Ugyldigt tidspunkt i kvitteringen: {value!r}.") from error
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]
