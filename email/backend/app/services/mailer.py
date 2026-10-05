"""Outgoing system email (verification / password reset). Uses SMTP when configured, otherwise logs token for local dev."""
import logging
import smtplib
from email.message import EmailMessage

from app.config import settings
from app.services.mailnet import open_smtp

log = logging.getLogger("app.mailer")


def send_system_email(to: str, subject: str, body: str, sensitive: bool = False) -> bool:
    """Returns True if the message was handed to an SMTP server.

    sensitive=True (password reset links) means the body is NEVER printed or logged, so the link can only be
    obtained from the recipient's inbox. Non-sensitive mail is printed in dev when SMTP is not configured.
    """
    if not sensitive:
        print(f"\n[SYSTEM MAIL] To: {to} | Subject: {subject}\n{body}\n")
    log.info("System email generated for %s (subject=%r)", to, subject)

    if not settings.SMTP_HOST or not settings.SMTP_USER:
        log.warning("SMTP is not configured (set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env); "
                    "email %r to %s was NOT sent", subject, to)
        return False

    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.SMTP_FROM, to, subject
    msg.set_content(body)
    try:
        with open_smtp() as smtp:
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception:
        log.exception("failed to send email to %s", to)
        return False


def send_reply_email(to: str, subject: str, body: str, from_name: str = "", in_reply_to: str = None,
                     message_id: str = None) -> tuple:
    """E-mail an approved reply to the original sender. Returns (delivered, note).

    delivered=False with a note means nothing was sent (SMTP not configured / disabled / failed), so the caller can
    tell the admin honestly instead of claiming the message was transmitted.
    """
    if not settings.SEND_REPLIES_VIA_SMTP:
        return False, "Sending is disabled (SEND_REPLIES_VIA_SMTP=false); reply was only recorded."
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        return False, "SMTP is not configured in backend/.env; reply was recorded but NOT e-mailed."
    msg = EmailMessage()
    msg["From"] = f"{from_name} <{settings.SMTP_USER}>" if from_name else settings.SMTP_USER
    msg["To"], msg["Subject"] = to, subject
    if message_id:
        msg["Message-ID"] = message_id
    if in_reply_to:  # keeps the reply in the same conversation in Gmail / Outlook
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)
    try:
        with open_smtp() as smtp:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        return True, f"Reply e-mailed to {to}."
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP login rejected. For Gmail use an App Password, not your normal password."
    except Exception as exc:
        log.exception("failed to send reply to %s", to)
        return False, f"Could not send e-mail: {type(exc).__name__}"
