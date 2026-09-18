"""Den offentlige API til q-serviceplatformen."""

from q_serviceplatformen.functionality import (
    DigitalPostDocument,
    DigitalPostReceipt,
    DigitalPostSendResult,
    PhysicalPostSendResult,
    PostDocument,
    RegistrationResult,
    check_registration,
    preview_physical_post_xml,
    send_digital_post,
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
