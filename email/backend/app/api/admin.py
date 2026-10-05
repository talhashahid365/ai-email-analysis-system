from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.auth import get_current_user
from app.database import get_db
from app.services import bootstrap, pipeline, settings_store
from app.services.audit import write_audit

router = APIRouter(prefix="/admin", tags=["Admin Portal"])


def require_admin_or_manager(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or manager access required")
    return current_user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# --- System Stats & AI Logs ---
@router.get("/stats", response_model=schemas.AdminStatsResponse)
def get_system_stats(
    admin_user: models.User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db),
):
    total_users = db.query(models.User).count()
    active_users = db.query(models.User).filter(models.User.is_active == True).count()
    total_emails = db.query(models.Email).count()
    total_threads = db.query(models.EmailThread).count()
    total_ai_analyses = db.query(models.AIAnalysis).count()
    total_replies = db.query(models.AIReply).count()
    total_ai_logs = db.query(models.AILog).count()
    ai_errors = db.query(models.AILog).filter(models.AILog.success == False).count()
    effective_prov = settings_store.effective_provider(db) or "heuristic"

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_emails": total_emails,
        "total_threads": total_threads,
        "total_ai_analyses": total_ai_analyses,
        "total_smart_replies": total_replies,
        "total_ai_logs": total_ai_logs,
        "ai_errors_count": ai_errors,
        "effective_ai_provider": effective_prov,
    }


# --- Email processing & AI usage ---
@router.get("/processing", response_model=schemas.AdminProcessingResponse)
def get_processing_overview(
    admin_user: models.User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db),
):
    """Counts of emails per processing status plus the most recent failures."""
    base = db.query(models.Email).filter(models.Email.is_outbound == False, models.Email.deleted_at.is_(None))  # noqa: E712
    counts = dict(base.with_entities(models.Email.processing_status, func.count(models.Email.id)).group_by(models.Email.processing_status).all())
    failed = (base.filter(models.Email.processing_status == "failed")
              .order_by(models.Email.id.desc()).limit(50).all())
    return {
        "by_status": {k or "unknown": v for k, v in counts.items()},
        "failed": [
            {"id": e.id, "user_id": e.user_id, "processing_error": e.processing_error,
             "retry_count": e.retry_count or 0, "received_at": e.received_at}
            for e in failed
        ],
    }


def _usage_rows(db: Session, column) -> List[dict]:
    rows = (
        db.query(
            column,
            func.count(models.AILog.id),
            func.sum(case((models.AILog.success == False, 1), else_=0)),  # noqa: E712
            func.sum(case((models.AILog.fallback_used == True, 1), else_=0)),  # noqa: E712
            func.avg(models.AILog.latency_ms),
        )
        .group_by(column)
        .order_by(func.count(models.AILog.id).desc())
        .all()
    )
    return [
        {"name": r[0] or "unknown", "calls": int(r[1]), "failures": int(r[2] or 0),
         "fallbacks": int(r[3] or 0), "avg_latency_ms": int(r[4] or 0)}
        for r in rows
    ]


@router.get("/usage", response_model=schemas.AdminUsageResponse)
def get_ai_usage(
    admin_user: models.User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db),
):
    """AI usage statistics from the AI log: volume, error rate, latency by operation and provider."""
    from app.timeutil import utcnow

    total = db.query(models.AILog).count()
    failed = db.query(models.AILog).filter(models.AILog.success == False).count()  # noqa: E712
    since = utcnow() - timedelta(hours=24)
    last_24h = db.query(models.AILog).filter(models.AILog.created_at >= since).count()
    return {
        "total_calls": total,
        "failed_calls": failed,
        "error_rate": round(failed / total, 4) if total else 0.0,
        "calls_last_24h": last_24h,
        "by_operation": _usage_rows(db, models.AILog.operation),
        "by_provider": _usage_rows(db, models.AILog.provider),
    }


