"""Live-test af den offentlige PostForespoerg-facade."""

import os

from dotenv import load_dotenv

from q_serviceplatformen import check_registration

load_dotenv(override=True)


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Miljøvariablen {name} mangler eller er tom.")
    return value


def main() -> None:
    """Udskriver True eller False uden at sende post."""
    recipient_type = _required(
        "POSTFORESPOERG_TEST_RECIPIENT_ID_TYPE"
    ).upper()
    result = check_registration(
        recipient_id=_required("POSTFORESPOERG_TEST_RECIPIENT_ID"),
        recipient_id_type=recipient_type,
        service="digitalpost",
    )
    print(f"Resultat fra PostForespoerg: {result}")
    print(
        "Modtageren er registreret til Digital Post."
        if result
        else "Modtageren er ikke registreret til Digital Post."
    )


if __name__ == "__main__":
    main()
