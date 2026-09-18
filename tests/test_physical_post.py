"""
Test af den offentlige facade til fysisk post.

Testdata hentes fra .env.

RUN_LIVE_PHYSICAL_POST_TEST=0:
    XML-requesten gemmes lokalt uden afsendelse.

RUN_LIVE_PHYSICAL_POST_TEST=1:
    Forsendelsen sendes præcis én gang.
"""

import os
import uuid
from pathlib import Path
from xml.dom import minidom

from dotenv import load_dotenv

from q_serviceplatformen.functionality.digital_post_models import (
    DigitalPostDocument,
)
from q_serviceplatformen.functionality.send_physical_post import (
    PhysicalPostSendResult,
    send_physical_post,
)


load_dotenv(override=True)


TEST_LOCAL_DIRECTORY = (
    Path(__file__).resolve().parent
    / "test_local"
)

XML_PREVIEW_PATH = (
    TEST_LOCAL_DIRECTORY
    / "physical_post_preview.xml"
)


def _require_environment_text(
    variable_name: str,
) -> str:
    """
    Henter en obligatorisk tekstværdi fra .env.

    Output:
        Den rensede tekstværdi.

    Fejl:
        RuntimeError, hvis variablen mangler eller er tom.
    """
    value = os.getenv(variable_name, "").strip()

    if not value:
        raise RuntimeError(
            f"Miljøvariablen {variable_name} mangler eller er tom."
        )

    return value


def _get_optional_environment_text(
    variable_name: str,
) -> str | None:
    """
    Henter en valgfri tekstværdi fra .env.

    Output:
        Den rensede tekst eller None.
    """
    value = os.getenv(variable_name, "").strip()

    return value or None


def _should_send_live() -> bool:
    """
    Afgør, om testen skal sende rigtig fysisk post.

    Output:
        False ved RUN_LIVE_PHYSICAL_POST_TEST=0.
        True ved RUN_LIVE_PHYSICAL_POST_TEST=1.

    Fejl:
        ValueError ved andre værdier.
    """
    value = os.getenv(
        "RUN_LIVE_PHYSICAL_POST_TEST",
        "0",
    ).strip()

    if value == "0":
        return False

    if value == "1":
        return True

    raise ValueError(
        "RUN_LIVE_PHYSICAL_POST_TEST skal være 0 eller 1."
    )


def _format_xml(
    xml_text: str,
) -> str:
    """
    Formaterer XML til læsevenlig tekst.

    Output:
        XML med indrykninger og linjeskift.
    """
    parsed_xml = minidom.parseString(
        xml_text.encode("utf-8")
    )

    return parsed_xml.toprettyxml(
        indent="    ",
        encoding=None,
    )


def main() -> None:
    """
    Bygger og eventuelt sender fysisk post.

    Output ved preview:
        XML-requesten gemmes i tests/test_local.

    Output ved live-test:
        PhysicalPostSendResult udskrives.

    Forsendelsen kaldes højst én gang pr. testkørsel.
    """
    send_live = _should_send_live()

    pdf_path = Path(
        _require_environment_text(
            "PHYSICAL_POST_PDF_PATH"
        )
    )

    if not pdf_path.is_file():
        raise FileNotFoundError(
            f"PDF-filen blev ikke fundet: {pdf_path}"
        )

    document = DigitalPostDocument(
        content=pdf_path.read_bytes(),
        file_name=pdf_path.name,
        document_id=str(uuid.uuid4()),
        label=pdf_path.stem,
    )

    print("")
    print(f"PDF-fil: {document.file_name}")
    print(f"PDF-størrelse: {len(document.content)} bytes")
    print(
        "Tilstand: "
        f"{'LIVE-AFSENDELSE' if send_live else 'KUN PREVIEW'}"
    )
    print("")

    result = send_physical_post(
        recipient_name=_require_environment_text(
            "PHYSICAL_POST_RECIPIENT_NAME"
        ),
        street_name=_require_environment_text(
            "PHYSICAL_POST_STREET_NAME"
        ),
        house_number=_require_environment_text(
            "PHYSICAL_POST_HOUSE_NUMBER"
        ),
        floor=_get_optional_environment_text(
            "PHYSICAL_POST_FLOOR"
        ),
        door=_get_optional_environment_text(
            "PHYSICAL_POST_DOOR"
        ),
        post_code=_require_environment_text(
            "PHYSICAL_POST_POST_CODE"
        ),
        city=_require_environment_text(
            "PHYSICAL_POST_CITY"
        ),
        country_code=_require_environment_text(
            "PHYSICAL_POST_COUNTRY_CODE"
        ),
        document=document,
        dry_run=not send_live,
    )

    if not send_live:
        if not isinstance(result, str):
            raise RuntimeError(
                "Preview forventede XML som tekst."
            )

        TEST_LOCAL_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        XML_PREVIEW_PATH.write_text(
            _format_xml(result),
            encoding="utf-8",
        )

        print("Forsendelsen blev ikke sendt.")
        print("XML-requesten er gemt her:")
        print(XML_PREVIEW_PATH)
        return

    if not isinstance(
        result,
        PhysicalPostSendResult,
    ):
        raise RuntimeError(
            "Live-afsendelsen returnerede et ukendt resultat."
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
    print(
        "Resultatet dokumenterer indsendelse, "
        "ikke endelig levering."
    )


if __name__ == "__main__":
    main()