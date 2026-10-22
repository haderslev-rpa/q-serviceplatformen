"""
Kontrolleret live-afsendelse af Digital Post med to PDF-bilag
i Serviceplatformens driftsmiljø.

Programmet læser modtager og hoveddokumentets PDF-sti fra .env.
Bilagene læses fra repositoryets tests_local-mappe:
- Bilag-1-test.pdf
- Bilag-2-test.pdf
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from requests.exceptions import HTTPError

from q_serviceplatformen.functionality.access import get_kombit_access
from q_serviceplatformen.functionality.digital_post_models import (
    DigitalPostDocument,
)
from q_serviceplatformen.functionality.send_digital_post import (
    send_digital_post,
)


EXPECTED_ENVIRONMENT = "https://prod.serviceplatformen.dk"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_LOCAL_DIRECTORY = PROJECT_ROOT / "tests_local"

ATTACHMENT_PATHS = (
    TEST_LOCAL_DIRECTORY / "Bilag-1-test.pdf",
    TEST_LOCAL_DIRECTORY / "Bilag-2-test.pdf",
)


def main() -> None:
    """Send et hoveddokument og to PDF-bilag som Digital Post."""
    load_dotenv(override=True)

    test_cpr = _require_environment_value(
        "DIGITAL_POST_TEST_CPR"
    )
    pdf_path_value = _require_environment_value(
        "DIGITAL_POST_TEST_PDF_PATH"
    )

    skip_registration_lookup = (
        os.getenv(
            "DIGITAL_POST_SKIP_REGISTRATION_LOOKUP",
            "0",
        ).strip()
        == "1"
    )

    pdf_path = Path(pdf_path_value).expanduser()

    if not pdf_path.is_absolute():
        pdf_path = PROJECT_ROOT / pdf_path

    main_document = _build_document(
        pdf_path,
        label="Teknisk testbrev",
    )

    attachments = [
        _build_document(
            attachment_path,
            label=attachment_path.stem,
        )
        for attachment_path in ATTACHMENT_PATHS
    ]

    kombit_access = get_kombit_access()

    if kombit_access.environment != EXPECTED_ENVIRONMENT:
        raise RuntimeError(
            "Afsendelsen blev stoppet, fordi miljøet ikke er "
            "Serviceplatformens driftsmiljø."
        )

    total_size = len(main_document.content) + sum(
        len(attachment.content)
        for attachment in attachments
    )

    print("")
    print("Programmet sender nu rigtig Digital Post med bilag.")
    print(f"Miljø: {kombit_access.environment}")
    print(f"Hoveddokument: {main_document.file_name}")
    print(f"Antal bilag: {len(attachments)}")

    for number, attachment in enumerate(
        attachments,
        start=1,
    ):
        print(
            f"Bilag {number}: {attachment.file_name} "
            f"({len(attachment.content)} bytes)"
        )

    print(f"Samlet dokumentstørrelse: {total_size} bytes")
    print("Modtagertype: CPR")
    print("CPR-nummeret udskrives ikke.")

    if skip_registration_lookup:
        print(
            "ADVARSEL: Registreringsopslaget springes over."
        )
    else:
        print(
            "Modtagerens registrering kontrolleres "
            "før afsendelse."
        )

    print("")

    try:
        result = send_digital_post(
            recipient_id=test_cpr,
            recipient_id_type="CPR",
            subject=(
                "TEST - Digital Post med bilag fra "
                "Haderslev Kommune"
            ),
            main_document=main_document,
            attachments=attachments,
            kombit_access=kombit_access,
            check_registration=(
                not skip_registration_lookup
            ),
        )
    except HTTPError as error:
        _raise_serviceplatform_error(error)

    print("Serviceplatformen accepterede afsendelseskaldet.")
    print(
        "Transaktions-ID: "
        f"{result.serviceplatform_transaction_id}"
    )
    print(
        "MeMo messageUUID: "
        f"{result.memo_message_uuid}"
    )
    print(
        "Indsendt: "
        f"{result.submitted_at.isoformat()}"
    )
    print("")
    print(
        "Bemærk: Resultatet dokumenterer indsendelse, "
        "ikke endelig levering."
    )


def _build_document(
    pdf_path: Path,
    *,
    label: str,
) -> DigitalPostDocument:
    """Læs en PDF og byg q-serviceplatformens dokumentmodel."""
    pdf_content = _read_pdf(pdf_path)

    return DigitalPostDocument(
        content=pdf_content,
        file_name=pdf_path.name,
        document_id=str(uuid4()),
        label=label,
    )


def _read_pdf(pdf_path: Path) -> bytes:
    """Læs og kontrollér en PDF-fil."""
    if not pdf_path.is_file():
        raise FileNotFoundError(
            "PDF-filen blev ikke fundet: "
            f"{pdf_path.resolve()}"
        )

    pdf_content = pdf_path.read_bytes()

    if not pdf_content:
        raise ValueError(
            f"PDF-filen er tom: {pdf_path.name}"
        )

    if not pdf_content.startswith(b"%PDF-"):
        raise ValueError(
            f"Filen er ikke en PDF: {pdf_path.name}"
        )

    return pdf_content


def _require_environment_value(
    variable_name: str,
) -> str:
    """Hent en obligatorisk værdi fra .env."""
    value = os.getenv(variable_name, "").strip()

    if not value:
        raise RuntimeError(
            f"Miljøvariablen {variable_name} mangler i .env."
        )

    return value


def _raise_serviceplatform_error(
    error: HTTPError,
) -> None:
    """Omsæt et HTTP-svar til en sikker og forståelig fejl."""
    response = error.response

    if response is None:
        raise RuntimeError(
            "Serviceplatform-kaldet fejlede uden et HTTP-svar."
        ) from error

    safe_url = response.url.split("?", maxsplit=1)[0]

    if response.status_code == 401:
        raise RuntimeError(
            "Serviceplatformen svarede 401 Unauthorized ved kald til "
            f"{safe_url}. "
            "Hvis fejlen opstår ved PostForespoerg_1, skal "
            "serviceaftalen have entity ID "
            "'http://entityid.kombit.dk/service/postforespoerg/1'."
        ) from error

    raise RuntimeError(
        "Serviceplatform-kaldet fejlede med HTTP-status "
        f"{response.status_code} ved {safe_url}."
    ) from error


if __name__ == "__main__":
    main()