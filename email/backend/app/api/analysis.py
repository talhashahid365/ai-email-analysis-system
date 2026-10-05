"""Per-email AI endpoints (spec §28): re-run the full pipeline, or run classification / summarisation / extraction
on their own. Every handler is owner-scoped (404 for other users' emails), permission-checked and rate-limited."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.auth import get_current_user
from app.database import get_db
from app.permissions import Action, require
from app.ratelimit import ai_limiter
from app.services import ai_engine, pipeline, threads
from app.services.audit import write_audit
from app.services.bootstrap import active_category_names
from app.services.settings_store import llm_provider_override

router = APIRouter(prefix="/emails/{email_id}", tags=["AI Analysis"])


def _owned_email(db: Session, user: models.User, email_id: int) -> models.Email:
    email = db.query(models.Email).filter(models.Email.id == email_id, models.Email.user_id == user.id).first()
    if email is None or email.is_outbound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
    return email


def _run_engine(db: Session, email: models.Email, operation: str):
    """Analyse the email once and log it. Returns (result, meta)."""
    result, meta = ai_engine.analyze_email(
        email.subject, email.body_plain, email.sender_email, email.sender_name, reference=email.received_at,
        categories=active_category_names(db), thread_context=threads.thread_context_text(db, email),
        provider=llm_provider_override(db))
    db.add(models.AILog(user_id=email.user_id, email_id=email.id, operation=operation, provider=meta["provider"],
                        model=meta.get("model"), success=True, fallback_used=bool(meta.get("fallback_used")),
                        latency_ms=meta.get("latency_ms", 0), error=meta.get("error")))
    return result, meta


def _ensure_analysis(db: Session, email: models.Email) -> None:
    """Slice endpoints update an existing analysis; an unprocessed email gets the full pipeline first."""
    if email.ai_analysis is None:
        if not pipeline.process_email(email.id, db=db, notify=False):
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI processing failed for this email")
        db.refresh(email)


@router.post("/reprocess", response_model=schemas.EmailDetailResponse, dependencies=[Depends(ai_limiter)])
def reprocess_email(email_id: int, req: Request, current_user: models.User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Re-run the whole pipeline. Completed actions/deadlines and a sent reply are preserved by the pipeline."""
    require(current_user, Action.AI_ANALYZE)
    email = _owned_email(db, current_user, email_id)
    if not pipeline.process_email(email.id, db=db, notify=False):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI processing failed for this email")
    db.refresh(email)
    write_audit(db, current_user.id, "ai.reprocess", f"Email #{email_id}", {}, ip=req.client.host if req.client else None)
    return email


@router.post("/classify", response_model=schemas.AIAnalysisSchema, dependencies=[Depends(ai_limiter)])
def classify_email(email_id: int, req: Request, current_user: models.User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """Re-run classification only: category, intent, priority (+reason), sentiment, reply/action required."""
    require(current_user, Action.AI_ANALYZE)
    email = _owned_email(db, current_user, email_id)
    _ensure_analysis(db, email)
    result, meta = _run_engine(db, email, "classify")
    a = email.ai_analysis
    for field in ("category", "intent", "priority", "priority_reason", "sentiment", "reply_required", "action_required"):
        setattr(a, field, result[field])
    a.sentiment_confidence = result.get("sentiment_confidence", a.sentiment_confidence)
    a.provider = meta["provider"]
    if email.reply_status not in ("replied", "dismissed"):
        email.reply_status = "pending" if result["reply_required"] else "not_required"
    db.commit()
    db.refresh(a)
    write_audit(db, current_user.id, "ai.classify", f"Email #{email_id}", {"category": a.category}, ip=req.client.host if req.client else None)
    return a


@router.post("/summarize", dependencies=[Depends(ai_limiter)])
def summarize_email(email_id: int, req: Request, mode: Literal["short", "detailed"] = "short",
                    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Re-run summarisation only. `mode` picks which summary is returned; both are refreshed."""
    require(current_user, Action.AI_ANALYZE)
    email = _owned_email(db, current_user, email_id)
    _ensure_analysis(db, email)
    result, meta = _run_engine(db, email, "summarize")
    a = email.ai_analysis
    a.short_summary, a.detailed_summary, a.provider = result["short_summary"], result["detailed_summary"], meta["provider"]
    db.commit()
    write_audit(db, current_user.id, "ai.summarize", f"Email #{email_id}", {"mode": mode}, ip=req.client.host if req.client else None)
    return {"email_id": email.id, "mode": mode, "summary": a.short_summary if mode == "short" else a.detailed_summary,
            "provider": a.provider}


@router.post("/extract", response_model=schemas.ExtractedInfoSchema, dependencies=[Depends(ai_limiter)])
def extract_email_info(email_id: int, req: Request, current_user: models.User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """Re-run information extraction only (names, order/invoice numbers, amounts, dates, location, requested action)."""
    require(current_user, Action.AI_ANALYZE)
    email = _owned_email(db, current_user, email_id)
    _ensure_analysis(db, email)
    result, _meta = _run_engine(db, email, "extract")
    info = result.get("extracted_info") or {}
    row = email.extracted_info
    if row is None:
        row = models.ExtractedInformation(email_id=email.id, user_id=email.user_id)
        db.add(row)
    for field in schemas.ExtractedInfoSchema.model_fields:
        setattr(row, field, info.get(field))
    db.commit()
    db.refresh(row)
    write_audit(db, current_user.id, "ai.extract", f"Email #{email_id}", {}, ip=req.client.host if req.client else None)
    return row
