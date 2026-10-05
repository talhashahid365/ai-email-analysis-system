"""Network helpers for Gmail IMAP / SMTP.

Some PCs, routers and antivirus programs break the TLS handshake that newer OpenSSL builds send (the TCP connection
opens, then the handshake hangs and times out). In MAIL_TLS_MODE=auto the first attempt uses normal settings and, if
the network refuses it, a second attempt is made limited to TLS 1.2. `LAST_TLS` records what worked.
"""
import imaplib
import smtplib
import ssl
from typing import List

from app.config import settings

LAST_TLS = ""


def _context(tls12_only: bool) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if tls12_only:
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def _modes() -> List[bool]:
    mode = (settings.MAIL_TLS_MODE or "auto").strip().lower()
    if mode == "tls12":
        return [True]
    if mode == "default":
        return [False]
    return [False, True]


def _label(tls12_only: bool) -> str:
    return "TLS 1.2 only" if tls12_only else "default TLS"


def connect_imap() -> imaplib.IMAP4_SSL:
    global LAST_TLS
    last: Exception = OSError("no connection attempt was made")
    for tls12 in _modes():
        try:
            conn = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT, ssl_context=_context(tls12),
                                     timeout=settings.MAIL_NET_TIMEOUT_SECONDS)
            LAST_TLS = _label(tls12)
            return conn
        except (OSError, ssl.SSLError) as exc:
            last = exc
    raise last


def open_smtp() -> smtplib.SMTP:
    """Connected SMTP session with TLS already negotiated (port 465 = implicit TLS, anything else = STARTTLS).
    The caller still has to call .login() and close it (it works as a context manager)."""
    global LAST_TLS
    last: Exception = OSError("no connection attempt was made")
    for tls12 in _modes():
        smtp = None
        try:
            if settings.SMTP_PORT == 465:
                smtp = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=_context(tls12),
                                        timeout=settings.MAIL_NET_TIMEOUT_SECONDS)
            else:
                smtp = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.MAIL_NET_TIMEOUT_SECONDS)
                smtp.ehlo()
                smtp.starttls(context=_context(tls12))
                smtp.ehlo()
            LAST_TLS = _label(tls12)
            return smtp
        except (OSError, ssl.SSLError, smtplib.SMTPException) as exc:
            last = exc
            if smtp is not None:
                try:
                    smtp.close()
                except Exception:
                    pass
    raise last
