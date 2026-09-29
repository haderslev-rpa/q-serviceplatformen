"""Enhedstest af kvitteringsparseren med den kendte PKO_PostStatus-struktur."""
import base64
import unittest

from q_serviceplatformen.functionality.post_receipt import (
    parse_post_receipt,
)


class PostReceiptTest(unittest.TestCase):
    def test_delivered_digital_post(self):
        payload = b"""<PKO_PostStatus xmlns="http://serviceplatformen.dk/xml/print/PKO_PostStatus/1/types"><TransmissionId>89f4af49-60cb-469c-b404-16f7b403e64c</TransmissionId><MessageUUID>a27235e7-8d31-4939-8ff3-1488a55a1b34</MessageUUID><KanalKode>Digital Post</KanalKode><TransaktionsDatoTid>2026-09-22T22:15:09.892Z</TransaktionsDatoTid><TransaktionsStatusKode>Afleveret Digital Post</TransaktionsStatusKode><CorrelationId>89f4af49-60cb-469c-b404-16f7b403e64c</CorrelationId><FejlDetaljer/></PKO_PostStatus>"""
        encoded = base64.b64encode(payload).decode("ascii")
        envelope = f"""<ns2:Haendelsesbesked xmlns="urn:oio:sagdok:3.0.0" xmlns:ns2="urn:oio:besked:kuvert:1.0"><ns2:BeskedId><UUIDIdentifikator>79c9152b-2637-4f94-879e-1051933a56ae</UUIDIdentifikator></ns2:BeskedId><ns2:Beskedkuvert><ns2:Leveranceinformation><ns2:Dannelsestidspunkt><TidsstempelDatoTid>2026-09-22T22:15:09.991Z</TidsstempelDatoTid></ns2:Dannelsestidspunkt><ns2:Leveranceruter><ns2:Leverancerute><ns2:LeveranceTidspunkt><TidsstempelDatoTid>2026-09-23T00:17:22.855+02:00</TidsstempelDatoTid></ns2:LeveranceTidspunkt><ns2:ErLeveretIHenholdTil><UUIDIdentifikator>5679513a-7be7-44fd-a0c2-494c3b422a22</UUIDIdentifikator></ns2:ErLeveretIHenholdTil></ns2:Leverancerute></ns2:Leveranceruter></ns2:Leveranceinformation></ns2:Beskedkuvert><ns2:Beskeddata><Base64 xmlns="urn:besked:kuvert:1.0">{encoded}</Base64></ns2:Beskeddata></ns2:Haendelsesbesked>""".encode()
        receipt = parse_post_receipt(envelope)
        self.assertEqual(receipt.status, "DELIVERED")
        self.assertTrue(receipt.is_final)
        self.assertTrue(receipt.is_success)
        self.assertEqual(receipt.channel, "DIGITAL_POST")
        self.assertEqual(receipt.memo_message_uuid, "a27235e7-8d31-4939-8ff3-1488a55a1b34")
        self.assertEqual(receipt.serviceplatform_transaction_id, "89f4af49-60cb-469c-b404-16f7b403e64c")
        self.assertEqual(receipt.broker_message_id, "79c9152b-2637-4f94-879e-1051933a56ae")


if __name__ == "__main__":
    unittest.main()
