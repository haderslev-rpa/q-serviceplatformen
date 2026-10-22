"""Builder og validering af indlejrede PDF-bilag til SF1601 Fjernprint."""
from __future__ import annotations

import base64
from collections.abc import Sequence

from q_serviceplatformen.functionality.post_models import PostDocument
from q_serviceplatformen.models.physical_mail import (
    Bilag,
    BilagNavn,
    BilagSamling,
    BilagSorteringsIndeksIdentifikator,
    FilformatNavn,
    VedhaeftningIndholdData,
)

MAX_PHYSICAL_POST_ATTACHMENTS = 100
MAX_PHYSICAL_POST_TOTAL_SIZE_BYTES = 7 * 1024 * 1024


def validate_physical_post_documents(
    document: PostDocument,
    attachments: Sequence[PostDocument] | None = None,
    *,
    max_total_size_bytes: int = MAX_PHYSICAL_POST_TOTAL_SIZE_BYTES,
) -> tuple[PostDocument, tuple[PostDocument, ...]]:
    """Valider hoveddokument og bilag og returner normaliserede dokumenter."""
    normalized_attachments = tuple(attachments or ())
    if not isinstance(document, PostDocument):
        raise TypeError("document skal være et PostDocument-objekt.")
    if not isinstance(max_total_size_bytes, int) or isinstance(max_total_size_bytes, bool):
        raise TypeError("max_total_size_bytes skal være et helt tal.")
    if max_total_size_bytes <= 0:
        raise ValueError("max_total_size_bytes skal være større end 0.")
    if len(normalized_attachments) > MAX_PHYSICAL_POST_ATTACHMENTS:
        raise ValueError(
            "Fysisk post understøtter højst "
            f"{MAX_PHYSICAL_POST_ATTACHMENTS} bilag."
        )
    _validate_pdf_document(document, "Hoveddokument")
    for index, attachment in enumerate(normalized_attachments, start=1):
        if not isinstance(attachment, PostDocument):
            raise TypeError(f"Bilag {index} skal være et PostDocument-objekt.")
        _validate_pdf_document(attachment, f"Bilag {index}")
    total_size = len(document.content) + sum(
        len(attachment.content) for attachment in normalized_attachments
    )
    if total_size > max_total_size_bytes:
        raise ValueError(
            f"Den fysiske forsendelse fylder {total_size} bytes. "
            f"Maksimum er {max_total_size_bytes} bytes."
        )
    return document, normalized_attachments


def build_physical_post_attachment_collection(
    attachments: Sequence[PostDocument] | None,
) -> BilagSamling | None:
    """Byg SF1601 BilagSamling med Base64-indlejrede PDF-bilag."""
    normalized_attachments = tuple(attachments or ())
    if not normalized_attachments:
        return None
    if len(normalized_attachments) > MAX_PHYSICAL_POST_ATTACHMENTS:
        raise ValueError(
            "Fysisk post understøtter højst "
            f"{MAX_PHYSICAL_POST_ATTACHMENTS} bilag."
        )
    physical_attachments: list[Bilag] = []
    for index, attachment in enumerate(normalized_attachments, start=1):
        if not isinstance(attachment, PostDocument):
            raise TypeError(f"Bilag {index} skal være et PostDocument-objekt.")
        _validate_pdf_document(attachment, f"Bilag {index}")
        visible_name = str(attachment.label or attachment.file_name).strip()
        physical_attachments.append(
            Bilag(
                bilag_navn=BilagNavn(value=visible_name),
                filformat_navn=FilformatNavn(value="pdf"),
                bilag_sorterings_indeks_identifikator=(
                    BilagSorteringsIndeksIdentifikator(value=index)
                ),
                vedhaeftning_indhold_data=VedhaeftningIndholdData(
                    value=base64.b64encode(attachment.content)
                ),
            )
        )
    return BilagSamling(bilag=physical_attachments)


def _validate_pdf_document(document: PostDocument, field_name: str) -> None:
    if not isinstance(document.content, bytes):
        raise TypeError(f"{field_name}: content skal være bytes.")
    if not document.content:
        raise ValueError(f"{field_name}: PDF-indholdet er tomt.")
    if not document.content.startswith(b"%PDF-"):
        raise ValueError(f"{field_name}: dokumentet er ikke en PDF.")
    file_name = str(document.file_name or "").strip()
    if not file_name.lower().endswith(".pdf"):
        raise ValueError(f"{field_name}: filnavnet skal ende på .pdf.")
    label = str(document.label or file_name).strip()
    if not label:
        raise ValueError(f"{field_name}: bilagsnavnet må ikke være tomt.")
