from __future__ import annotations

import logging
from dataclasses import dataclass

from .settings import settings

logger = logging.getLogger(__name__)


@dataclass
class EmailSendResult:
    preview_url: str | None = None


class EmailProvider:
    def send_verification_email(self, to: str, link: str) -> EmailSendResult:
        raise NotImplementedError

    def send_password_reset_email(self, to: str, link: str) -> EmailSendResult:
        raise NotImplementedError


class ConsoleEmailProvider(EmailProvider):
    def send_verification_email(self, to: str, link: str) -> EmailSendResult:
        logger.info('[EMAIL][VERIFY] to=%s link=%s', to, link)
        return EmailSendResult(preview_url=link if settings.dev_email_preview_enabled else None)

    def send_password_reset_email(self, to: str, link: str) -> EmailSendResult:
        logger.info('[EMAIL][RESET] to=%s link=%s', to, link)
        return EmailSendResult(preview_url=link if settings.dev_email_preview_enabled else None)


class EtherealEmailProvider(ConsoleEmailProvider):
    """
    Dev stub: in this project returns preview URL and logs message.
    You can switch to real SMTP by implementing transport here without changing API.
    """


def get_email_provider() -> EmailProvider:
    provider = (settings.EMAIL_PROVIDER or 'console').strip().lower()
    if provider == 'ethereal':
        return EtherealEmailProvider()
    return ConsoleEmailProvider()
