import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app import models
from app.services import llm, search, settings_store, text_utils

log = logging.getLogger("app.rag_assistant")


# phrase in the question -> preset understood by search.resolve_date_range
_DATE_PHRASES = (
    (r"\btoday(?:'s)?\b", "today"),
    (r"\byesterday\b", "yesterday"),
    (r"\b(?:this|current) week\b", "this_week"),
    (r"\blast month\b", "last_month"),
    (r"\b(?:this|current) month\b", "this_month"),
    (r"\b(?:this|current) year\b", "this_year"),
    (r"\b(?:last|past) (\d{1,3}) days?\b", None),
    (r"\b(?:last|past) 7 days\b|\b(?:last|past) week\b", "last_7_days"),
)


def _apply_date_phrase(q_lower: str, f: "search.EmailFilters") -> None:
    """Translate 'today', 'this week', 'last 3 days'... into date_from/date_to so the filter really narrows the search."""
    for pattern, preset in _DATE_PHRASES:
        m = re.search(pattern, q_lower)
        if not m:
            continue
        if preset is None:
            preset = f"last_{int(m.group(1))}_days"
        try:
            f.date_from, f.date_to = search.resolve_date_range(preset)
        except search.SearchError:
            continue
        return


def extract_query_filters(question: str) -> search.EmailFilters:
    """Fallback heuristic parser to convert natural language queries into EmailFilters."""
    q_lower = question.lower()
    f = search.EmailFilters()

    if "unread" in q_lower:
        f.is_read = False
    elif re.search(r"\b(?:already read|have read|been read|read emails?)\b", q_lower):
        f.is_read = True

    _apply_date_phrase(q_lower, f)

    if "starred" in q_lower or "favorite" in q_lower:
        f.is_starred = True

    if "urgent" in q_lower or "critical" in q_lower or "high priority" in q_lower:
        f.priorities = ["HIGH", "CRITICAL"]

    if "complaint" in q_lower or "angry" in q_lower:
        if "angry" in q_lower:
            f.sentiments = ["Angry", "Negative"]
        if "complaint" in q_lower:
            f.categories = ["Customer Complaint"]

    if "sales" in q_lower or "pricing" in q_lower or "quote" in q_lower:
        f.categories = ["Sales Inquiry"]

    if "support" in q_lower or "help" in q_lower or "bug" in q_lower:
        f.categories = ["Support Request"]

    if "payment" in q_lower or "invoice" in q_lower or "billing" in q_lower:
        f.categories = ["Invoice / Payment"]

    if "meeting" in q_lower or "schedule" in q_lower:
        f.categories = ["Meeting Request"]

    if "job" in q_lower or "application" in q_lower or "resume" in q_lower:
        f.categories = ["Job Application"]

    if "reply" in q_lower or "waiting for response" in q_lower or "needs reply" in q_lower:
        f.reply_required = True

    if "action" in q_lower or "pending" in q_lower or "task" in q_lower:
        f.action_required = True

    # Free text fallback if no specific structured filters matched
    if not f.has_structured():
        f.q = question.strip()

    return f


