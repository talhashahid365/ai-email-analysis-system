import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app import models
from app.services import llm
from app.services import settings_store
from app.timeutil import utcnow

log = logging.getLogger("app.smart_reply")

TONE_PROMPTS = {
    "Professional": "Write a polite, professional, and clear business response.",
    "Friendly": "Write a warm, approachable, and encouraging response.",
    "Short": "Write a concise, direct 2-3 sentence response focusing only on key facts.",
    "Detailed": "Write a comprehensive response addressing all points in depth.",
    "Apologetic": "Write a deeply empathetic and apologetic response acknowledging any inconvenience and providing concrete next steps.",
    "Formal": "Write a formal, structured executive response suitable for official record.",
}


def generate_heuristic_reply(
    tone: str,
    category: str,
    sender_name: str,
    subject: str,
    extracted: Optional[Dict[str, Any]] = None,
    reject_reason: Optional[str] = None,
) -> str:
    """Generate intelligent template reply based on tone and metadata when LLM API is unavailable."""
    order_num = extracted.get("order_number") if extracted else None
    order_str = f" for order #{order_num}" if order_num else ""
    feedback_note = f"\n\nNote addressing feedback ({reject_reason}): We have noted your request and adjusted accordingly." if reject_reason else ""

    if tone == "Apologetic" or category == "Customer Complaint":
        return (
            f"Dear {sender_name},\n\n"
            f"Thank you for contacting us regarding '{subject}'. We sincerely apologize for the inconvenience caused{order_str}.\n\n"
            f"Our team is currently reviewing your request. Please reply with any additional details so we can resolve this immediately for you.{feedback_note}\n\n"
            f"Best regards,\nCustomer Support Team"
        )
    elif tone == "Short":
        return (
            f"Hi {sender_name},\n\n"
            f"Thanks for reaching out about '{subject}'. We've logged your request{order_str} and will follow up shortly.{feedback_note}\n\n"
            f"Best,\nSupport Team"
        )
    elif tone == "Friendly":
        return (
            f"Hi {sender_name}!\n\n"
            f"Thanks so much for getting in touch about '{subject}'! We're happy to help you out{order_str}.\n\n"
            f"We are working on this right now and will get back to you with an update as soon as possible.{feedback_note}\n\n"
            f"Warmly,\nThe Team"
        )
    elif tone == "Formal":
        return (
            f"Dear {sender_name},\n\n"
            f"This email serves as official confirmation of receipt for your correspondence regarding '{subject}'{order_str}.\n\n"
            f"The matter has been assigned to a representative for formal review. You will receive further communication within one business day.{feedback_note}\n\n"
            f"Sincerely,\nExecutive Services"
        )
    else:  # Professional default
        return (
            f"Dear {sender_name},\n\n"
            f"Thank you for reaching out to us regarding '{subject}'.\n\n"
            f"We have received your message{order_str} and are reviewing the details provided. We will update you promptly once processing is complete.{feedback_note}\n\n"
            f"Best regards,\nSupport & Operations Team"
        )


def generate_smart_reply(
    db: Optional[Session],
    tone: str,
    subject: str,
    body: str,
    sender_name: str,
    sender_email: str,
    thread_history: List[Dict[str, Any]],
    category: str,
    extracted: Optional[Dict[str, Any]] = None,
    custom_instructions: Optional[str] = None,
    reject_reason: Optional[str] = None,
    provider_override: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Generate context-aware reply using shared LLM layer with thread, extracted info, reject feedback, and template fallback."""
    tone_instruction = TONE_PROMPTS.get(tone, TONE_PROMPTS["Professional"])
    prov = provider_override or (settings_store.llm_provider_override(db) if db else None)
    resolved = llm.resolve_provider(prov)

    history_str = ""
    if thread_history:
        history_str = "CONVERSATION THREAD HISTORY:\n"
        for idx, msg in enumerate(thread_history, 1):
            role_label = "You" if msg.get("role") == "you" else msg.get("name", "Sender")
            history_str += f"{idx}. [{role_label}]: {msg.get('body')}\n"

    if not resolved:
        # No LLM provider configured — fall back to heuristic template immediately
        fallback_text = generate_heuristic_reply(tone, category, sender_name, subject, extracted, reject_reason)
        return fallback_text, {
            "provider": "heuristic",
            "model": "template-engine",
            "latency_ms": 0,
            "fallback_used": False,
            "error": None,
        }

    system_prompt = (
        "You are writing a response to an email thread as a customer service / business representative.\n"
        f"TONE INSTRUCTION: {tone_instruction}\n"
        "Instructions: Return ONLY the plain text email response body without any markdown block quotes, extra tags, or commentary."
    )

    user_prompt = (
        f"EMAIL METADATA:\n"
        f"Sender: {sender_name} <{sender_email}>\n"
        f"Subject: {subject}\n"
        f"Category: {category}\n"
        f"Extracted Info: {json.dumps(extracted) if extracted else '{}'}\n\n"
        f"{history_str}\n"
        f"LATEST MESSAGE BODY:\n{body}\n\n"
    )

    if custom_instructions:
        user_prompt += f"ADDITIONAL INSTRUCTIONS: {custom_instructions}\n"
    if reject_reason:
        user_prompt += f"PREVIOUS DRAFT REJECTED REASON: {reject_reason}. Please revise the response to specifically address this feedback.\n"

    user_prompt += "\nWrite the reply:"

    try:
        reply_text, info = llm.complete(system_prompt, user_prompt, provider=resolved)
        meta = {
            "provider": info.provider,
            "model": info.model,
            "latency_ms": info.latency_ms,
            "fallback_used": False,
        }
        return reply_text.strip(), meta
    except Exception as exc:
        log.warning("LLM smart reply generation failed, falling back to heuristic: %s", exc)
        fallback_text = generate_heuristic_reply(tone, category, sender_name, subject, extracted, reject_reason)
        meta = {
            "provider": "heuristic",
            "model": "template-engine",
            "latency_ms": 0,
            "fallback_used": True,
            "error": str(exc),
        }
        return fallback_text, meta
