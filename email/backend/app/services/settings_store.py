"""Admin-editable runtime settings persisted in `system_settings` (falls back to config defaults).

Only keys listed in SETTINGS are accepted, and every one of them is read somewhere in the backend:
  llm_provider        -> analysis, smart reply and assistant (services/pipeline.py, smart_reply.py, rag_assistant.py)
  allow_registration  -> POST /auth/register
  default_reply_tone  -> smart reply when no tone is supplied
  reply_overdue_hours -> analytics "overdue replies" and reply-required notifications
"""
from typing import Any, Dict

from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.services import llm

TONES = ["Professional", "Friendly", "Short", "Detailed", "Apologetic", "Formal"]


class SettingError(ValueError):
    pass


def _bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "on"):
        return True
    if s in ("false", "0", "no", "off"):
        return False
    raise SettingError(f"Expected true/false, got {v!r}")


def _choice(options):
    def parse(v: Any) -> str:
        s = str(v).strip()
        for o in options:
            if o.lower() == s.lower():
                return o
        raise SettingError(f"Must be one of: {', '.join(options)}")
    return parse


def _int(lo: int, hi: int):
    def parse(v: Any) -> int:
        try:
            n = int(v)
        except (TypeError, ValueError):
            raise SettingError("Must be an integer")
        if not lo <= n <= hi:
            raise SettingError(f"Must be between {lo} and {hi}")
        return n
    return parse


SETTINGS: Dict[str, Dict[str, Any]] = {
    "llm_provider": {"parse": _choice(["auto", "gemini", "openai", "anthropic", "heuristic"]),
                     "default": lambda: settings.LLM_PROVIDER, "description": "Which LLM provider powers the AI features"},
    "allow_registration": {"parse": _bool, "default": lambda: settings.ALLOW_REGISTRATION,
                           "description": "Allow new users to self-register"},
    "default_reply_tone": {"parse": _choice(TONES), "default": lambda: "Professional",
                           "description": "Tone used for smart replies when none is chosen"},
    "reply_overdue_hours": {"parse": _int(1, 720), "default": lambda: settings.REPLY_OVERDUE_HOURS,
                            "description": "Hours before a reply-required email counts as overdue"},
}


def get_setting(db: Session, key: str) -> Any:
    spec = SETTINGS[key]
    row = db.get(models.SystemSetting, key)
    if row is not None:
        try:
            return spec["parse"](row.value)
        except SettingError:
            pass
    return spec["default"]()


def get_all_settings(db: Session) -> Dict[str, Dict[str, Any]]:
    stored = {r.key: r for r in db.query(models.SystemSetting).all()}
    out = {}
    for key, spec in SETTINGS.items():
        out[key] = {"value": get_setting(db, key), "default": spec["default"](), "description": spec["description"],
                    "is_overridden": key in stored,
                    "updated_at": stored[key].updated_at if key in stored else None}
    return out


def set_setting(db: Session, key: str, value: Any) -> Any:
    if key not in SETTINGS:
        raise SettingError(f"Unknown setting '{key}'. Valid keys: {', '.join(SETTINGS)}")
    parsed = SETTINGS[key]["parse"](value)
    row = db.get(models.SystemSetting, key)
    text = str(parsed).lower() if isinstance(parsed, bool) else str(parsed)
    if row is None:
        db.add(models.SystemSetting(key=key, value=text))
    else:
        row.value = text
    db.commit()
    return parsed


def reset_setting(db: Session, key: str) -> None:
    if key not in SETTINGS:
        raise SettingError(f"Unknown setting '{key}'")
    row = db.get(models.SystemSetting, key)
    if row is not None:
        db.delete(row)
        db.commit()


def llm_provider_override(db: Session):
    """Value to pass as `provider=` to the LLM layer ('auto' means: let config decide)."""
    value = get_setting(db, "llm_provider")
    return None if value == "auto" else value


def effective_provider(db: Session):
    return llm.resolve_provider(llm_provider_override(db))
