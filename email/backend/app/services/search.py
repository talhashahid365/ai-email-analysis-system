"""Email search & filtering.

Three entry points share one implementation:

* `EmailFilters` + `apply_filters` – flat filters used by GET /emails, GET /search/emails and the AI assistant.
* `compile_structured` – a JSON condition tree (AND / OR groups) used by POST /search/structured.
* `resolve_date_range` – presets such as ``last_30_days`` -> (start, end).

Everything is user-scoped: the caller always passes `user_id`, and outbound (own) messages are excluded unless asked for.
"""
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, not_, or_
from sqlalchemy.orm import Session, selectinload

from app import models
from app.timeutil import to_naive_utc, utcnow

Email, AIAnalysis, Extracted = models.Email, models.AIAnalysis, models.ExtractedInformation

PRIORITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
DATE_PRESETS = ("today", "yesterday", "this_week", "this_month", "last_month", "this_year",
                "last_7_days", "last_30_days", "last_90_days")
SORT_FIELDS = ("received_at", "priority", "sender", "subject")


class SearchError(ValueError):
    """Invalid filter / structured query supplied by the caller (maps to HTTP 422)."""


# ------------------------------------------------------------------ dates
def _start_of_day(d: date) -> datetime:
    return datetime(d.year, d.month, d.day)


