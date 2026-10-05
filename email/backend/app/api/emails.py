import csv
import json
import io
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.ratelimit import upload_limiter
from app.services import imap_sync, pipeline, search, threads
from app.services.audit import write_audit
from app.services.email_parser import parse_dataset_file, parse_eml_content

router = APIRouter(prefix="/emails", tags=["Emails"])


def _format_email_item(e: models.Email) -> dict:
    analysis = e.ai_analysis
    return {
        "id": e.id,
        "user_id": e.user_id,
        "thread_id": e.thread_id,
        "sender_name": e.sender_name,
        "sender_email": e.sender_email,
        "recipient_email": e.recipient_email,
        "subject": e.subject,
        "body_preview": e.body_plain[:120] + "..." if len(e.body_plain) > 120 else e.body_plain,
        "received_at": e.received_at,
        "is_read": e.is_read,
        "is_starred": e.is_starred,
        "is_archived": e.is_archived,
        "is_outbound": e.is_outbound,
        "reply_status": e.reply_status,
        "processing_status": e.processing_status,
        "category": analysis.category if analysis else "Unprocessed",
        "priority": analysis.priority if analysis else "MEDIUM",
        "sentiment": analysis.sentiment if analysis else "Neutral",
        "reply_required": analysis.reply_required if analysis else False,
        "action_required": analysis.action_required if analysis else False,
    }


