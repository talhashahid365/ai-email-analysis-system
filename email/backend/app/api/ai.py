import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.ratelimit import ai_limiter
from app.services import mailer, pipeline, smart_reply, threads
from app.services.audit import write_audit
from app.timeutil import utcnow

router = APIRouter(prefix="/emails/{email_id}", tags=["AI & Smart Reply"])


@router.post("/reply", response_model=schemas.AIReplySchema, dependencies=[Depends(ai_limiter)])
def create_smart_reply(
    email_id: int,
    request: schemas.SmartReplyRequest,
    req_http: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_obj = (
        db.query(models.Email)
        .filter(models.Email.id == email_id, models.Email.user_id == current_user.id)
        .first()
    )
    if not email_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    thread_history = threads.thread_history(db, email_obj)

    extracted_dict = None
    if email_obj.extracted_info:
        extracted_dict = {
            "order_number": email_obj.extracted_info.order_number,
            "product": email_obj.extracted_info.product,
            "amount": email_obj.extracted_info.amount,
            "customer_name": email_obj.extracted_info.customer_name,
            "company": email_obj.extracted_info.company,
        }

    category = email_obj.ai_analysis.category if email_obj.ai_analysis else "General Information"
    tone = request.tone or "Professional"

    draft_body, meta = smart_reply.generate_smart_reply(
        db=db,
        tone=tone,
        subject=email_obj.subject,
        body=email_obj.body_plain,
        sender_name=email_obj.sender_name,
        sender_email=email_obj.sender_email,
        thread_history=thread_history,
        category=category,
        extracted=extracted_dict,
        custom_instructions=request.custom_instructions,
        reject_reason=request.reject_reason,
    )

    prev_replies_count = (
        db.query(models.AIReply)
        .filter(models.AIReply.email_id == email_id, models.AIReply.user_id == current_user.id)
        .count()
    )

    ai_reply = models.AIReply(
        email_id=email_obj.id,
        user_id=current_user.id,
        selected_tone=tone,
        suggested_body=draft_body,
        status="draft",
        provider=meta.get("provider", "heuristic"),
        model=meta.get("model"),
        fallback_used=meta.get("fallback_used", False),
        custom_instructions=request.custom_instructions,
        version=prev_replies_count + 1,
    )
    db.add(ai_reply)

    db.add(
        models.AILog(
            user_id=current_user.id,
            email_id=email_obj.id,
            operation="reply",
            provider=meta.get("provider", "heuristic"),
            model=meta.get("model"),
            success=True,
            fallback_used=meta.get("fallback_used", False),
            latency_ms=meta.get("latency_ms", 0),
            error=meta.get("error"),
        )
    )

    db.commit()
    db.refresh(ai_reply)
    write_audit(db, current_user.id, "ai.generate_reply", f"Email #{email_id}", {"tone": tone, "version": ai_reply.version}, ip=req_http.client.host if req_http.client else None)
    return ai_reply


@router.post("/reply/{reply_id}/approve", response_model=schemas.AIReplySchema)
def approve_smart_reply(
    email_id: int,
    reply_id: int,
    request: schemas.SmartReplyApproveRequest,
    req_http: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reply_obj = (
        db.query(models.AIReply)
        .filter(
            models.AIReply.id == reply_id,
            models.AIReply.email_id == email_id,
            models.AIReply.user_id == current_user.id,
        )
        .first()
    )
    if not reply_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Smart reply draft not found")

    email_obj = (
        db.query(models.Email)
        .filter(models.Email.id == email_id, models.Email.user_id == current_user.id)
        .first()
    )
    if not email_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    if reply_obj.status == "approved":  # a double click / retry must never e-mail the customer twice
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This reply was already approved and sent.")

    final_body = request.edited_body or reply_obj.edited_body or reply_obj.suggested_body
    if request.edited_body:
        reply_obj.edited_body = request.edited_body

    # Send first: if SMTP is configured but the mail cannot be delivered, nothing is marked as replied.
    subject = email_obj.subject if email_obj.subject.lower().lstrip().startswith("re:") else f"Re: {email_obj.subject}"
    domain = (settings.SMTP_USER.split("@")[-1] if "@" in settings.SMTP_USER else "ai-mail.local")
    out_message_id = f"<{uuid.uuid4().hex}@{domain}>"  # same id is e-mailed and stored, so the customer's follow-up threads correctly
    delivered, note = mailer.send_reply_email(email_obj.sender_email, subject, final_body, from_name=current_user.full_name,
                                              in_reply_to=email_obj.message_id, message_id=out_message_id)
    smtp_configured = bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SEND_REPLIES_VIA_SMTP)
    if smtp_configured and not delivered:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=note)

    pipeline.record_outbound_reply(db, current_user, email_obj, final_body, reply_obj, message_id=out_message_id)
    db.commit()
    db.refresh(reply_obj)

    write_audit(db, current_user.id, "ai.approve_reply", f"AIReply #{reply_id}",
                {"email_id": email_id, "delivered": delivered, "to": email_obj.sender_email}, ip=req_http.client.host if req_http.client else None)
    reply_obj.delivered, reply_obj.delivery_note = delivered, note  # transient, not stored
    return reply_obj


@router.post("/reply/{reply_id}/reject", response_model=schemas.AIReplySchema)
def reject_smart_reply(
    email_id: int,
    reply_id: int,
    request: schemas.SmartReplyRejectRequest,
    req_http: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reply_obj = (
        db.query(models.AIReply)
        .filter(
            models.AIReply.id == reply_id,
            models.AIReply.email_id == email_id,
            models.AIReply.user_id == current_user.id,
        )
        .first()
    )
    if not reply_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Smart reply draft not found")

    reply_obj.status = "rejected"
    reply_obj.rejected_at = utcnow()
    reply_obj.reject_reason = request.reason

    db.commit()
    db.refresh(reply_obj)

    write_audit(db, current_user.id, "ai.reject_reply", f"AIReply #{reply_id}", {"reason": request.reason}, ip=req_http.client.host if req_http.client else None)
    return reply_obj