def resolve_date_range(preset: Optional[str] = None, days: Optional[int] = None, now: Optional[datetime] = None
                       ) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Return (start_inclusive, end_exclusive) as naive UTC datetimes. Rolling windows end 'now'."""
    now = now or utcnow()
    today = _start_of_day(now.date())
    if days is not None:
        if days < 0 or days > 3650:
            raise SearchError("days must be between 0 and 3650")
        return now - timedelta(days=days), now + timedelta(seconds=1)
    if not preset:
        return None, None
    p = preset.strip().lower().replace("-", "_").replace(" ", "_")
    m = re.fullmatch(r"(?:last|past)_(\d{1,4})_(day|week|month)s?", p)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        return now - timedelta(days=n * {"day": 1, "week": 7, "month": 30}[unit]), now + timedelta(seconds=1)
    if p == "today":
        return today, today + timedelta(days=1)
    if p == "yesterday":
        return today - timedelta(days=1), today
    if p == "this_week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=7)
    if p == "this_month":
        start = today.replace(day=1)
        nxt = (start + timedelta(days=32)).replace(day=1)
        return start, nxt
    if p == "last_month":
        this_start = today.replace(day=1)
        prev_start = (this_start - timedelta(days=1)).replace(day=1)
        return prev_start, this_start
    if p == "this_year":
        return datetime(today.year, 1, 1), datetime(today.year + 1, 1, 1)
    raise SearchError(f"Unknown date preset '{preset}'. Use one of: {', '.join(DATE_PRESETS)} or last_<N>_days")


def parse_datetime(value: Any, end_of_day: bool = False) -> datetime:
    """Accepts datetime / date / ISO strings. A bare date with end_of_day=True means 'up to and including that day'."""
    if isinstance(value, datetime):
        return to_naive_utc(value)
    if isinstance(value, date):
        d = _start_of_day(value)
        return d + timedelta(days=1) if end_of_day else d
    if not isinstance(value, str) or not value.strip():
        raise SearchError(f"Invalid date value: {value!r}")
    text = value.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            d = _start_of_day(date.fromisoformat(text))
            return d + timedelta(days=1) if end_of_day else d
        return to_naive_utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError as exc:
        raise SearchError(f"Invalid date value: {value!r}") from exc


# ------------------------------------------------------------------ flat filters
@dataclass
class EmailFilters:
    q: Optional[str] = None                 # free text: subject, body, sender, AI summary, extracted fields
    sender: Optional[str] = None            # sender name or address (substring)
    subject: Optional[str] = None
    body: Optional[str] = None
    sentiments: List[str] = field(default_factory=list)
    priorities: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    intent: Optional[str] = None            # substring
    action_required: Optional[bool] = None
    reply_required: Optional[bool] = None
    reply_status: List[str] = field(default_factory=list)  # pending | replied | dismissed | not_required
    is_read: Optional[bool] = None
    is_starred: Optional[bool] = None
    is_archived: Optional[bool] = False     # None = both
    thread_id: Optional[int] = None
    processing_status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None      # exclusive upper bound
    include_outbound: bool = False
    sort_by: str = "received_at"
    sort_dir: str = "desc"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k in ("date_from", "date_to"):
            d[k] = d[k].isoformat() if d[k] else None
        return {k: v for k, v in d.items() if v not in (None, [], "")}

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "EmailFilters":
        f = cls()
        for k, v in (data or {}).items():
            if not hasattr(f, k) or v in (None, "", []):
                continue
            if k in ("date_from", "date_to"):
                v = parse_datetime(v)
            setattr(f, k, v)
        return f

    def has_structured(self) -> bool:
        """True when any filter beyond free-text is set (used by the assistant to decide filter vs. rank)."""
        return any([self.sender, self.subject, self.body, self.sentiments, self.priorities, self.categories,
                    self.intent, self.action_required is not None, self.reply_required is not None, self.reply_status,
                    self.is_read is not None, self.is_starred is not None, self.date_from, self.date_to,
                    self.thread_id])

    def describe(self) -> str:
        parts: List[str] = []
        if self.priorities:
            parts.append("priority " + "/".join(p.title() for p in self.priorities))
        if self.sentiments:
            parts.append("sentiment " + "/".join(self.sentiments))
        if self.categories:
            parts.append("category " + "/".join(self.categories))
        if self.intent:
            parts.append(f"intent containing '{self.intent}'")
        if self.action_required is not None:
            parts.append("action required" if self.action_required else "no action required")
        if self.reply_required is not None:
            parts.append("reply required" if self.reply_required else "no reply required")
        if self.reply_status:
            parts.append("reply status " + "/".join(self.reply_status))
        if self.is_read is not None:
            parts.append("read" if self.is_read else "unread")
        if self.is_starred:
            parts.append("starred")
        if self.sender:
            parts.append(f"from '{self.sender}'")
        if self.subject:
            parts.append(f"subject containing '{self.subject}'")
        if self.body:
            parts.append(f"body containing '{self.body}'")
        if self.q:
            parts.append(f"matching '{self.q}'")
        if self.date_from or self.date_to:
            a = self.date_from.strftime("%Y-%m-%d") if self.date_from else "the beginning"
            b = (self.date_to - timedelta(seconds=1)).strftime("%Y-%m-%d") if self.date_to else "now"
            parts.append(f"received {a} → {b}")
        return ", ".join(parts) if parts else "all emails"


def _esc(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _like(col, term: str):
    return col.ilike(f"%{_esc(term.strip())}%", escape="\\")


def _norm_list(values: Optional[List[str]], transform) -> List[str]:
    out = []
    for v in values or []:
        for part in str(v).split(","):
            part = part.strip()
            if part:
                out.append(transform(part))
    return out


def normalize_filters(f: EmailFilters) -> EmailFilters:
    f.priorities = _norm_list(f.priorities, str.upper)
    bad = [p for p in f.priorities if p not in PRIORITY_ORDER]
    if bad:
        raise SearchError(f"Invalid priority {bad}. Use LOW, MEDIUM, HIGH or CRITICAL")
    f.sentiments = _norm_list(f.sentiments, str.title)
    f.categories = _norm_list(f.categories, str)
    f.reply_status = _norm_list(f.reply_status, str.lower)
    if f.sort_by not in SORT_FIELDS:
        raise SearchError(f"sort_by must be one of {', '.join(SORT_FIELDS)}")
    if f.sort_dir not in ("asc", "desc"):
        raise SearchError("sort_dir must be 'asc' or 'desc'")
    if f.date_from and f.date_to and f.date_from >= f.date_to:
        raise SearchError("date_from must be before date_to")
    return f


def priority_rank():
    return case(*[(AIAnalysis.priority == k, v) for k, v in PRIORITY_ORDER.items()], else_=0)


def apply_filters(query, f: EmailFilters):
    """`query` must be `db.query(Email)` already outer-joined to AIAnalysis and ExtractedInformation (see `base_query`)."""
    f = normalize_filters(f)
    if not f.include_outbound:
        query = query.filter(Email.is_outbound == False)  # noqa: E712
    if f.is_archived is not None:
        query = query.filter(Email.is_archived == f.is_archived)
    if f.is_read is not None:
        query = query.filter(Email.is_read == f.is_read)
    if f.is_starred is not None:
        query = query.filter(Email.is_starred == f.is_starred)
    if f.thread_id is not None:
        query = query.filter(Email.thread_id == f.thread_id)
    if f.processing_status:
        query = query.filter(Email.processing_status == f.processing_status)
    if f.q:
        query = query.filter(or_(_like(Email.subject, f.q), _like(Email.body_plain, f.q), _like(Email.sender_name, f.q),
                                 _like(Email.sender_email, f.q), _like(AIAnalysis.short_summary, f.q),
                                 _like(Extracted.customer_name, f.q), _like(Extracted.company, f.q),
                                 _like(Extracted.order_number, f.q), _like(Extracted.invoice_number, f.q),
                                 _like(Extracted.product, f.q)))
    if f.sender:
        query = query.filter(or_(_like(Email.sender_name, f.sender), _like(Email.sender_email, f.sender)))
    if f.subject:
        query = query.filter(_like(Email.subject, f.subject))
    if f.body:
        query = query.filter(_like(Email.body_plain, f.body))
    if f.sentiments:
        query = query.filter(AIAnalysis.sentiment.in_(f.sentiments))
    if f.priorities:
        query = query.filter(AIAnalysis.priority.in_(f.priorities))
    if f.categories:
        query = query.filter(func.lower(AIAnalysis.category).in_([c.lower() for c in f.categories]))
    if f.intent:
        query = query.filter(_like(AIAnalysis.intent, f.intent))
    if f.action_required is not None:
        query = query.filter(AIAnalysis.action_required == f.action_required)
    if f.reply_required is not None:
        query = query.filter(AIAnalysis.reply_required == f.reply_required)
    if f.reply_status:
        query = query.filter(Email.reply_status.in_(f.reply_status))
    if f.date_from:
        query = query.filter(Email.received_at >= f.date_from)
    if f.date_to:
        query = query.filter(Email.received_at < f.date_to)
    return query


def base_query(db: Session, user_id: int):
    return (db.query(Email).outerjoin(AIAnalysis, AIAnalysis.email_id == Email.id)
            .outerjoin(Extracted, Extracted.email_id == Email.id)  # one row per email (unique email_id)
            .options(selectinload(Email.ai_analysis)).filter(Email.user_id == user_id))


def apply_sort(query, f: EmailFilters):
    direction = (lambda c: c.asc()) if f.sort_dir == "asc" else (lambda c: c.desc())
    if f.sort_by == "priority":
        return query.order_by(direction(priority_rank()), Email.received_at.desc(), Email.id.desc())
    col = {"received_at": Email.received_at, "sender": Email.sender_name, "subject": Email.subject}[f.sort_by]
    return query.order_by(direction(col), Email.id.desc())


def run_search(db: Session, user_id: int, f: EmailFilters, limit: int = 50, offset: int = 0) -> Tuple[List[models.Email], int]:
    q = apply_filters(base_query(db, user_id), f)
    total = q.count()
    rows = apply_sort(q, f).offset(max(offset, 0)).limit(max(1, limit)).all()
    return rows, total


# ------------------------------------------------------------------ list item projection
def preview(text: str, n: int = 140) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def list_item(e: models.Email) -> Dict[str, Any]:
    a = e.ai_analysis
    return {
        "id": e.id, "thread_id": e.thread_id, "sender_name": e.sender_name, "sender_email": e.sender_email,
        "subject": e.subject, "body_preview": preview(e.body_plain), "received_at": e.received_at,
        "is_read": bool(e.is_read), "is_starred": bool(e.is_starred), "is_archived": bool(e.is_archived),
        "processing_status": e.processing_status, "reply_status": e.reply_status or "not_required",
        "category": a.category if a else "Unprocessed", "intent": a.intent if a else None,
        "priority": a.priority if a else "MEDIUM", "sentiment": a.sentiment if a else "Neutral",
        "short_summary": a.short_summary if a else None,
        "reply_required": bool(a.reply_required) if a else False,
        "action_required": bool(a.action_required) if a else False,
    }


# ------------------------------------------------------------------ structured search
MAX_CONDITIONS, MAX_DEPTH = 40, 4

TEXT_FIELDS = {
    "sender": [Email.sender_name, Email.sender_email], "sender_email": [Email.sender_email],
    "sender_name": [Email.sender_name], "subject": [Email.subject], "body": [Email.body_plain],
    "summary": [AIAnalysis.short_summary], "intent": [AIAnalysis.intent], "category": [AIAnalysis.category],
    "priority": [AIAnalysis.priority], "sentiment": [AIAnalysis.sentiment], "reply_status": [Email.reply_status],
    "processing_status": [Email.processing_status],
}
BOOL_FIELDS = {"action_required": AIAnalysis.action_required, "reply_required": AIAnalysis.reply_required,
               "is_read": Email.is_read, "is_starred": Email.is_starred, "is_archived": Email.is_archived}
DATE_FIELDS = {"date": Email.received_at, "received_at": Email.received_at}
ALL_FIELDS = sorted(set(TEXT_FIELDS) | set(BOOL_FIELDS) | set(DATE_FIELDS))
TEXT_OPS = {"eq", "ne", "in", "not_in", "contains", "not_contains", "starts_with", "is_null"}
DATE_OPS = {"eq", "within", "gt", "gte", "lt", "lte", "between", "is_null"}


def _norm_value(field_name: str, value: Any) -> Any:
    if not isinstance(value, str):
        return value
    v = value.strip()
    if field_name == "priority":
        return v.upper()
    if field_name == "sentiment":
        return v.title()
    return v


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "yes", "1"):
        return True
    if isinstance(value, str) and value.strip().lower() in ("false", "no", "0"):
        return False
    raise SearchError(f"Expected a boolean, got {value!r}")


def _compile_condition(c: Dict[str, Any], now: datetime):
    name = str(c.get("field", "")).strip().lower()
    op = str(c.get("op", "eq")).strip().lower()
    value = c.get("value")
    if name in BOOL_FIELDS:
        col = BOOL_FIELDS[name]
        if op == "is_null":
            return col.is_(None) if _bool(value if value is not None else True) else col.isnot(None)
        if op not in ("eq", "ne"):
            raise SearchError(f"Operator '{op}' is not valid for boolean field '{name}'")
        expr = col == _bool(value)
        return expr if op == "eq" else not_(expr)
    if name in DATE_FIELDS:
        col = DATE_FIELDS[name]
        if op not in DATE_OPS:
            raise SearchError(f"Operator '{op}' is not valid for date field '{name}'")
        if op == "is_null":
            return col.is_(None) if _bool(value if value is not None else True) else col.isnot(None)
        if op == "between":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise SearchError("'between' needs a [start, end] list")
            return and_(col >= parse_datetime(value[0]), col < parse_datetime(value[1], end_of_day=True))
        if op in ("eq", "within") and isinstance(value, str) and (value.strip().lower().replace("-", "_").replace(" ", "_") in DATE_PRESETS
                                                                  or re.fullmatch(r"(?:last|past)[ _-]\d+[ _-](?:day|week|month)s?", value.strip().lower())):
            start, end = resolve_date_range(value, now=now)
            return and_(col >= start, col < end)
        if op == "within":
            raise SearchError(f"Unknown date preset {value!r}")
        if op == "eq":
            return and_(col >= parse_datetime(value), col < parse_datetime(value, end_of_day=True))
        if op == "gt":
            return col >= parse_datetime(value, end_of_day=True) if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()) else col > parse_datetime(value)
        if op == "gte":
            return col >= parse_datetime(value)
        if op == "lt":
            return col < parse_datetime(value)
        return col < parse_datetime(value, end_of_day=True)  # lte
    if name in TEXT_FIELDS:
        cols = TEXT_FIELDS[name]
        if op not in TEXT_OPS:
            raise SearchError(f"Operator '{op}' is not valid for field '{name}'")
        if op == "is_null":
            expr = and_(*[col.is_(None) for col in cols])
            return expr if _bool(value if value is not None else True) else not_(expr)
        if op in ("in", "not_in"):
            if not isinstance(value, (list, tuple)) or not value:
                raise SearchError(f"'{op}' needs a non-empty list")
            vals = [str(_norm_value(name, v)).lower() for v in value]
            expr = or_(*[func.lower(col).in_(vals) for col in cols])
            return expr if op == "in" else not_(expr)
        if value is None or str(value).strip() == "":
            raise SearchError(f"Field '{name}' needs a value")
        v = str(_norm_value(name, value))
        if op in ("eq", "ne"):
            expr = or_(*[func.lower(col) == v.lower() for col in cols])
            return expr if op == "eq" else not_(expr)
        if op in ("contains", "not_contains"):
            expr = or_(*[_like(col, v) for col in cols])
            return expr if op == "contains" else not_(expr)
        return or_(*[col.ilike(f"{_esc(v)}%", escape="\\") for col in cols])  # starts_with
    raise SearchError(f"Unknown field '{c.get('field')}'. Valid fields: {', '.join(ALL_FIELDS)}")


def compile_structured(node: Dict[str, Any], now: Optional[datetime] = None, _depth: int = 0, _count: Optional[List[int]] = None):
    """Compile {"match": "all"|"any", "conditions": [...]} (nestable) into a SQLAlchemy boolean expression."""
    now = now or utcnow()
    count = _count if _count is not None else [0]
    if _depth > MAX_DEPTH:
        raise SearchError(f"Conditions may be nested at most {MAX_DEPTH} levels deep")
    if not isinstance(node, dict):
        raise SearchError("Each condition must be an object")
    if "conditions" in node or "match" in node:
        match = str(node.get("match", "all")).lower()
        if match not in ("all", "any"):
            raise SearchError("'match' must be 'all' or 'any'")
        items = node.get("conditions") or []
        if not isinstance(items, list) or not items:
            raise SearchError("A group needs at least one condition")
        parts = [compile_structured(i, now, _depth + 1, count) for i in items]
        return and_(*parts) if match == "all" else or_(*parts)
    count[0] += 1
    if count[0] > MAX_CONDITIONS:
        raise SearchError(f"At most {MAX_CONDITIONS} conditions are allowed")
    return _compile_condition(node, now)


def run_structured(db: Session, user_id: int, tree: Dict[str, Any], limit: int = 50, offset: int = 0,
                   sort_by: str = "received_at", sort_dir: str = "desc", include_archived: bool = True,
                   now: Optional[datetime] = None) -> Tuple[List[models.Email], int]:
    f = EmailFilters(is_archived=None if include_archived else False, sort_by=sort_by, sort_dir=sort_dir)
    normalize_filters(f)
    q = base_query(db, user_id).filter(Email.is_outbound == False)  # noqa: E712
    if not include_archived:
        q = q.filter(Email.is_archived == False)  # noqa: E712
    q = q.filter(compile_structured(tree, now))
    total = q.count()
    rows = apply_sort(q, f).offset(max(offset, 0)).limit(max(1, limit)).all()
    return rows, total
