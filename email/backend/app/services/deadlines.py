"""Natural-language date & deadline detection -> structured ISO dates.

Pure Python (no DB / network) so it can be unit-tested and reused by the heuristic engine,
the LLM post-processor and the assistant query parser.

Conventions
-----------
* A bare weekday ("Friday") means the next occurrence strictly after the reference date.
* "this Friday" may be today; "next Monday" is the Monday of the following calendar week.
* Numeric dates are day-first (25/09/2026). ISO (2026-09-25) and month names are unambiguous.
* Dates written in the past tense ("I received it on Monday") resolve to the previous occurrence.
"""
import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional

WEEKDAYS = {name.lower(): i for i, name in enumerate(calendar.day_name)}
_MONTH_ALIASES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_MONTH_RE = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_WEEKDAY_RE = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
_NUM_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
              "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fourteen": 14, "twenty": 20, "thirty": 30}
_NUM_RE = r"(\d{1,3}|a|an|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fourteen|twenty|thirty)"
_UNIT_RE = r"(hour|day|business day|working day|week|month)s?"

_DEADLINE_CUES = re.compile(
    r"(by|before|until|till|due|deadline|no later than|not later than|latest|within|expires?|expiry|"
    r"end of|on or before|due by|need(?:ed)? by|required by|respond by|reply by)\s*(?:the\s+)?(?:next\s+|this\s+)?$",
    re.I)
_PAST_CUES = re.compile(r"(received|arrived|ordered|delivered|placed|purchased|bought|paid|sent|since|last|happened|occurred|started|noticed)\b[^.?!]{0,40}$", re.I)
_TIME_AFTER = re.compile(r"^\s*(?:,|at|@|around|by|from)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)", re.I)
_TIME_BEFORE = re.compile(r"(?:at|@|around|by)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)\s*(?:on|,)?\s*$", re.I)
_TIME_24_AFTER = re.compile(r"^\s*(?:,|at|@)?\s*([01]?\d|2[0-3]):([0-5]\d)\b")


@dataclass
class DateMention:
    phrase: str
    start: int
    end: int
    date: date
    time: Optional[str] = None  # "HH:MM"
    kind: str = "absolute"  # absolute | relative
    is_deadline: bool = False

    @property
    def iso(self) -> str:
        return self.date.isoformat()

    @property
    def iso_datetime(self) -> str:
        return f"{self.iso}T{self.time}" if self.time else self.iso


def _to_date(ref) -> date:
    return ref.date() if isinstance(ref, datetime) else ref


def _safe_date(y: int, m: int, d: int) -> Optional[date]:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _add_business_days(start: date, n: int) -> date:
    cur = start
    while n > 0:
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            n -= 1
    return cur


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _weekday_date(ref: date, wd: int, mode: str, past: bool) -> date:
    if past:
        delta = (ref.weekday() - wd) % 7 or 7
        return ref - timedelta(days=delta)
    if mode == "this":
        return ref + timedelta(days=(wd - ref.weekday()) % 7)
    if mode == "next":
        monday_next = ref + timedelta(days=7 - ref.weekday())
        return monday_next + timedelta(days=wd)
    return ref + timedelta(days=(wd - ref.weekday()) % 7 or 7)


def _num(tok: str) -> int:
    tok = tok.lower()
    return int(tok) if tok.isdigit() else _NUM_WORDS.get(tok, 1)


def _absolute_year(ref: date, month: int, day: int, year: Optional[int]) -> Optional[date]:
    if year:
        return _safe_date(year, month, day)
    d = _safe_date(ref.year, month, day)
    if d and (ref - d).days > 240:  # e.g. "5 January" mentioned in November -> next January
        d = _safe_date(ref.year + 1, month, day)
    return d


