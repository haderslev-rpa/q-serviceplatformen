"""Offentlige funktioner og modeller til brug fra andre pakker."""

from q_serviceplatformen.functionality.post_models import (
    DigitalPostDocument,
    DigitalPostReceipt,
    DigitalPostSendResult,
    PhysicalPostSendResult,
    PostDocument,
    RegistrationResult,
)
from q_serviceplatformen.functionality.registration import (
    check_registration,
)
from q_serviceplatformen.functionality.send_digital_post import (
    send_digital_post,
)
from q_serviceplatformen.functionality.send_physical_post import (
    preview_physical_post_xml,
    send_physical_post,
)

__all__ = [
    "DigitalPostDocument",
    "DigitalPostReceipt",
    "DigitalPostSendResult",
    "PhysicalPostSendResult",
    "PostDocument",
    "RegistrationResult",
    "check_registration",
    "preview_physical_post_xml",
    "send_digital_post",
    "send_physical_post",
]