# --- Reprocess / retry ---
@router.post("/emails/{email_id}/reprocess")
def admin_reprocess_email(
    email_id: int,
    req: Request,
    background_tasks: BackgroundTasks,
    admin_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Queue one email (any user's) for AI re-processing."""
    email = db.query(models.Email).filter(models.Email.id == email_id, models.Email.is_outbound == False).first()  # noqa: E712
    if not email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
    email.processing_status, email.retry_count, email.processing_error = "queued", 0, None
    db.commit()
    mode = pipeline.enqueue(background_tasks, [email.id], notify=False)
    write_audit(db, admin_user.id, "admin.reprocess_email", f"Email #{email_id}", {"mode": mode}, ip=req.client.host if req.client else None)
    return {"queued": 1, "mode": mode}


@router.post("/emails/retry-failed")
def admin_retry_failed(
    req: Request,
    background_tasks: BackgroundTasks,
    limit: int = 100,
    admin_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Re-queue emails whose AI processing failed (status 'failed'), oldest first."""
    limit = max(1, min(limit, 500))
    rows = (db.query(models.Email).filter(models.Email.processing_status == "failed", models.Email.is_outbound == False)  # noqa: E712
            .order_by(models.Email.id.asc()).limit(limit).all())
    for e in rows:
        e.processing_status, e.retry_count, e.processing_error = "queued", 0, None
    db.commit()
    ids = [e.id for e in rows]
    mode = pipeline.enqueue(background_tasks, ids, notify=False)
    write_audit(db, admin_user.id, "admin.retry_failed", "emails", {"count": len(ids), "mode": mode}, ip=req.client.host if req.client else None)
    return {"queued": len(ids), "mode": mode}


@router.get("/ai-logs", response_model=List[schemas.AILogResponse])
def get_ai_logs(
    limit: int = 100,
    admin_user: models.User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db),
):
    return db.query(models.AILog).order_by(models.AILog.created_at.desc()).limit(limit).all()


@router.get("/ai-errors", response_model=List[schemas.AILogResponse])
def get_ai_errors(
    limit: int = 100,
    admin_user: models.User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.AILog)
        .filter(models.AILog.success == False)
        .order_by(models.AILog.created_at.desc())
        .limit(limit)
        .all()
    )


# --- Category Management ---
@router.get("/categories", response_model=List[schemas.CategorySchema])
def list_categories(
    admin_user: models.User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db),
):
    bootstrap.seed_defaults(db)
    return db.query(models.Category).order_by(models.Category.id).all()


@router.post("/categories", response_model=schemas.CategorySchema, status_code=status.HTTP_201_CREATED)
def create_category(
    cat_in: schemas.CategoryCreate,
    request: Request,
    admin_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    name_clean = cat_in.name.strip()
    existing = db.query(models.Category).filter(models.Category.name.ilike(name_clean)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category name already exists")

    cat = models.Category(
        name=name_clean,
        description=cat_in.description,
        color=cat_in.color or "#64748b",
        is_active=cat_in.is_active,
        is_system=False,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    write_audit(db, admin_user.id, "admin.create_category", f"Category {cat.name}", ip=request.client.host if request.client else None)
    return cat


@router.patch("/categories/{category_id}", response_model=schemas.CategorySchema)
def update_category(
    category_id: int,
    cat_in: schemas.CategoryUpdate,
    request: Request,
    admin_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cat = db.get(models.Category, category_id)
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if cat_in.description is not None:
        cat.description = cat_in.description
    if cat_in.color is not None:
        cat.color = cat_in.color
    if cat_in.is_active is not None:
        cat.is_active = cat_in.is_active

    db.commit()
    db.refresh(cat)
    write_audit(db, admin_user.id, "admin.update_category", f"Category {cat.name}", ip=request.client.host if request.client else None)
    return cat


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    request: Request,
    admin_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cat = db.get(models.Category, category_id)
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if cat.is_system:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="System default categories cannot be deleted")

    name = cat.name
    db.delete(cat)
    db.commit()
    write_audit(db, admin_user.id, "admin.delete_category", f"Category {name}", ip=request.client.host if request.client else None)
    return None


# --- System Settings ---
@router.get("/settings", response_model=List[schemas.SystemSettingSchema])
def get_system_settings(
    admin_user: models.User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db),
):
    all_s = settings_store.get_all_settings(db)
    return [{"key": k, **v} for k, v in all_s.items()]


@router.put("/settings/{key}", response_model=schemas.SystemSettingSchema)
def update_system_setting(
    key: str,
    update_in: schemas.SystemSettingUpdate,
    request: Request,
    admin_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        val = settings_store.set_setting(db, key, update_in.value)
        write_audit(db, admin_user.id, "admin.update_setting", f"Setting {key}", {"value": val}, ip=request.client.host if request.client else None)
        all_s = settings_store.get_all_settings(db)
        return {"key": key, **all_s[key]}
    except settings_store.SettingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/settings/reset/{key}", response_model=schemas.SystemSettingSchema)
def reset_system_setting(
    key: str,
    request: Request,
    admin_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        settings_store.reset_setting(db, key)
        write_audit(db, admin_user.id, "admin.reset_setting", f"Setting {key}", ip=request.client.host if request.client else None)
        all_s = settings_store.get_all_settings(db)
        return {"key": key, **all_s[key]}
    except settings_store.SettingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# --- Users Management ---
def _active_admin_count(db: Session) -> int:
    return db.query(models.User).filter(models.User.role == "admin", models.User.is_active == True).count()  # noqa: E712


@router.get("/users", response_model=List[schemas.UserResponse])
def admin_list_users(
    admin_user: models.User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db),
):
    return db.query(models.User).order_by(models.User.id).all()


@router.patch("/users/{user_id}/role", response_model=schemas.UserResponse)
def update_user_role(
    user_id: int,
    role_in: schemas.UserRoleUpdate,
    request: Request,
    admin_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if role_in.role not in ("user", "manager", "admin"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role. Must be 'user', 'manager', or 'admin'")

    target_user = db.get(models.User, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # An admin can promote or demote anyone, but the system must always keep at least one active admin.
    if target_user.role == "admin" and role_in.role != "admin" and target_user.is_active and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot remove the last admin. Make another user admin first.")

    target_user.role = role_in.role
    db.commit()
    db.refresh(target_user)

    write_audit(db, admin_user.id, "admin.update_user_role", f"User {target_user.email}", {"new_role": role_in.role}, ip=request.client.host if request.client else None)
    return target_user


@router.patch("/users/{user_id}/status", response_model=schemas.UserResponse)
def update_user_status(
    user_id: int,
    status_in: schemas.UserStatusUpdate,
    request: Request,
    admin_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target_user = db.get(models.User, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target_user.id == admin_user.id and not status_in.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account")

    if (not status_in.is_active) and target_user.role == "admin" and target_user.is_active and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot suspend the last admin. Make another user admin first.")

    target_user.is_active = status_in.is_active
    db.commit()
    db.refresh(target_user)

    write_audit(db, admin_user.id, "admin.update_user_status", f"User {target_user.email}", {"is_active": status_in.is_active}, ip=request.client.host if request.client else None)
    return target_user


# --- Audit Logs ---
@router.get("/audit-logs", response_model=List[schemas.AuditLogResponse])
def get_audit_logs(
    limit: int = 100,
    admin_user: models.User = Depends(require_admin_or_manager),
    db: Session = Depends(get_db),
):
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(limit).all()