def _collect(text: str, ref: date) -> List[DateMention]:
    found: List[DateMention] = []

    def add(m, d: Optional[date], kind="absolute"):
        if d:
            found.append(DateMention(m.group(0), m.start(), m.end(), d, None, kind))

    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        add(m, _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in re.finditer(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b", text):
        add(m, _safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
    for m in re.finditer(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?(?:\s+of)?\s+{_MONTH_RE}\b(?:,?\s+(\d{{4}}))?(?!\d)", text, re.I):
        add(m, _absolute_year(ref, _MONTH_ALIASES[m.group(2).lower()], int(m.group(1)), int(m.group(3)) if m.group(3) else None))
    for m in re.finditer(rf"\b{_MONTH_RE}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?!\d)(?:,?\s+(\d{{4}})(?!\d))?", text, re.I):
        add(m, _absolute_year(ref, _MONTH_ALIASES[m.group(1).lower()], int(m.group(2)), int(m.group(3)) if m.group(3) else None))

    for m in re.finditer(r"\bday after tomorrow\b", text, re.I):
        add(m, ref + timedelta(days=2), "relative")
    for m in re.finditer(r"\btomorrow\b", text, re.I):
        if not re.match(r"day after tomorrow", text[max(0, m.start() - 10):m.end()], re.I) and \
                not text[max(0, m.start() - 10):m.start()].lower().endswith("after "):
            add(m, ref + timedelta(days=1), "relative")
    for m in re.finditer(r"\b(today|tonight|eod|cob|end of (?:the )?day|close of business)\b", text, re.I):
        add(m, ref, "relative")
    for m in re.finditer(rf"\b(?:(this|next|coming|upcoming|last)\s+)?{_WEEKDAY_RE}\b", text, re.I):
        prefix = (m.group(1) or "").lower()
        wd = WEEKDAYS[m.group(2).lower()]
        past = prefix == "last" or bool(_PAST_CUES.search(text[max(0, m.start() - 60):m.start()])) and prefix in ("", "last")
        mode = {"this": "this", "coming": "this", "upcoming": "this", "next": "next"}.get(prefix, "bare")
        add(m, _weekday_date(ref, wd, mode, past), "relative")
    for m in re.finditer(rf"\b(?:in|within(?: the next)?)\s+{_NUM_RE}\s+{_UNIT_RE}\b", text, re.I):
        n, unit = _num(m.group(1)), m.group(2).lower()
        if unit == "hour":
            d = ref + timedelta(days=max(1, -(-n // 24)))
        elif unit in ("business day", "working day"):
            d = _add_business_days(ref, n)
        elif unit == "week":
            d = ref + timedelta(weeks=n)
        elif unit == "month":
            d = _add_months(ref, n)
        else:
            d = ref + timedelta(days=n)
        add(m, d, "relative")
    for m in re.finditer(rf"\b{_NUM_RE}\s+(day|week)s?\s+from now\b", text, re.I):
        n = _num(m.group(1))
        add(m, ref + timedelta(days=n * (7 if m.group(2).lower() == "week" else 1)), "relative")
    for m in re.finditer(r"\bend of (?:the |this |next )?(week|month|quarter|year)\b", text, re.I):
        phrase = m.group(0).lower()
        unit = m.group(1).lower()
        nxt = " next " in f" {phrase} "
        if unit == "week":
            base = ref + timedelta(days=7 if nxt else 0)
            d = base + timedelta(days=4 - base.weekday()) if base.weekday() <= 4 else base + timedelta(days=(4 - base.weekday()) % 7)
        elif unit == "month":
            base = _add_months(ref, 1 if nxt else 0)
            d = date(base.year, base.month, calendar.monthrange(base.year, base.month)[1])
        elif unit == "quarter":
            q_end_month = ((ref.month - 1) // 3 + 1) * 3
            d = date(ref.year, q_end_month, calendar.monthrange(ref.year, q_end_month)[1])
        else:
            d = date(ref.year + (1 if nxt else 0), 12, 31)
        add(m, d, "relative")
    for m in re.finditer(r"\bnext (week|month)\b", text, re.I):
        add(m, ref + timedelta(days=7 - ref.weekday()) if m.group(1).lower() == "week" else _add_months(ref, 1).replace(day=1), "relative")
    return found


def extract_date_mentions(text: str, reference=None) -> List[DateMention]:
    """Return non-overlapping date mentions in reading order, each flagged deadline / non-deadline."""
    ref = _to_date(reference or datetime.utcnow())
    text = text or ""
    found = _collect(text, ref)
    found.sort(key=lambda d: (d.start, -(d.end - d.start)))
    kept: List[DateMention] = []
    for d in found:
        if kept and d.start < kept[-1].end:
            if (d.end - d.start) > (kept[-1].end - kept[-1].start):
                kept[-1] = d
            continue
        kept.append(d)
    for d in kept:
        before = text[max(0, d.start - 48):d.start]
        after = text[d.end:d.end + 24]
        d.is_deadline = bool(_DEADLINE_CUES.search(before)) or d.phrase.lower().startswith(("within", "end of")) or \
            bool(re.match(r"\s*(?:is|at the latest|at latest)\b.{0,15}(deadline|latest)", after, re.I)) or \
            bool(re.search(r"deadline\s*(?:is|:)?\s*$", before, re.I))
        tm = _TIME_AFTER.match(after) or _TIME_BEFORE.search(before)
        if tm:
            hour, minute, mer = int(tm.group(1)), int(tm.group(2) or 0), tm.group(3).lower().replace(".", "")
            if 1 <= hour <= 12:
                hour = hour % 12 + (12 if mer == "pm" else 0)
                d.time = f"{hour:02d}:{minute:02d}"
        else:
            t24 = _TIME_24_AFTER.match(after)
            if t24:
                d.time = f"{int(t24.group(1)):02d}:{t24.group(2)}"
    return kept


def resolve_phrase(phrase: Optional[str], reference=None) -> Optional[str]:
    """'by Friday' -> '2026-10-02'. Returns None when nothing can be resolved."""
    if not phrase:
        return None
    mentions = extract_date_mentions(phrase, reference)
    return mentions[0].iso if mentions else None


def is_valid_iso(value) -> bool:
    try:
        datetime.strptime(str(value)[:10], "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False
