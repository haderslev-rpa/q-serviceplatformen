"""Offentlig facade til registreringsopslag gennem PostForespoerg."""

from __future__ import annotations

from typing import Literal

from q_serviceplatformen.authentication import KombitAccess
from q_serviceplatformen.functionality.access import get_kombit_access
from q_serviceplatformen.functionality.post_models import RecipientIdType
from q_serviceplatformen.sf1601_client import is_registered


def check_registration(
    *,
    recipient_id: str,
    recipient_id_type: RecipientIdType,
    service: Literal["digitalpost", "nemsms"] = "digitalpost",
    kombit_access: KombitAccess | None = None,
) -> bool:
    """
    Returnerer True eller False ved et gennemført opslag.

    Tekniske fejl fortsætter som exceptions og bliver aldrig til False.
    """
    normalized_id = normalize_recipient_id(
        recipient_id=recipient_id,
        recipient_id_type=recipient_id_type,
    )
    access = kombit_access or get_kombit_access()
    return is_registered(
        id_=normalized_id,
        service=service,
        kombit_access=access,
    )


def normalize_recipient_id(
    *,
    recipient_id: str,
    recipient_id_type: RecipientIdType,
) -> str:
    """Returnerer CPR/CVR med kun cifre efter validering."""
    if not isinstance(recipient_id, str):
        raise TypeError("recipient_id skal være tekst.")

    normalized_id = "".join(
        character for character in recipient_id if character.isdigit()
    )

    if recipient_id_type == "CPR":
        expected_length = 10
    elif recipient_id_type == "CVR":
        expected_length = 8
    else:
        raise ValueError("recipient_id_type skal være CPR eller CVR.")

    if len(normalized_id) != expected_length:
        raise ValueError(
            f"{recipient_id_type} skal indeholde {expected_length} cifre."
        )

    return normalized_id
