"""Outbound email abstraction.

No email provider has been chosen yet (see docs/ARCHITECTURE.md §11). Until one is configured,
messages are written to the API log in development so flows like password reset can be exercised
locally. In production the console sender refuses to log message bodies, because they contain
secrets such as reset links.
"""

import logging
from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings

logger = logging.getLogger("ipp.email")


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class ConsoleEmailSender:
    def send(self, message: EmailMessage) -> None:
        if get_settings().is_production:
            logger.error("No email provider configured; dropped email %r", message.subject)
            return
        logger.warning("DEV EMAIL to=%s subject=%r\n%s", message.to, message.subject, message.body)


_sender: EmailSender = ConsoleEmailSender()


def get_email_sender() -> EmailSender:
    return _sender
