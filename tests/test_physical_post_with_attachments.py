"""Preview eller live-test af fysisk post med to PDF-bilag."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from xml.dom import minidom

from dotenv import load_dotenv

from q_serviceplatformen.functionality.post_models import (
    PhysicalPostSendResult,
    PostDocument,
)
from q_serviceplatformen.functionality.send_physical_post import (
    preview_physical_post_xml,
    send_physical_post,
)

load_dotenv(override=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_LOCAL_DIRECTORY = PROJECT_ROOT / "tests_local"

BILAG_PATHS = [
    TEST_LOCAL_DIRECTORY / "Bilag-1-test.pdf",
    TEST_LOCAL_DIRECTORY / "Bilag-2-test.pdf",
]

XML_PREVIEW_PATH = (
    TEST_LOCAL_DIRECTORY
    / "physical_post_with_attachments_preview.xml"
)


def _required(name: str) -> str:
    """Hent en obligatorisk miljøvariabel."""
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Miljøvariablen {name} mangler eller er tom."
        )

    return value


def _optional(name: str) -> str | None:
    """Hent en valgfri miljøvariabel."""
    return os.getenv(name, "").strip() or None


def _send_live() -> bool:
    """Afgør om testen må sende til Serviceplatformen."""
    value = os.getenv(
        "RUN_LIVE_PHYSICAL_POST_TEST",
        "0",
    ).strip()

    if value not in {"0", "1"}:
        raise ValueError(
            "RUN_LIVE_PHYSICAL_POST_TEST skal være 0 eller 1."
        )

    return value == "1"


def _resolve_path(raw_path: str) -> Path:
    """Gør en relativ sti fra .env relativ til repositoryets rod."""
    path = Path(raw_path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


def _build_document(path: Path) -> PostDocument:
    """Læs og validér én PDF og returnér et PostDocument."""
    if not path.is_file():
        raise FileNotFoundError(
            f"PDF-filen blev ikke fundet: {path}"
        )

    content = path.read_bytes()

    if not content:
        raise ValueError(
            f"PDF-filen er tom: {path}"
        )

    if not content.startswith(b"%PDF-"):
        raise ValueError(
            f"Filen er ikke en gyldig PDF: {path}"
        )

    return PostDocument(
        content=content,
        file_name=path.name,
        document_id=str(uuid.uuid4()),
        label=path.name,
    )


def _format_xml(xml_text: str) -> str:
    """Formatér XML, så previewfilen er læsbar."""
    return minidom.parseString(
        xml_text.encode("utf-8")
    ).toprettyxml(
        indent="    ",
        encoding=None,
    )


def main() -> None:
    """Byg preview eller send én fysisk forsendelse med to bilag."""
    main_document_path = _resolve_path(
        _required("PHYSICAL_POST_PDF_PATH")
    )

    main_document = _build_document(
        main_document_path
    )

    attachments = [
        _build_document(path)
        for path in BILAG_PATHS
    ]

    kwargs = {
        "recipient_name": _required(
            "PHYSICAL_POST_RECIPIENT_NAME"
        ),
        "street_name": _required(
            "PHYSICAL_POST_STREET_NAME"
        ),
        "house_number": _required(
            "PHYSICAL_POST_HOUSE_NUMBER"
        ),
        "floor": _optional(
            "PHYSICAL_POST_FLOOR"
        ),
        "door": _optional(
            "PHYSICAL_POST_DOOR"
        ),
        "post_code": _required(
            "PHYSICAL_POST_POST_CODE"
        ),
        "city": _required(
            "PHYSICAL_POST_CITY"
        ),
        "country_code": (
            os.getenv(
                "PHYSICAL_POST_COUNTRY_CODE",
                "DK",
            ).strip()
            or "DK"
        ),
        "document": main_document,
        "attachments": attachments,
    }

    print(f"Hoveddokument: {main_document_path}")
    print("Bilag:")
    for index, path in enumerate(
        BILAG_PATHS,
        start=1,
    ):
        print(f"  {index}. {path}")

    if not _send_live():
        xml_text = preview_physical_post_xml(
            **kwargs
        )

        XML_PREVIEW_PATH.write_text(
            _format_xml(xml_text),
            encoding="utf-8",
        )

        print("")
        print("Forsendelsen blev ikke sendt.")
        print(
            "XML-preview er gemt her: "
            f"{XML_PREVIEW_PATH}"
        )
        return

    result = send_physical_post(
        **kwargs
    )

    if not isinstance(
        result,
        PhysicalPostSendResult,
    ):
        raise RuntimeError(
            "Fysisk post returnerede et ukendt resultat."
        )

    print("")
    print("Serviceplatformen accepterede indsendelsen.")
    print(
        "Transaktions-ID: "
        f"{result.serviceplatform_transaction_id}"
    )
    print(
        "Afsendelses-ID: "
        f"{result.shipment_id}"
    )
    print(
        "Indsendt: "
        f"{result.submitted_at.isoformat()}"
    )


if __name__ == "__main__":
    main()