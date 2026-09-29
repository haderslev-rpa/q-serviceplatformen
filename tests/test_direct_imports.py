"""Kontrollerer direkte imports med tomme __init__.py-filer."""
import unittest

from q_serviceplatformen.beskedfordeler_message_broker import MessageBroker
from q_serviceplatformen.functionality.post_models import PostDocument
from q_serviceplatformen.functionality.post_receipt import parse_post_receipt
from q_serviceplatformen.functionality.registration import check_registration
from q_serviceplatformen.functionality.send_digital_post import send_digital_post
from q_serviceplatformen.functionality.send_physical_post import send_physical_post


class DirectImportTest(unittest.TestCase):
    def test_direct_imports(self) -> None:
        objects = (
            MessageBroker,
            PostDocument,
            parse_post_receipt,
            check_registration,
            send_digital_post,
            send_physical_post,
        )
        self.assertTrue(all(objects))


if __name__ == "__main__":
    unittest.main()
