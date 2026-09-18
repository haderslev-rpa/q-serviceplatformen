"""Preview eller live-test af den offentlige fysiske post-facade."""

import os
import uuid
from pathlib import Path
from xml.dom import minidom

from dotenv import load_dotenv

from q_serviceplatformen import (
    PhysicalPostSendResult,
    PostDocument,
    preview_physical_post_xml,
    send_physical_post,
)

load_dotenv(override=True)

TEST_LOCAL_DIRECTORY = Path(__file__).resolve().parent / "test_local"
XML_PREVIEW_PATH = TEST_LOCAL_DIRECTORY / "physical_post_preview.xml"


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Miljøvariablen {name} mangler eller er tom.")
    return value


def _optional(name: str) -> str | None:
    return os.getenv(name, "").strip() or None


def _send_live() -> bool:
    value = os.getenv("RUN_LIVE_PHYSICAL_POST_TEST", "0").strip()
    if value not in {"0", "1"}:
        raise ValueError("RUN_LIVE_PHYSICAL_POST_TEST skal være 0 eller 1.")
    return value == "1"


def _format_xml(xml_text: str) -> str:
    return minidom.parseString(xml_text.encode("utf-8")).toprettyxml(
        indent="    ",
        encoding=None,
    )


def main() -> None:
    """Bygger preview eller sender præcis én fysisk forsendelse."""
    send_live = _send_live()
    pdf_path = Path(_required("PHYSICAL_POST_PDF_PATH"))
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF-filen blev ikke fundet: {pdf_path}")

    document = PostDocument(
        content=pdf_path.read_bytes(),
        file_name=pdf_path.name,
        document_id=str(uuid.uuid4()),
        label=pdf_path.stem,
    )
    kwargs = {
        "recipient_name": _required("PHYSICAL_POST_RECIPIENT_NAME"),
        "street_name": _required("PHYSICAL_POST_STREET_NAME"),
        "house_number": _required("PHYSICAL_POST_HOUSE_NUMBER"),
        "floor": _optional("PHYSICAL_POST_FLOOR"),
        "door": _optional("PHYSICAL_POST_DOOR"),
        "post_code": _required("PHYSICAL_POST_POST_CODE"),
        "city": _required("PHYSICAL_POST_CITY"),
        "country_code": _required("PHYSICAL_POST_COUNTRY_CODE"),
        "document": document,
    }

    if not send_live:
        xml_text = preview_physical_post_xml(**kwargs)
        TEST_LOCAL_DIRECTORY.mkdir(parents=True, exist_ok=True)
        XML_PREVIEW_PATH.write_text(
            _format_xml(xml_text),
            encoding="utf-8",
        )
        print("Forsendelsen blev ikke sendt.")
        print(f"XML-requesten er gemt her: {XML_PREVIEW_PATH}")
        return

    result = send_physical_post(**kwargs)
    if not isinstance(result, PhysicalPostSendResult):
        raise RuntimeError("Fysisk post returnerede et ukendt resultat.")
    print("Serviceplatformen accepterede indsendelsen.")
    print(f"Transaktions-ID: {result.serviceplatform_transaction_id}")
    print(f"Afsendelses-ID: {result.shipment_id}")
    print(f"Indsendt: {result.submitted_at.isoformat()}")
    print("Resultatet dokumenterer indsendelse, ikke endelig levering.")


if __name__ == "__main__":
    main()
