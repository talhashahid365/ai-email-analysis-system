"""Audit-log writer. Never raises: a failed audit write must not break the user's request."""
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app import models

log = logging.getLogger("app.audit")
_SENSITIVE = ("password", "token", "secret", "authorization", "api_key")


def _clean(details: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not details:
        return None
    out: Dict[str, Any] = {}
    for k, v in details.items():
        if any(s in str(k).lower() for s in _SENSITIVE):
            out[k] = "***"
        elif isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v if not isinstance(v, str) else v[:500]
        elif isinstance(v, (list, tuple)):
            out[k] = [x if isinstance(x, (int, float, bool)) else str(x)[:200] for x in list(v)[:50]]
        elif isinstance(v, dict):
            out[k] = _clean(v)
        else:
            out[k] = str(v)[:200]
    return out


def write_audit(db: Session, user_id: Optional[int], action: str, resource: str,
                details: Optional[Dict[str, Any]] = None, ip: Optional[str] = None, commit: bool = True) -> None:
    try:
        db.add(models.AuditLog(user_id=user_id, action=action, resource=resource[:200],
                               details=_clean(details), ip_address=ip))
        if commit:
            db.commit()
        else:
            db.flush()
    except Exception:  # pragma: no cover - defensive
        log.exception("audit write failed for action=%s", action)
        try:
            db.rollback()
        except Exception:
            pass
