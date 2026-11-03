import smtplib
import ssl
from email.message import EmailMessage
from email.policy import SMTP as SMTP_POLICY

from app.core.config import Settings
from app.schemas.meetings import validate_address
from app.services.llm.provider import ChatError


class MailFailure(Exception):
    def __init__(self, code: str, ambiguous: bool = False):
        self.code, self.ambiguous = code, ambiguous


def mail_config(settings: Settings, recipients: list[str]) -> None:
    if settings.smtp_mode == "disabled" or not settings.smtp_host:
        raise ChatError(
            "SMTP_NOT_CONFIGURED",
            (
                "Configure backend SMTP_MODE/HOST/FROM and DEMO_ALLOW"
                "ED_RECIPIENTS. Sending is disabled by default."
            ),
            503,
        )
    try:
        validate_address(settings.smtp_from)
        for address in recipients:
            validate_address(address)
    except ValueError as exc:
        raise ChatError(
            "EMAIL_INVALID_ADDRESS",
            "Choose explicit valid sender/recipient addresses.",
            422,
        ) from exc
    allowed = {
        v.strip().lower()
        for v in settings.demo_allowed_recipients.split(",")
        if v.strip()
    }
    if not recipients or not set(recipients).issubset(allowed):
        raise ChatError(
            "EMAIL_RECIPIENT_NOT_ALLOWED",
            (
                "Choose recipients from backend DEMO_ALLOWED_RECIPIEN"
                "TS; addresses are never inferred from names."
            ),
            422,
        )
    if settings.smtp_mode == "local":
        if settings.smtp_host not in (
            "localhost",
            "127.0.0.1",
            "::1",
            "mailpit",
        ) or any(
            not x.rsplit("@", 1)[-1].endswith((".test", ".invalid")) for x in recipients
        ):
            raise ChatError(
                "SMTP_LOCAL_ONLY",
                "Local mode requires loopback/Mailpit and .test/.invalid recipients.",
                422,
            )
    elif not settings.smtp_external_send_enabled or settings.smtp_security == "none":
        raise ChatError(
            "SMTP_EXTERNAL_DISABLED",
            (
                "External sending requires explicit owner configurati"
                "on, TLS and approval of this draft revision."
            ),
            503,
        )


class SMTPTransport:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send(
        self, recipients: list[str], subject: str, body: str, message_id: str
    ) -> None:
        s = self.settings
        mail_config(s, recipients)
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = (
            s.smtp_from,
            ", ".join(recipients),
            subject,
        )
        message["Message-ID"] = message_id
        message.set_content(body)
        connection: smtplib.SMTP | None = None
        data_started = False
        try:
            if s.smtp_security == "ssl":
                connection = smtplib.SMTP_SSL(
                    s.smtp_host,
                    s.smtp_port,
                    timeout=s.smtp_timeout_seconds,
                    context=ssl.create_default_context(),
                )
            else:
                connection = smtplib.SMTP(
                    s.smtp_host, s.smtp_port, timeout=s.smtp_timeout_seconds
                )
            connection.ehlo_or_helo_if_needed()
            if s.smtp_security == "starttls":
                connection.starttls(context=ssl.create_default_context())
                connection.ehlo()
            if s.smtp_username:
                connection.login(s.smtp_username, s.smtp_password.get_secret_value())
            # Preflight ALL recipients before DATA; never knowingly partially send.
            if connection.mail(s.smtp_from)[0] != 250:
                raise MailFailure("SMTP_SENDER_REJECTED")
            if any(
                connection.rcpt(address)[0] not in (250, 251) for address in recipients
            ):
                connection.rset()
                raise MailFailure("SMTP_RECIPIENT_REJECTED")
            data_started = True
            if connection.data(message.as_bytes(policy=SMTP_POLICY))[0] != 250:
                raise MailFailure("SMTP_DATA_REJECTED")
        except smtplib.SMTPDataError as exc:
            raise MailFailure("SMTP_DATA_REJECTED") from exc
        except (OSError, smtplib.SMTPException) as exc:
            raise MailFailure(
                "SMTP_DELIVERY_UNCERTAIN" if data_started else "SMTP_CONNECTION_FAILED",
                data_started,
            ) from exc
        finally:
            if connection:
                # QUIT failures cannot turn an accepted DATA into a resend.
                connection.close()
