"""Structured JSON logging with sensitive data redaction and request-context injection.

The module owns the two ContextVars that carry the current request ID and user ID
into every log record produced anywhere in the application, eliminating the need to
thread these values through function arguments.
"""
import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

# ---------------------------------------------------------------------------
# Request-scoped context — set by RequestIDMiddleware on every incoming request
# ---------------------------------------------------------------------------
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')

# Fields that must never appear in plaintext in log output.
SENSITIVE_FIELDS = {
    'password',
    'hashed_password',
    'token',
    'access_token',
    'refresh_token',
    'secret',
    'secret_key',
    'authorization',
    'api_key',
    'private_key',
}


class RedactingFilter(logging.Filter):
    """Scrubs sensitive keys from structured log messages and injects request context.

    Operates on both dict-valued ``msg`` fields (structured logging calls) and on
    any extra key that matches a sensitive name to prevent accidental leakage.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Redact sensitive keys when the message body is a dict
        if hasattr(record, 'msg') and isinstance(record.msg, dict):
            for key in SENSITIVE_FIELDS:
                if key in record.msg:
                    record.msg[key] = '[REDACTED]'

        # Redact sensitive fields that were passed via extra={}
        for key in SENSITIVE_FIELDS:
            if hasattr(record, key):
                setattr(record, key, '[REDACTED]')

        # Inject current request / user IDs so every log line is traceable
        record.request_id = request_id_var.get('')
        record.user_id = user_id_var.get('')
        return True


def setup_logging(debug: bool = False) -> None:
    """Configure the root logger with a JSON formatter.

    Call **once** at application startup before the FastAPI app object is created.
    When *debug* is ``True`` the root level is set to DEBUG, enabling verbose
    SQLAlchemy and uvicorn output — do **not** use in production.
    """
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s %(user_id)s'
    )
    handler.setFormatter(formatter)
    handler.addFilter(RedactingFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    # Suppress per-request access log — RequestIDMiddleware emits a structured equivalent
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    # Quieten SQLAlchemy query noise in production
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


# Module-level logger for all MailNexa application code.
logger = logging.getLogger('mailnexa')
