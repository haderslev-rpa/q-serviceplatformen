"""Live-test af autentificering mod Serviceplatformens driftsmiljø."""

from q_serviceplatformen.functionality.access import get_kombit_access


POSTFORESPOERG_ENTITY_ID = (
    "http://entityid.kombit.dk/service/postforespoerg/1"
)


def main() -> None:
    """
    Henter et SAML-token og et access token fra Serviceplatformen.

    Output:
        Udskriver:

        - Det valgte Serviceplatform-miljø.
        - Om SAML-tokenet blev hentet.
        - Om access tokenet blev hentet.

        Selve tokenværdierne udskrives ikke.

        Testen sender ikke Digital Post og foretager ikke opslag
        på CPR- eller CVR-numre.
    """

    print("Opretter Serviceplatform-adgang...")

    kombit_access = get_kombit_access()

    print(f"CVR: {kombit_access.cvr}")
    print(f"Miljø: {kombit_access.environment}")
    print(f"Certifikat: {kombit_access.cert_path}")

    expected_environment = "https://prod.serviceplatformen.dk"

    if kombit_access.environment != expected_environment:
        raise RuntimeError(
            "Live-testen blev stoppet, fordi det valgte miljø "
            "ikke er Serviceplatformens driftsmiljø."
        )

    print("")
    print("Henter SAML-token...")

    saml_token = kombit_access.get_saml_token(
        POSTFORESPOERG_ENTITY_ID
    )

    if not saml_token:
        raise RuntimeError(
            "Serviceplatformen returnerede et tomt SAML-token."
        )

    print("SAML-token blev hentet korrekt.")
    print("")
    print("Henter access token...")

    access_token = kombit_access.get_access_token(
        POSTFORESPOERG_ENTITY_ID
    )

    if not access_token:
        raise RuntimeError(
            "Serviceplatformen returnerede et tomt access token."
        )

    print("Access token blev hentet korrekt.")
    print("")
    print("Live-testen er gennemført.")
    print("Der blev ikke sendt Digital Post.")


if __name__ == "__main__":
    main()