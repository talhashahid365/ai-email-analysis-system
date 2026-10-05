"""Provider-agnostic LLM client. API keys live only in backend environment variables.

Providers: gemini | openai | anthropic. `LLM_PROVIDER=auto` picks the first provider with a key
(anthropic -> openai -> gemini). With no key the callers fall back to the heuristic engine.
"""
import json
import re
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from app.config import settings

PROVIDERS = ("anthropic", "openai", "gemini")


class LLMError(RuntimeError):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


@dataclass
class LLMInfo:
    provider: str
    model: str
    latency_ms: int


def _key_for(provider: str) -> str:
    return {"gemini": settings.GEMINI_API_KEY, "openai": settings.OPENAI_API_KEY,
            "anthropic": settings.ANTHROPIC_API_KEY}.get(provider, "")


def _model_for(provider: str) -> str:
    return {"gemini": settings.GEMINI_MODEL, "openai": settings.OPENAI_MODEL,
            "anthropic": settings.ANTHROPIC_MODEL}[provider]


def resolve_provider(override: Optional[str] = None) -> Optional[str]:
    choice = (override or settings.LLM_PROVIDER or "auto").lower()
    if choice == "heuristic":
        return None
    if choice in PROVIDERS:
        return choice if _key_for(choice) else None
    for p in PROVIDERS:
        if _key_for(p):
            return p
    return None


def _scrub(message: str) -> str:
    for p in PROVIDERS:
        k = _key_for(p)
        if k:
            message = message.replace(k, "***")
    return message[:500]


def _post(url: str, headers: dict, payload: dict) -> dict:
    import httpx  # imported lazily so the heuristic engine works without the dependency
    last_err, status = "unknown error", 0
    for attempt in range(settings.LLM_MAX_RETRIES + 1):
        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=settings.LLM_TIMEOUT_SECONDS)
            if resp.status_code == 200:
                return resp.json()
            status = resp.status_code
            detail = ""
            try:  # providers put the human-readable reason in error.message
                err = resp.json().get("error", {})
                detail = err.get("message", "") if isinstance(err, dict) else str(err)
            except Exception:
                detail = resp.text[:200]
            last_err = f"HTTP {resp.status_code}: {detail}"[:400]
            if resp.status_code not in (429, 500, 502, 503, 504):
                break
        except Exception as exc:  # network / timeout
            last_err = type(exc).__name__
        time.sleep(min(2 ** attempt, 4))
    raise LLMError(_scrub(f"LLM request failed: {last_err}"), status)


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise LLMError("Model did not return JSON")
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError as exc:
            raise LLMError("Model returned invalid JSON") from exc


def complete(system: str, user: str, json_mode: bool = False, provider: Optional[str] = None,
             max_tokens: int = 1500) -> Tuple[str, LLMInfo]:
    prov = resolve_provider(provider)
    if not prov:
        raise LLMError("No LLM provider configured")
    model, key, started = _model_for(prov), _key_for(prov), time.monotonic()
    if prov == "gemini":
        # Gemini models are retired often (2.0-flash shut down on 2026-06-01), so try the configured model first
        # and then each fallback until one is available.
        candidates = [model] + [m.strip() for m in settings.GEMINI_FALLBACK_MODELS.split(",")
                                if m.strip() and m.strip() != model]
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                # headroom: newer Gemini models spend part of this budget on internal reasoning
                "generationConfig": {"maxOutputTokens": max(max_tokens * 4, 4096), "temperature": 0.2,
                                     **({"responseMimeType": "application/json"} if json_mode else {})}}
        data, last_exc = None, None
        for cand in candidates:
            try:
                data = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{cand}:generateContent",
                             {"x-goog-api-key": key, "Content-Type": "application/json"}, body)
                model = cand
                break
            except LLMError as exc:
                last_exc = exc
                if exc.status not in (400, 404):  # key / quota / network problems will not be fixed by another model
                    raise
        if data is None:
            raise last_exc or LLMError("Gemini request failed")
        try:
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected Gemini response (empty or blocked)") from exc
    elif prov == "openai":
        body = {"model": model, "temperature": 0.2, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        data = _post("https://api.openai.com/v1/chat/completions",
                     {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, body)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected OpenAI response") from exc
    else:
        body = {"model": model, "max_tokens": max_tokens, "temperature": 0.2, "system": system,
                "messages": [{"role": "user", "content": user}]}
        data = _post("https://api.anthropic.com/v1/messages",
                     {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, body)
        try:
            text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError) as exc:
            raise LLMError("Unexpected Anthropic response") from exc
    return text, LLMInfo(prov, model, int((time.monotonic() - started) * 1000))


def complete_json(system: str, user: str, provider: Optional[str] = None, max_tokens: int = 2000) -> Tuple[dict, LLMInfo]:
    text, info = complete(system, user, json_mode=True, provider=provider, max_tokens=max_tokens)
    return _extract_json(text), info
