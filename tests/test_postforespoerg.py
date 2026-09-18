"""
Live-test af PostForespoerg gennem SF1601.

Testen foretager et rigtigt registreringsopslag, men sender
ikke Digital Post eller fysisk post.

Testmodtageren hentes fra .env.

Forventet resultat:
    True:
        Modtageren er registreret til Digital Post.

    False:
        Opslaget lykkedes, men modtageren er ikke registreret.

Tekniske fejl som HTTP-fejl, timeout og adgangsfejl fortsætter
som exceptions og må ikke fortolkes som False.
"""

import os

from dotenv import load_dotenv

from q_serviceplatformen import digital_post
from q_serviceplatformen.functionality.access import (
    get_kombit_access,
)


load_dotenv(override=True)


def _require_environment_text(
    variable_name: str,
) -> str:
    """
    Henter en obligatorisk tekstværdi fra .env.

    Output:
        Miljøvariablens værdi uden mellemrum før og efter.

    Fejl:
        RuntimeError, hvis miljøvariablen mangler eller er tom.
    """
    value = os.getenv(variable_name, "").strip()

    if not value:
        raise RuntimeError(
            f"Miljøvariablen {variable_name} mangler eller er tom."
        )

    return value


def _get_normalized_recipient_id() -> tuple[str, str]:
    """
    Henter og normaliserer testmodtageren fra .env.

    Output:
        En tuple med:
            - normaliseret CPR- eller CVR-nummer
            - typen CPR eller CVR

    Fejl:
        ValueError, hvis typen eller nummerets længde er ugyldig.
    """
    recipient_id = _require_environment_text(
        "POSTFORESPOERG_TEST_RECIPIENT_ID"
    )

    recipient_id_type = _require_environment_text(
        "POSTFORESPOERG_TEST_RECIPIENT_ID_TYPE"
    ).upper()

    normalized_recipient_id = "".join(
        character
        for character in recipient_id
        if character.isdigit()
    )

    if recipient_id_type == "CPR":
        expected_length = 10
    elif recipient_id_type == "CVR":
        expected_length = 8
    else:
        raise ValueError(
            "POSTFORESPOERG_TEST_RECIPIENT_ID_TYPE skal være "
            "CPR eller CVR."
        )

    if len(normalized_recipient_id) != expected_length:
        raise ValueError(
            f"{recipient_id_type} skal indeholde præcis "
            f"{expected_length} cifre."
        )

    return normalized_recipient_id, recipient_id_type


def main() -> None:
    """
    Udfører et registreringsopslag gennem PostForespoerg.

    Output:
        Funktionen udskriver resultatet fra is_registered():

        True:
            Modtageren er registreret til Digital Post.

        False:
            Modtageren er ikke registreret til Digital Post.

        Funktionen sender ikke post.
    """
    recipient_id, recipient_id_type = (
        _get_normalized_recipient_id()
    )

    kombit_access = get_kombit_access()

    print("")
    print("Tester PostForespoerg.")
    print(f"Miljø: {kombit_access.environment}")
    print(f"Modtagertype: {recipient_id_type}")
    print("Modtagerens CPR/CVR udskrives ikke.")
    print("Der sendes ikke Digital Post eller fysisk post.")
    print("")

    result = digital_post.is_registered(
        id_=recipient_id,
        service="digitalpost",
        kombit_access=kombit_access,
    )

    print("PostForespoerg blev gennemført.")
    print(f"Resultat fra is_registered(): {result}")

    if result:
        print(
            "Betydning: Modtageren er registreret til Digital Post."
        )
    else:
        print(
            "Betydning: Modtageren er ikke registreret til "
            "Digital Post."
        )


if __name__ == "__main__":
    main()