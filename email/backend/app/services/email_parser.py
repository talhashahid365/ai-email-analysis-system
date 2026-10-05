"""Email parser: .eml files, pasted text, CSV / JSON datasets -> normalised dicts."""
import csv
import email
import io
import json
import re
from datetime import datetime
from email import policy
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

from app.services.text_utils import html_to_text, sanitize
from app.timeutil import to_naive_utc

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_html_text(raw_html: str) -> str:  # backwards-compatible name
    return html_to_text(raw_html)


def _addr(value: Optional[str], default_name: str = "Unknown Sender") -> Tuple[str, str]:
    name, addr = parseaddr(value or "")
    addr = addr.strip().lower()
    if not _EMAIL_RE.match(addr):
        addr = "unknown@example.com"
    return (name.strip() or addr.split("@")[0].replace(".", " ").title() or default_name), addr


def _date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return to_naive_utc(parsedate_to_datetime(value))
    except (TypeError, ValueError):
        pass
    try:
        return to_naive_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except ValueError:
        return None


def parse_eml_content(file_bytes: bytes) -> Dict[str, Any]:
    msg = email.message_from_bytes(file_bytes, policy=policy.default)
    sender_name, sender_email = _addr(str(msg.get("From", "")))
    _, recipient = _addr(str(msg.get("To", "")), "me")
    body_plain, body_html = "", ""
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.is_multipart() or "attachment" in str(part.get("Content-Disposition", "")).lower():
            continue
        ctype = part.get_content_type()
        try:
            content = part.get_content()
        except Exception:
            payload = part.get_payload(decode=True) or b""
            content = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if ctype == "text/plain" and not body_plain:
            body_plain = str(content)
        elif ctype == "text/html" and not body_html:
            body_html = str(content)
    if not body_plain and body_html:
        body_plain = html_to_text(body_html)
    refs = str(msg.get("References", "") or "").split()
    return {
        "sender_name": sender_name, "sender_email": sender_email, "recipient_email": recipient,
        "subject": sanitize(str(msg.get("Subject", "") or "(no subject)"), 500).strip() or "(no subject)",
        "body_plain": sanitize(body_plain), "body_html": body_html or None,
        "received_at": _date(msg.get("Date")),
        "message_id": (str(msg.get("Message-ID", "")).strip() or None),
        "in_reply_to": (str(msg.get("In-Reply-To", "")).strip() or (refs[-1] if refs else None)),
    }


_HEADER_LINE = re.compile(r"^(from|to|subject|date|cc)\s*:\s*(.*)$", re.I)


def parse_pasted_text(text: str, sender_email: Optional[str] = None, sender_name: Optional[str] = None,
                      subject: Optional[str] = None) -> Dict[str, Any]:
    """Accepts a raw email with optional 'From:/Subject:' header lines, or just a body."""
    text = sanitize(text).strip()
    headers: Dict[str, str] = {}
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = _HEADER_LINE.match(lines[i].strip())
        if not m:
            break
        headers[m.group(1).lower()] = m.group(2).strip()
        i += 1
    body = "\n".join(lines[i:]).strip() if headers else text
    name, addr = _addr(headers.get("from")) if headers.get("from") else (sender_name, sender_email)
    return {
        "sender_name": sender_name or name or "Unknown Sender",
        "sender_email": (sender_email or addr or "unknown@example.com").lower(),
        "recipient_email": _addr(headers.get("to"))[1] if headers.get("to") else None,
        "subject": subject or headers.get("subject") or (body.split("\n")[0][:80] if body else "(no subject)"),
        "body_plain": body, "body_html": None, "received_at": _date(headers.get("date")),
        "message_id": None, "in_reply_to": None,
    }


_ALIASES = {
    "sender_email": ["sender_email", "from_email", "from", "sender", "email"],
    "sender_name": ["sender_name", "from_name", "name"],
    "recipient_email": ["recipient_email", "to", "recipient"],
    "subject": ["subject", "title"],
    "body_plain": ["body_plain", "body", "text", "content", "message"],
    "received_at": ["received_at", "date", "timestamp", "sent_at"],
    "message_id": ["message_id", "id"],
    "in_reply_to": ["in_reply_to", "reply_to_id", "parent_id"],
}


def _normalise_row(row: Dict[str, Any]) -> Dict[str, Any]:
    lower = {str(k).strip().lower(): v for k, v in row.items()}
    out: Dict[str, Any] = {}
    for field, names in _ALIASES.items():
        for n in names:
            if lower.get(n) not in (None, ""):
                out[field] = lower[n]
                break
    if "sender_email" in out:
        name, addr = _addr(str(out["sender_email"]))
        out["sender_email"] = addr
        out.setdefault("sender_name", name)
    out.setdefault("sender_name", "Unknown Sender")
    out["received_at"] = _date(str(out["received_at"])) if out.get("received_at") else None
    out["body_html"] = None
    return out


def parse_dataset_file(filename: str, content: bytes, max_rows: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Returns (valid_rows, errors). Supports .json (list or {emails:[...]}), .jsonl and .csv."""
    text = content.decode("utf-8-sig", errors="replace")
    name = filename.lower()
    if name.endswith(".csv"):
        raw_rows = list(csv.DictReader(io.StringIO(text)))
    elif name.endswith(".jsonl"):
        raw_rows = [json.loads(l) for l in text.splitlines() if l.strip()]
    else:
        data = json.loads(text)
        raw_rows = data.get("emails", []) if isinstance(data, dict) else data
    if not isinstance(raw_rows, list):
        raise ValueError("Dataset must be a list of email objects")
    if len(raw_rows) > max_rows:
        raise ValueError(f"Too many rows ({len(raw_rows)}); limit is {max_rows}")
    valid, errors = [], []
    for idx, raw in enumerate(raw_rows, 1):
        if not isinstance(raw, dict):
            errors.append({"row": idx, "error": "row is not an object"})
            continue
        row = _normalise_row(raw)
        if not row.get("subject") or not row.get("body_plain") or not row.get("sender_email"):
            errors.append({"row": idx, "error": "subject, body and sender_email are required"})
            continue
        row["subject"] = sanitize(str(row["subject"]), 500)
        row["body_plain"] = sanitize(str(row["body_plain"]))
        valid.append(row)
    return valid, errors