def process_assistant_query(
    question: str,
    db: Session,
    user_id: int,
    conversation_id: Optional[int] = None,
    provider_override: Optional[str] = None,
) -> Tuple[str, List[models.Email], Dict[str, Any]]:
    """Process natural language question using structured filter resolution, vector embedding similarity ranking, and LLM synthesis with conversation memory."""

    # 1. Fetch conversation memory if available
    conv_history_str = ""
    if conversation_id:
        prior_msgs = (
            db.query(models.AIMessage)
            .filter(models.AIMessage.conversation_id == conversation_id)
            .order_by(models.AIMessage.id.desc())
            .limit(6)
            .all()
        )
        if prior_msgs:
            lines = []
            for m in reversed(prior_msgs):
                sender = "User" if m.sender == "user" else "Assistant"
                lines.append(f"{sender}: {m.content}")
            conv_history_str = "PREVIOUS CONVERSATION HISTORY:\n" + "\n".join(lines) + "\n\n"

    # 2. Try LLM filter generation first if provider configured
    prov = provider_override or settings_store.llm_provider_override(db)
    filter_dict = {}

    if llm.resolve_provider(prov):
        filter_system_prompt = (
            "You are a query parsing assistant for an email system. Convert the user's question into a JSON object of search filters.\n"
            "Supported fields:\n"
            "- q: free text search query (string or null)\n"
            "- sender: substring search for sender name/email (string or null)\n"
            "- sentiments: list of strings (e.g. ['Positive', 'Neutral', 'Negative', 'Angry', 'Urgent'])\n"
            "- priorities: list of strings (e.g. ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])\n"
            "- categories: list of strings (e.g. ['Sales Inquiry', 'Customer Complaint', 'Support Request', 'Meeting Request', 'Invoice / Payment', 'Job Application', 'General Information', 'Spam', 'Urgent', 'Other'])\n"
            "- reply_required: boolean or null\n"
            "- action_required: boolean or null\n"
            "- is_read: boolean or null\n"
            "- is_starred: boolean or null\n"
            "- date_preset: one of today, yesterday, this_week, this_month, last_month, this_year, last_7_days, last_30_days, or null\n"
            "Return ONLY valid JSON."
        )
        filter_user_prompt = f"{conv_history_str}USER QUESTION: {question}\n\nExtract JSON filters:"
        try:
            parsed_json, _ = llm.complete_json(filter_system_prompt, filter_user_prompt, provider=prov)
            filter_dict = parsed_json
            preset = filter_dict.pop("date_preset", None) if isinstance(filter_dict, dict) else None
            if preset:
                start, end = search.resolve_date_range(str(preset))
                filter_dict["date_from"], filter_dict["date_to"] = start, end
        except Exception as exc:
            log.warning("LLM filter parsing failed, falling back to heuristic: %s", exc)

    if not filter_dict:
        filters_obj = extract_query_filters(question)
    else:
        try:
            filters_obj = search.EmailFilters.from_dict(filter_dict)
        except Exception:
            filters_obj = extract_query_filters(question)

    # 3. Perform database retrieval candidate fetching
    matching_emails, total_count = search.run_search(db, user_id, filters_obj, limit=20)

    # If structured search gave no results and we had structured filters, fall back to free text query
    if not matching_emails and filters_obj.has_structured():
        fallback_filters = search.EmailFilters(q=question.strip())
        matching_emails, total_count = search.run_search(db, user_id, fallback_filters, limit=20)
        filters_obj = fallback_filters

    applied_filters = filters_obj.to_dict()

    if not matching_emails:
        answer = f"I searched your inbox for {filters_obj.describe()}, but found no matching records."
        return answer, [], applied_filters

    # 4. RAG Vector Embedding Cosine Similarity Ranking
    query_vector = text_utils.compute_embedding_vector(question)
    scored_emails = []

    for email in matching_emails:
        doc_text = f"{email.subject} {email.body_plain}"
        doc_vector = text_utils.compute_embedding_vector(doc_text)
        sim_score = text_utils.cosine_similarity(query_vector, doc_vector)
        scored_emails.append((sim_score, email))

    # Sort descending by embedding similarity score
    scored_emails.sort(key=lambda x: x[0], reverse=True)
    ranked_emails = [e for _, e in scored_emails[:10]]

    # 5. Context preparation for answer synthesis
    email_lines = []
    for e in ranked_emails:
        analysis = e.ai_analysis
        cat = analysis.category if analysis else "General"
        prio = analysis.priority if analysis else "MEDIUM"
        sent = analysis.sentiment if analysis else "Neutral"
        summ = analysis.short_summary if analysis else e.body_plain[:120]
        email_lines.append(
            f"- Email #{e.id} | From: {e.sender_name} <{e.sender_email}> | Subject: '{e.subject}' | Category: {cat} | Priority: {prio} | Sentiment: {sent} | Summary: {summ}"
        )
    context_str = "\n".join(email_lines)

    # 6. Synthesize final answer using LLM or structured fallback
    if llm.resolve_provider(prov):
        answer_system = (
            "You are the AI Email Assistant for a user. Answer the user's question clearly, concisely, and accurately based strictly on the retrieved email context provided.\n"
            "Cite specific email subjects and senders where relevant. Refer to email IDs as #<id>."
        )
        answer_user = f"{conv_history_str}RETRIEVED EMAIL CONTEXT ({filters_obj.describe()}):\n{context_str}\n\nUSER QUESTION: {question}\n\nProvide answer:"
        try:
            answer_text, info = llm.complete(answer_system, answer_user, provider=prov)
            db.add(
                models.AILog(
                    user_id=user_id,
                    operation="assistant",
                    provider=info.provider,
                    model=info.model,
                    success=True,
                    latency_ms=info.latency_ms,
                )
            )
            db.flush()
            return answer_text.strip(), ranked_emails, applied_filters
        except Exception as exc:
            log.warning("LLM answer synthesis failed, falling back to structured summary: %s", exc)
            db.add(
                models.AILog(
                    user_id=user_id,
                    operation="assistant",
                    provider="heuristic",
                    success=False,
                    error=str(exc),
                )
            )
            db.flush()

    # Heuristic structured answer
    desc = filters_obj.describe()
    lines = [f"Found {len(ranked_emails)} email(s) matching ({desc}):\n"]
    for e in ranked_emails:
        analysis = e.ai_analysis
        cat = analysis.category if analysis else "General"
        lines.append(f"• [#{e.id}] **{e.sender_name}**: '{e.subject}' ({cat})")

    lines.append("\nYou can select any of these emails in your inbox to review details, extract information, or generate smart replies.")
    answer = "\n".join(lines)
    return answer, ranked_emails, applied_filters
