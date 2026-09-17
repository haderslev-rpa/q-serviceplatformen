"""Tests of MeMo XML functionality."""

import base64
import unittest
from datetime import datetime
from xml.etree import ElementTree

from q_serviceplatformen.configuration import SENDER_CVR, SENDER_LABEL
from q_serviceplatformen.functionality.digital_post_builder import (
    build_digital_post_message,
)
from q_serviceplatformen.functionality.digital_post_models import DigitalPostDocument
from q_serviceplatformen.models import message, xml_util
from q_serviceplatformen.models.message import (
    File,
    MainDocument,
    Message,
    MessageBody,
    MessageHeader,
    Recipient,
    Sender,
)
from tests.xml_compare import xml_compare


# We don't care about duplicate code in tests.
# pylint: disable=R0801


class MessageXMLTest(unittest.TestCase):
    """Test converting Message objects to XML."""

    def test_nemsms(self):
        """
        Tester oprettelse og XML-konvertering af en NemSMS.

        Output:
            Ingen returværdi. Testen består, når den genererede XML
            svarer til det gemte eksempel.
        """

        memo_message = message.create_nemsms(
            message_label="Label Text",
            message_text="Message Text",
            sender=Sender(
                label="Sender Label",
                senderID="Sender ID",
                idType="CVR",
            ),
            recipient=Recipient(
                label="Recipient Label",
                recipientID="Recipient ID",
                idType="CPR",
            ),
        )

        memo_message.messageHeader.messageUUID = (
            "fcdcf318-59b6-427c-9879-4f0af833d593"
        )

        actual_xml = xml_util.dataclass_to_xml(memo_message)
        expected_xml = ElementTree.parse(
            "tests/message_xml/MeMo_NemSMS.xml"
        ).getroot()

        xml_compare(actual_xml, expected_xml)

    def test_digital_post_with_attached_files(self):
        """
        Tester den eksisterende hjælpefunktion med to filer.

        Output:
            Ingen returværdi. Testen består, når den genererede XML
            svarer til det gemte eksempel med vedhæftede filer.
        """

        memo_message = message.create_digital_post_with_main_document(
            label="Label Text",
            sender=Sender(
                label="Sender Label",
                senderID="Sender ID",
                idType="CVR",
            ),
            recipient=Recipient(
                recipientID="Recipient ID",
                idType="CPR",
            ),
            files=(
                File(
                    encodingFormat="text/plain",
                    filename="File1.txt",
                    language="da",
                    content=base64.b64encode(
                        b"File content 1"
                    ).decode(),
                ),
                File(
                    encodingFormat="text/plain",
                    filename="File2.txt",
                    language="da",
                    content=base64.b64encode(
                        b"File content 2"
                    ).decode(),
                ),
            ),
        )

        memo_message.messageHeader.messageUUID = (
            "78212f5c-6d79-4012-8ed1-e2420243bd17"
        )

        if memo_message.messageBody is None:
            self.fail("Hjælpefunktionen oprettede ikke et MessageBody.")

        memo_message.messageBody.createdDateTime = datetime(
            2000,
            1,
            1,
            0,
            0,
            0,
        )

        actual_xml = xml_util.dataclass_to_xml(memo_message)
        expected_xml = ElementTree.parse(
            "tests/message_xml/MeMo_with_attachment.xml"
        ).getroot()

        xml_compare(actual_xml, expected_xml)

    def test_digital_post_builder(self):
        """
        Tester Haderslevs builder med hoveddokument og ét PDF-bilag.

        Output:
            Ingen returværdi. Testen består, når builderen opretter
            korrekt afsender, modtager, dokumenter og XML.
        """

        main_pdf_content = b"%PDF-1.4\nHoveddokument"
        attachment_pdf_content = b"%PDF-1.4\nBilag"

        main_document = DigitalPostDocument(
            content=main_pdf_content,
            file_name="Hovedbrev.pdf",
            document_id="hoveddokument-1",
            label="Hovedbrev",
        )
        attachment = DigitalPostDocument(
            content=attachment_pdf_content,
            file_name="Bilag.pdf",
            document_id="bilag-1",
            label="Bilag",
        )

        memo_message = build_digital_post_message(
            recipient_id="010190-1234",
            recipient_id_type="CPR",
            subject="Test af Digital Post-builder",
            main_document=main_document,
            attachments=[attachment],
        )

        self.assertEqual(
            memo_message.messageHeader.messageType,
            "DIGITALPOST",
        )
        self.assertEqual(
            memo_message.messageHeader.label,
            "Test af Digital Post-builder",
        )
        self.assertEqual(
            memo_message.messageHeader.sender.senderID,
            SENDER_CVR,
        )
        self.assertEqual(
            memo_message.messageHeader.sender.label,
            SENDER_LABEL,
        )
        self.assertEqual(
            memo_message.messageHeader.recipient.recipientID,
            "0101901234",
        )
        self.assertEqual(
            memo_message.messageHeader.recipient.idType,
            "CPR",
        )

        message_body = memo_message.messageBody
        if message_body is None:
            self.fail("Builderen oprettede ikke et MessageBody.")

        self.assertEqual(
            message_body.mainDocument.mainDocumentID,
            "hoveddokument-1",
        )
        self.assertEqual(
            message_body.mainDocument.files[0].filename,
            "Hovedbrev.pdf",
        )
        self.assertEqual(
            message_body.mainDocument.files[0].encodingFormat,
            "application/pdf",
        )
        self.assertEqual(
            message_body.mainDocument.files[0].content,
            base64.b64encode(main_pdf_content).decode("ascii"),
        )

        additional_documents = message_body.additionalDocuments
        if additional_documents is None:
            self.fail("Builderen oprettede ikke bilag.")

        self.assertEqual(len(additional_documents), 1)

        additional_document = additional_documents[0]
        self.assertEqual(
            additional_document.additionalDocumentID,
            "bilag-1",
        )
        self.assertEqual(
            additional_document.files[0].filename,
            "Bilag.pdf",
        )
        self.assertEqual(
            additional_document.files[0].content,
            base64.b64encode(
                attachment_pdf_content
            ).decode("ascii"),
        )

        xml_content = xml_util.dataclass_to_xml_string(memo_message)
        ElementTree.fromstring(xml_content)

        self.assertIn("Test af Digital Post-builder", xml_content)
        self.assertIn("Hovedbrev.pdf", xml_content)
        self.assertIn("Bilag.pdf", xml_content)

    def test_minimum_example(self):
        """
        Tester konvertering mod det minimale MeMo-eksempel.

        Output:
            Ingen returværdi. Testen består, når den genererede XML
            svarer til den gemte minimumsfil.
        """

        memo_message = Message(
            messageHeader=MessageHeader(
                messageType="DIGITALPOST",
                messageUUID=(
                    "8C2EA15D-61FB-4BA9-9366-42F8B194C114"
                ),
                label="Pladsanvisning",
                sender=Sender(
                    senderID="12345678",
                    idType="CVR",
                    label="Kommunen",
                ),
                recipient=Recipient(
                    recipientID="2211771212",
                    idType="CPR",
                ),
            ),
            messageBody=MessageBody(
                createdDateTime=datetime(2024, 5, 3, 12, 0, 0),
                mainDocument=MainDocument(
                    files=(
                        File(
                            encodingFormat="application/pdf",
                            filename="Pladsanvisning.pdf",
                            language="da",
                            content="VGhpcyBpcyBhIHRlc3Q=",
                        ),
                    ),
                ),
            ),
        )

        actual_xml = xml_util.dataclass_to_xml(memo_message)
        expected_xml = ElementTree.parse(
            "tests/message_xml/MeMo_Minimum_Example.xml"
        ).getroot()

        xml_compare(actual_xml, expected_xml)

    def test_full_example_file_is_valid_xml(self):
        """
        Kontrollerer at det gemte fulde MeMo-eksempel er gyldig XML.

        Output:
            Ingen returværdi. Testen består, når XML-filen kan læses,
            og rodelementet er et MeMo Message-element.
        """

        root = ElementTree.parse(
            "tests/message_xml/MeMo_Full_Example.xml"
        ).getroot()

        self.assertTrue(root.tag.endswith("Message"))


if __name__ == "__main__":
    unittest.main()
