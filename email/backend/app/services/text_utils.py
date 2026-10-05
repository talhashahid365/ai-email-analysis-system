"""Text cleaning step of the pipeline: HTML stripping, quoted-reply removal, sanitising, injection flags, and vector embedding similarity."""
import html
import math
import re
from typing import Tuple, List, Dict

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_QUOTE_HEADERS = [
    re.compile(r"^\s*On .{5,200}wrote:\s*$", re.I | re.M),
    re.compile(r"^\s*-{2,}\s*Original Message\s*-{2,}\s*$", re.I | re.M),
    re.compile(r"^\s*From:\s.+\n\s*(Sent|Date):\s.+", re.I | re.M),
    re.compile(r"^\s*_{10,}\s*$", re.M),
]
_INJECTION = re.compile(
    r"(ignore (all |any )?(previous|prior|above) (instructions|prompts)|disregard (the )?(system|previous) (prompt|instructions)|"
    r"you are now|system prompt|reveal your (prompt|instructions)|act as (an?|the) (admin|system)|"
    r"forward (all|every) (emails|messages) to|delete (all|every) (emails|messages))", re.I)


def sanitize(text: str, max_chars: int = 50_000) -> str:
    text = _CONTROL.sub("", text or "").replace("\r\n", "\n").replace("\r", "\n")
    return text[:max_chars]


def html_to_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    t = re.sub(r"(?is)<(script|style|head).*?>.*?</\1>", "", raw_html)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(p|div|tr|li|h[1-6])>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def split_quoted(body: str) -> Tuple[str, str]:
    """Return (new_text, quoted_history). Keeps analysis focused on the latest message."""
    body = body or ""
    cut = len(body)
    for pat in _QUOTE_HEADERS:
        m = pat.search(body)
        if m and m.start() > 0:
            cut = min(cut, m.start())
    lines, new_lines, quoted_started = body[:cut].split("\n"), [], False
    for ln in lines:
        if ln.lstrip().startswith(">"):
            quoted_started = True
        if not quoted_started:
            new_lines.append(ln)
    new_text = "\n".join(new_lines).strip()
    quoted = (body[len("\n".join(new_lines)):]).strip() if quoted_started or cut < len(body) else ""
    return (new_text or body.strip()), quoted


def clean_for_analysis(body: str, max_chars: int = 6000) -> str:
    text, _ = split_quoted(body)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:max_chars].strip()


def detect_injection(text: str) -> List[str]:
    return ["prompt_injection_suspected"] if _INJECTION.search(text or "") else []


def normalize_subject(subject: str) -> str:
    s = (subject or "").strip()
    while True:
        n = re.sub(r"^\s*(re|fwd?|aw|sv)\s*:\s*", "", s, flags=re.I)
        if n == s:
            break
        s = n
    return re.sub(r"\s+", " ", s).strip().lower()


# --- Vector Embedding & Cosine Similarity for True RAG ---
def compute_embedding_vector(text: str) -> Dict[str, float]:
    """Convert text into normalized term-frequency embedding vector."""
    tokens = re.findall(r"\w+", (text or "").lower())
    if not tokens:
        return {}
    counts: Dict[str, int] = {}
    for t in tokens:
        if len(t) > 2:
            counts[t] = counts.get(t, 0) + 1
    norm = math.sqrt(sum(v * v for v in counts.values()))
    if norm == 0:
        return {}
    return {k: v / norm for k, v in counts.items()}


def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """Calculate cosine similarity between two embedding vectors."""
    if not vec1 or not vec2:
        return 0.0
    common_keys = set(vec1.keys()) & set(vec2.keys())
    dot_product = sum(vec1[k] * vec2[k] for k in common_keys)
    return dot_product