@router.post("", response_model=schemas.EmailDetailResponse, status_code=status.HTTP_201_CREATED)
def create_email(
    email_in: schemas.EmailCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        res = pipeline.ingest_email(db, current_user, email_in.model_dump())
    except pipeline.IngestError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if not res.duplicate:
        pipeline.enqueue(background_tasks, [res.email.id], db=db)

    write_audit(db, current_user.id, "email.create", f"Email #{res.email.id}", {"subject": res.email.subject, "duplicate": res.duplicate}, ip=request.client.host if request.client else None)
    return res.email


@router.post("/upload", response_model=schemas.EmailDetailResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(upload_limiter)])
async def upload_eml_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    request: Request = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename = file.filename or "upload.eml"
    if not (filename.lower().endswith(".eml") or filename.lower().endswith(".txt")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .eml and .txt email files are supported")

    content_bytes = await file.read()
    if len(content_bytes) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    parsed = parse_eml_content(content_bytes)
    try:
        res = pipeline.ingest_email(db, current_user, parsed, raw_eml_path=filename)
    except pipeline.IngestError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if not res.duplicate:
        pipeline.enqueue(background_tasks, [res.email.id], db=db)

    write_audit(db, current_user.id, "email.upload", f"Email #{res.email.id}", {"filename": filename, "duplicate": res.duplicate}, ip=request.client.host if request.client else None)
    return res.email


@router.post("/sync-inbox", dependencies=[Depends(upload_limiter)])
def sync_inbox(
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch new real e-mail from the configured IMAP mailbox and queue it for AI analysis."""
    try:
        stats = imap_sync.sync_mailbox(db, current_user, background_tasks)
    except imap_sync.ImapNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except imap_sync.ImapError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    write_audit(db, current_user.id, "email.sync_inbox", "IMAP", stats, ip=request.client.host if request.client else None)
    return stats


@router.post("/import-batch", response_model=List[schemas.EmailListItem], dependencies=[Depends(upload_limiter)])
def import_batch_emails(
    batch: schemas.EmailImportBatch,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(batch.emails) > settings.MAX_IMPORT_ROWS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Batch size exceeds maximum allowed ({settings.MAX_IMPORT_ROWS})")

    ingested_emails = []
    to_process = []
    for item in batch.emails:
        try:
            res = pipeline.ingest_email(db, current_user, item.model_dump())
            ingested_emails.append(res.email)
            if not res.duplicate:
                to_process.append(res.email.id)
        except pipeline.IngestError:
            continue

    if to_process:
        pipeline.enqueue(background_tasks, to_process, db=db)

    write_audit(db, current_user.id, "email.import_batch", f"Imported {len(ingested_emails)} emails", {"count": len(ingested_emails)}, ip=request.client.host if request.client else None)
    return [_format_email_item(e) for e in ingested_emails]


@router.post("/import-file", response_model=List[schemas.EmailListItem], dependencies=[Depends(upload_limiter)])
async def import_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    request: Request = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename = (file.filename or "").lower()
    content_bytes = await file.read()

    if not filename.endswith((".json", ".jsonl", ".csv")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only JSON, JSONL and CSV files are supported for file import")

    # parse_dataset_file handles Excel's UTF-8 BOM, case-insensitive headers and column aliases
    # (from/sender/email, body/text/content/message, ...), and reports per-row problems.
    try:
        items_to_ingest, row_errors = parse_dataset_file(filename, content_bytes, settings.MAX_IMPORT_ROWS)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not read the file. Check that it is valid CSV/JSON.")

    if not items_to_ingest:
        first = row_errors[0]["error"] if row_errors else "no rows found"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No emails could be imported ({first}). The file needs columns: subject, body (or text/content), and sender_email (or from/sender/email).",
        )

    ingested_emails = []
    to_process = []
    for item in items_to_ingest:
        try:
            res = pipeline.ingest_email(db, current_user, item)
            ingested_emails.append(res.email)
            if not res.duplicate:
                to_process.append(res.email.id)
        except pipeline.IngestError:
            continue

    if not ingested_emails:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No valid emails were found in the file (check sender addresses and bodies).")

    if to_process:
        pipeline.enqueue(background_tasks, to_process, db=db)

    write_audit(db, current_user.id, "email.import_file", f"Imported file {filename}", {"count": len(ingested_emails)}, ip=request.client.host if request.client else None)
    return [_format_email_item(e) for e in ingested_emails]


@router.get("/threads", response_model=List[schemas.EmailThreadListItem])
def list_email_threads(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t_rows = (
        db.query(models.EmailThread)
        .filter(models.EmailThread.user_id == current_user.id)
        .order_by(models.EmailThread.last_message_at.desc())
        .all()
    )
    res = []
    for t in t_rows:
        msg_count = db.query(models.Email).filter(models.Email.thread_id == t.id).count()
        res.append({
            "id": t.id,
            "subject": t.subject,
            "snippet": t.snippet,
            "unread_count": t.unread_count,
            "last_message_at": t.last_message_at,
            "message_count": msg_count,
        })
    return res


@router.get("/threads/{thread_id}", response_model=schemas.EmailThreadDetailResponse)
def get_email_thread_details(
    thread_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread_obj = (
        db.query(models.EmailThread)
        .filter(models.EmailThread.id == thread_id, models.EmailThread.user_id == current_user.id)
        .first()
    )
    if not thread_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    msgs = (
        db.query(models.Email)
        .filter(models.Email.thread_id == thread_id, models.Email.user_id == current_user.id)
        .order_by(models.Email.received_at.asc(), models.Email.id.asc())
        .all()
    )
    return {
        "id": thread_obj.id,
        "subject": thread_obj.subject,
        "snippet": thread_obj.snippet,
        "unread_count": thread_obj.unread_count,
        "last_message_at": thread_obj.last_message_at,
        "messages": [_format_email_item(m) for m in msgs],
    }


@router.get("", response_model=List[schemas.EmailListItem])
def list_emails(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    sentiment: Optional[str] = None,
    unread_only: bool = False,
    reply_required_only: bool = False,
    action_required_only: bool = False,
    starred_only: bool = False,
    archived: bool = False,
    search_text: Optional[str] = None,
    sender: Optional[str] = Query(None, max_length=200),
    date_preset: Optional[str] = Query(None, max_length=30),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    f = search.EmailFilters(
        q=search_text,
        categories=[category] if category else [],
        priorities=[priority] if priority else [],
        sentiments=[sentiment] if sentiment else [],
        is_read=False if unread_only else None,
        reply_required=True if reply_required_only else None,
        action_required=True if action_required_only else None,
        sender=sender or None,
        is_starred=True if starred_only else None,
        is_archived=archived,
    )
    if date_preset:
        try:
            f.date_from, f.date_to = search.resolve_date_range(date_preset)
        except search.SearchError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    query = search.apply_filters(search.base_query(db, current_user.id), f)
    emails = search.apply_sort(query, f).all()
    return [_format_email_item(e) for e in emails]


@router.get("/{email_id}", response_model=schemas.EmailDetailResponse)
def get_email_details(
    email_id: int,
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

    if not email_obj.is_read:
        email_obj.is_read = True
        threads.refresh_thread(db, email_obj.thread_id)
        db.commit()
        db.refresh(email_obj)

    return email_obj


@router.patch("/{email_id}/read", response_model=schemas.EmailListItem)
def mark_read(
    email_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_obj = db.query(models.Email).filter(models.Email.id == email_id, models.Email.user_id == current_user.id).first()
    if not email_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    email_obj.is_read = True
    threads.refresh_thread(db, email_obj.thread_id)
    db.commit()
    db.refresh(email_obj)
    return _format_email_item(email_obj)


@router.patch("/{email_id}/unread", response_model=schemas.EmailListItem)
def mark_unread(
    email_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_obj = db.query(models.Email).filter(models.Email.id == email_id, models.Email.user_id == current_user.id).first()
    if not email_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    email_obj.is_read = False
    threads.refresh_thread(db, email_obj.thread_id)
    db.commit()
    db.refresh(email_obj)
    return _format_email_item(email_obj)


@router.patch("/{email_id}/toggle-star")
def toggle_star(
    email_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_obj = db.query(models.Email).filter(models.Email.id == email_id, models.Email.user_id == current_user.id).first()
    if not email_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    email_obj.is_starred = not email_obj.is_starred
    db.commit()
    return {"is_starred": email_obj.is_starred}


@router.patch("/{email_id}/toggle-archive")
def toggle_archive(
    email_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_obj = db.query(models.Email).filter(models.Email.id == email_id, models.Email.user_id == current_user.id).first()
    if not email_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    email_obj.is_archived = not email_obj.is_archived
    db.commit()
    return {"is_archived": email_obj.is_archived}


@router.patch("/{email_id}/dismiss-reply")
def dismiss_reply(
    email_id: int,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_obj = db.query(models.Email).filter(models.Email.id == email_id, models.Email.user_id == current_user.id).first()
    if not email_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    email_obj.reply_status = "dismissed"
    db.commit()
    write_audit(db, current_user.id, "email.dismiss_reply", f"Email #{email_id}", ip=request.client.host if request.client else None)
    return {"reply_status": email_obj.reply_status}


@router.delete("/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_email(
    email_id: int,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_obj = db.query(models.Email).filter(models.Email.id == email_id, models.Email.user_id == current_user.id).first()
    if not email_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    thread_id = email_obj.thread_id
    db.delete(email_obj)
    db.flush()
    threads.refresh_thread(db, thread_id)
    db.commit()

    write_audit(db, current_user.id, "email.delete", f"Email #{email_id}", ip=request.client.host if request.client else None)
    return None
