"""Bygger MeMo-beskeder til Digital Post."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from q_serviceplatformen.configuration import (
    DEFAULT_LANGUAGE,
    DEFAULT_LEGAL_NOTIFICATION,
    DEFAULT_MANDATORY,
    DEFAULT_MIME_TYPE,
    DEFAULT_POST_TYPE,
    SENDER_CVR,
    SENDER_LABEL,
)
from q_serviceplatformen.functionality.digital_post_models import (
    DigitalPostDocument,
)
from q_serviceplatformen.models.message import (
    AdditionalDocument,
    File,
    MainDocument,
    Message,
    MessageBody,
    MessageHeader,
    Recipient,
    Sender,
)


RecipientIdType = Literal["CPR", "CVR"]


def build_digital_post_message(
    *,
    recipient_id: str,
    recipient_id_type: RecipientIdType,
    subject: str,
    main_document: DigitalPostDocument,
    attachments: list[DigitalPostDocument] | None = None,
) -> Message:
    """
    Bygger en komplet MeMo-besked til Digital Post.

    Input:
        recipient_id:
            Modtagerens normaliserede CPR- eller CVR-nummer.

        recipient_id_type:
            CPR eller CVR.

        subject:
            Digital Post-beskedens emne.

        main_document:
            Forsendelsens hoveddokument.

        attachments:
            En liste med PDF-bilag. Listen kan udelades.

    Output:
        Et Message-objekt med:

        - Afsender fra q_serviceplatformen.configuration.
        - Modtager som CPR eller CVR.
        - Hoveddokument som MainDocument.
        - Bilag som AdditionalDocument.
        - Et nyt messageUUID.
        - Standardværdier til myndighedspost.

        Funktionen sender ikke beskeden til Serviceplatformen.
    """

    validated_recipient_id = _validate_recipient(
        recipient_id=recipient_id,
        recipient_id_type=recipient_id_type,
    )
    validated_subject = _require_text(
        subject,
        "subject",
    )
    validated_main_document = _validate_document(
        main_document,
        "main_document",
    )

    validated_attachments = _validate_attachments(
        attachments or [],
        main_document=validated_main_document,
    )

    main_memo_document = _build_main_document(
        validated_main_document
    )

    additional_memo_documents = tuple(
        _build_additional_document(document)
        for document in validated_attachments
    )

    return Message(
        messageHeader=MessageHeader(
            messageType="DIGITALPOST",
            messageUUID=str(uuid4()),
            label=validated_subject,
            mandatory=DEFAULT_MANDATORY,
            legalNotification=DEFAULT_LEGAL_NOTIFICATION,
            postType=DEFAULT_POST_TYPE,
            sender=Sender(
                senderID=SENDER_CVR,
                idType="CVR",
                label=SENDER_LABEL,
            ),
            recipient=Recipient(
                recipientID=validated_recipient_id,
                idType=recipient_id_type,
            ),
        ),
        messageBody=MessageBody(
            createdDateTime=datetime.now(timezone.utc),
            mainDocument=main_memo_document,
            additionalDocuments=(
                additional_memo_documents
                if additional_memo_documents
                else None
            ),
        ),
    )


def _build_main_document(
    document: DigitalPostDocument,
) -> MainDocument:
    """
    Bygger et MeMo-hoveddokument.

    Output:
        Et MainDocument med ét base64-kodet PDF-dokument.
    """

    return MainDocument(
        mainDocumentID=document.document_id,
        label=document.label or document.file_name,
        files=(
            _build_file(document),
        ),
    )


def _build_additional_document(
    document: DigitalPostDocument,
) -> AdditionalDocument:
    """
    Bygger ét MeMo-bilag.

    Output:
        Et AdditionalDocument med én base64-kodet PDF-fil.
    """

    return AdditionalDocument(
        additionalDocumentID=document.document_id,
        label=document.label or document.file_name,
        files=(
            _build_file(document),
        ),
    )


def _build_file(
    document: DigitalPostDocument,
) -> File:
    """
    Bygger et MeMo File-objekt.

    Output:
        Et File-objekt med PDF-indholdet kodet som base64-tekst.
    """

    encoded_content = base64.b64encode(
        document.content
    ).decode("ascii")

    return File(
        encodingFormat=DEFAULT_MIME_TYPE,
        filename=document.file_name,
        language=DEFAULT_LANGUAGE,
        content=encoded_content,
    )


def _validate_attachments(
    attachments: list[DigitalPostDocument],
    *,
    main_document: DigitalPostDocument,
) -> list[DigitalPostDocument]:
    """
    Validerer alle bilag før bygning af MeMo-beskeden.

    Output:
        Den validerede liste med bilag.

    Fejl:
        TypeError eller ValueError ved ugyldige eller dublerede
        dokumenter.
    """

    if not isinstance(attachments, list):
        raise TypeError(
            "attachments skal være en liste."
        )

    validated_attachments: list[DigitalPostDocument] = []

    document_ids = {
        main_document.document_id.casefold(),
    }
    file_names = {
        main_document.file_name.casefold(),
    }

    for index, attachment in enumerate(attachments):
        validated_attachment = _validate_document(
            attachment,
            f"attachments[{index}]",
        )

        normalized_document_id = (
            validated_attachment.document_id.casefold()
        )
        normalized_file_name = (
            validated_attachment.file_name.casefold()
        )

        if normalized_document_id in document_ids:
            raise ValueError(
                "Alle dokumenter skal have forskellige document_id."
            )

        if normalized_file_name in file_names:
            raise ValueError(
                "Alle dokumenter skal have forskellige filnavne."
            )

        document_ids.add(normalized_document_id)
        file_names.add(normalized_file_name)
        validated_attachments.append(validated_attachment)

    return validated_attachments


def _validate_document(
    document: DigitalPostDocument,
    field_name: str,
) -> DigitalPostDocument:
    """
    Validerer ét dokument til MeMo-beskeden.

    Output:
        Det validerede DigitalPostDocument.

    Fejl:
        TypeError eller ValueError, hvis dokumentet ikke er en
        ikke-tom PDF med filnavn og dokument-ID.
    """

    if not isinstance(document, DigitalPostDocument):
        raise TypeError(
            f"{field_name} skal være et DigitalPostDocument."
        )

    if not isinstance(document.content, bytes):
        raise TypeError(
            f"{field_name}.content skal være bytes."
        )

    if not document.content:
        raise ValueError(
            f"{field_name}.content må ikke være tom."
        )

    if not document.content.startswith(b"%PDF-"):
        raise ValueError(
            f"{field_name} er ikke en PDF."
        )

    file_name = _require_text(
        document.file_name,
        f"{field_name}.file_name",
    )

    if not file_name.lower().endswith(".pdf"):
        raise ValueError(
            f"{field_name}.file_name skal ende på .pdf."
        )

    _require_text(
        document.document_id,
        f"{field_name}.document_id",
    )

    return document


def _validate_recipient(
    *,
    recipient_id: str,
    recipient_id_type: RecipientIdType,
) -> str:
    """
    Validerer modtagerens CPR- eller CVR-nummer.

    Output:
        Modtagerens validerede identifikator uden mellemrum,
        bindestreger eller andre skilletegn.
    """

    if not isinstance(recipient_id, str):
        raise TypeError(
            "recipient_id skal være tekst."
        )

    normalized_id = "".join(
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
            "recipient_id_type skal være CPR eller CVR."
        )

    if len(normalized_id) != expected_length:
        raise ValueError(
            f"{recipient_id_type} skal indeholde "
            f"{expected_length} cifre."
        )

    return normalized_id


def _require_text(
    value: str,
    field_name: str,
) -> str:
    """
    Validerer et obligatorisk tekstfelt.

    Output:
        Teksten uden mellemrum før og efter.
    """

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} skal være tekst."
        )

    cleaned_value = value.strip()

    if not cleaned_value:
        raise ValueError(
            f"{field_name} må ikke være tom."
        )

    return cleaned_value