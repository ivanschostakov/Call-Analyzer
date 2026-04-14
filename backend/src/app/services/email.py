import asyncio
import logging
import smtplib

from email.message import EmailMessage
from email.utils import formataddr
from urllib.parse import urlencode

from config import (
    FRONTEND_BASE_URL,
    SMTP_FROM_EMAIL,
    SMTP_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_SSL,
    SMTP_USE_TLS,
    SMTP_USERNAME,
)
from src.app.observability import log_exception, log_info, start_timer

logger = logging.getLogger(__name__)


def _ensure_smtp_configured() -> None:
    if not SMTP_HOST or not SMTP_FROM_EMAIL: raise RuntimeError("SMTP is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL (or SMTP_USERNAME).")

def _deliver_email(message: EmailMessage) -> None:
    _ensure_smtp_configured()
    log_info(
        logger,
        "email.smtp.deliver.start",
        host=SMTP_HOST,
        port=SMTP_PORT,
        use_ssl=SMTP_USE_SSL,
        use_tls=SMTP_USE_TLS,
        recipient=message.get("To"),
        subject=message.get("Subject"),
    )

    if SMTP_USE_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as client:
            if SMTP_USERNAME and SMTP_PASSWORD: client.login(SMTP_USERNAME, SMTP_PASSWORD)
            client.send_message(message)
        return

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as client:
        if SMTP_USE_TLS: client.starttls()
        if SMTP_USERNAME and SMTP_PASSWORD: client.login(SMTP_USERNAME, SMTP_PASSWORD)
        client.send_message(message)


def _build_invitation_email(*, recipient_email: str, company_name: str, invited_by_name: str, login_url: str, register_url: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"Приглашение в компанию {company_name}"
    message["From"] = formataddr((SMTP_FROM_NAME, SMTP_FROM_EMAIL))
    message["To"] = recipient_email
    message.set_content(
        "\n".join(
            [
                f"Вас пригласили в компанию «{company_name}» в Call Analyzer.",
                "",
                f"Приглашение отправил: {invited_by_name}.",
                "",
                "Если у вас уже есть аккаунт, войдите по ссылке:",
                login_url,
                "",
                "Если аккаунта еще нет, зарегистрируйтесь по ссылке:",
                register_url,
                "",
                "После входа или регистрации приглашение применится автоматически.",
            ]
        )
    )
    return message


async def send_company_invitation_email(*, recipient_email: str, company_name: str, invited_by_name: str, token: str) -> None:
    timer = start_timer()
    invite_query = urlencode(
        {
            "inviteToken": token,
            "inviteEmail": recipient_email,
            "companyName": company_name,
        }
    )
    login_url = f"{FRONTEND_BASE_URL}/login?{invite_query}"
    register_url = f"{FRONTEND_BASE_URL}/register?{invite_query}"
    message = _build_invitation_email(
        recipient_email=recipient_email,
        company_name=company_name,
        invited_by_name=invited_by_name,
        login_url=login_url,
        register_url=register_url,
    )
    log_info(
        logger,
        "email.invitation.start",
        recipient_email=recipient_email,
        company_name=company_name,
        invited_by_name=invited_by_name,
        invitation_token=token,
    )
    try: await asyncio.to_thread(_deliver_email, message)
    except Exception:
        log_exception(logger, "email.invitation.failed", recipient_email=recipient_email, company_name=company_name)
        raise
    log_info(logger, "email.invitation.success", recipient_email=recipient_email, company_name=company_name, duration_ms=timer.elapsed_ms)
