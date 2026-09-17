"""
Kontrolleret live-afsendelse af Digital Post i driftsmiljøet.

Programmet læser modtager og PDF-sti fra .env, kontrollerer
driftsmiljøet og sender én Digital Post-besked.
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


def main() -> None:
    """
    Sender én PDF som Digital Post i driftsmiljøet.

    Output:
        Udskriver Serviceplatformens transaktions-ID,
        MeMo-beskedens UUID og indsendelsestidspunkt.

        En returværdi fra afsendelsen dokumenterer indsendelse,
        men ikke endelig levering. Endelig levering skal senere
        findes via en kvittering.
    """

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
        pdf_path = Path.cwd() / pdf_path

    pdf_content = _read_pdf(pdf_path)

    kombit_access = get_kombit_access()

    if kombit_access.environment != EXPECTED_ENVIRONMENT:
        raise RuntimeError(
            "Afsendelsen blev stoppet, fordi miljøet ikke er "
            "Serviceplatformens driftsmiljø."
        )

    main_document = DigitalPostDocument(
        content=pdf_content,
        file_name=pdf_path.name,
        document_id=str(uuid4()),
        label="Teknisk testbrev",
    )

    print("")
    print("Programmet sender nu rigtig Digital Post.")
    print(f"Miljø: {kombit_access.environment}")
    print(f"PDF-fil: {pdf_path.name}")
    print(f"PDF-størrelse: {len(pdf_content)} bytes")
    print("Modtagertype: CPR")
    print("CPR-nummeret udskrives ikke.")

    if skip_registration_lookup:
        print(
            "ADVARSEL: Registreringsopslaget springes over."
        )
    else:
        print(
            "Modtagerens registrering kontrolleres før afsendelse."
        )

    print("")

    try:
        result = send_digital_post(
            recipient_id=test_cpr,
            recipient_id_type="CPR",
            subject="TEST - Digital Post fra Haderslev Kommune",
            main_document=main_document,
            attachments=None,
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


def _read_pdf(pdf_path: Path) -> bytes:
    """
    Læser og kontrollerer testens PDF-fil.

    Output:
        PDF-filens indhold som bytes.

    Fejl:
        FileNotFoundError, hvis filen ikke findes.

        ValueError, hvis filen er tom eller ikke begynder
        med en PDF-signatur.
    """

    if not pdf_path.is_file():
        raise FileNotFoundError(
            "Test-PDF'en blev ikke fundet: "
            f"{pdf_path.resolve()}"
        )

    pdf_content = pdf_path.read_bytes()

    if not pdf_content:
        raise ValueError(
            "Test-PDF'en er tom."
        )

    if not pdf_content.startswith(b"%PDF-"):
        raise ValueError(
            "Testfilen er ikke en PDF."
        )

    return pdf_content


def _require_environment_value(
    variable_name: str,
) -> str:
    """
    Henter en obligatorisk værdi fra .env.

    Output:
        Miljøvariablens værdi uden mellemrum før og efter.

    Fejl:
        RuntimeError, hvis variablen mangler eller er tom.
    """

    value = os.getenv(variable_name, "").strip()

    if not value:
        raise RuntimeError(
            f"Miljøvariablen {variable_name} mangler i .env."
        )

    return value


def _raise_serviceplatform_error(
    error: HTTPError,
) -> None:
    """
    Omsætter et HTTP-svar til en mere forståelig fejl.

    Output:
        Funktionen returnerer ikke. Den rejser altid en ny
        RuntimeError med HTTP-status og det kaldte endpoint.

        Token, CPR-nummer og certifikatindhold udskrives ikke.
    """

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