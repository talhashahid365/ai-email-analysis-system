from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.config import settings
from app.database import get_db
from app.ratelimit import auth_limiter
from app.services.audit import write_audit
from app.services.mailer import send_system_email
from app.services.settings_store import get_setting

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    payload = security.decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    jti = payload.get("jti")
    if jti:
        revoked = db.query(models.RevokedToken).filter_by(jti=jti).first()
        if revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked (logged out)")

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    iat = payload.get("iat")
    if iat and user.password_changed_at:
        token_iat = datetime.fromtimestamp(iat, tz=timezone.utc)
        pwd_changed = user.password_changed_at.replace(tzinfo=timezone.utc) if user.password_changed_at.tzinfo is None else user.password_changed_at
        if token_iat < pwd_changed:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password changed; please log in again")

    return user


@router.post("/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED, dependencies=[Depends(auth_limiter)])
def register_user(user_in: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    allow_reg = get_setting(db, "allow_registration")
    if not allow_reg:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration is currently disabled")

    if len(user_in.password) < settings.PASSWORD_MIN_LENGTH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")

    email_clean = user_in.email.strip().lower()
    existing = db.query(models.User).filter(models.User.email == email_clean).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    role = "user"
    if email_clean in settings.admin_emails_list:
        role = "admin"
    elif settings.FIRST_USER_IS_ADMIN and db.query(models.User).count() == 0:
        role = "admin"

    require_verify = settings.REQUIRE_EMAIL_VERIFICATION
    new_user = models.User(
        email=email_clean,
        hashed_password=security.hash_password(user_in.password),
        full_name=user_in.full_name.strip(),
        company=user_in.company,
        job_title=user_in.job_title,
        role=role,
        is_active=True,
        is_verified=not require_verify,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    verify_token = None
    if require_verify:
        verify_token = security.create_token(new_user.id, token_type="verify")
        verify_link = f"{settings.FRONTEND_URL}/verify-email?token={verify_token}"
        send_system_email(new_user.email, "Verify Your Email Account", f"Hello {new_user.full_name},\n\nPlease verify your email address by clicking: {verify_link}")

    access_token = security.create_access_token(subject=new_user.id)
    write_audit(db, new_user.id, "auth.register", f"User {new_user.email}", {"role": new_user.role}, ip=request.client.host if request.client else None)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": new_user,
        "verify_token": verify_token if settings.EXPOSE_DEV_TOKENS else None
    }


@router.post("/login", response_model=schemas.Token, dependencies=[Depends(auth_limiter)])
def login_user(user_in: schemas.UserLogin, request: Request, db: Session = Depends(get_db)):
    email_clean = user_in.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email_clean).first()
    if not user or not security.verify_password(user_in.password, user.hashed_password):
        write_audit(db, None, "auth.login_failed", f"Email {email_clean}", ip=request.client.host if request.client else None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    # Recovery path: an ADMIN_EMAILS address is promoted at login ONLY when the system has no active admin.
    # Once an admin exists, roles are managed from the Users & RBAC tab and this never overrides their decisions.
    if (email_clean in settings.admin_emails_list and user.role != "admin"
            and db.query(models.User).filter(models.User.role == "admin", models.User.is_active == True).count() == 0):  # noqa: E712
        user.role = "admin"
        write_audit(db, user.id, "auth.role_promoted", f"{user.email} promoted to admin via ADMIN_EMAILS", ip=request.client.host if request.client else None)

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    access_token = security.create_access_token(subject=user.id)
    write_audit(db, user.id, "auth.login", f"User {user.email}", ip=request.client.host if request.client else None)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/token", response_model=schemas.Token, dependencies=[Depends(auth_limiter)])
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return login_user(schemas.UserLogin(email=form_data.username, password=form_data.password), request, db)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout_user(request: Request, token: str = Depends(oauth2_scheme), current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    payload = security.decode_access_token(token)
    if payload and "jti" in payload:
        exp_timestamp = payload.get("exp")
        exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) if exp_timestamp else datetime.now(timezone.utc)
        db.add(models.RevokedToken(jti=payload["jti"], expires_at=exp_dt))
        db.commit()

    write_audit(db, current_user.id, "auth.logout", f"User {current_user.email}", ip=request.client.host if request.client else None)
    return {"message": "Successfully logged out"}


@router.post("/verify-email")
def verify_email(req: schemas.EmailVerifyRequest, request: Request, db: Session = Depends(get_db)):
    payload = security.decode_token(req.token, expected_type="verify")
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")

    user_id = int(payload["sub"])
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_verified = True
    db.commit()
    write_audit(db, user.id, "auth.verify_email", f"User {user.email}", ip=request.client.host if request.client else None)
    return {"message": "Email verified successfully"}


@router.post("/forgot-password", dependencies=[Depends(auth_limiter)])
def forgot_password(req: schemas.PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    email_clean = req.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email_clean).first()
    if not user:
        return {"message": "If that email is registered, password reset instructions have been sent."}

    fingerprint = security.password_fingerprint(user.hashed_password)
    reset_token = security.create_token(user.id, token_type="reset", extra={"fp": fingerprint})
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    # The reset link is delivered ONLY by email. It is never returned by the API or printed to the console.
    send_system_email(
        user.email,
        "Password Reset Request",
        f"Hello {user.full_name},\n\nClick the following link to reset your password "
        f"(valid for {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes):\n{reset_link}\n\n"
        "If you did not request this, you can ignore this email.",
        sensitive=True,
    )
    write_audit(db, user.id, "auth.forgot_password", f"User {user.email}", ip=request.client.host if request.client else None)

    return {"message": "If that email is registered, password reset instructions have been sent."}


@router.post("/reset-password", dependencies=[Depends(auth_limiter)])
def reset_password(req: schemas.PasswordResetConfirm, request: Request, db: Session = Depends(get_db)):
    payload = security.decode_token(req.token, expected_type="reset")
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user_id = int(payload["sub"])
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    expected_fp = security.password_fingerprint(user.hashed_password)
    if payload.get("fp") != expected_fp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has already been used or is invalid")

    if len(req.new_password) < settings.PASSWORD_MIN_LENGTH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")

    user.hashed_password = security.hash_password(req.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    db.commit()

    write_audit(db, user.id, "auth.reset_password", f"User {user.email}", ip=request.client.host if request.client else None)
    return {"message": "Password reset successfully. You can now log in with your new password."}


@router.get("/me", response_model=schemas.UserResponse)
def get_user_profile(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=schemas.UserResponse)
def update_user_profile(user_update: schemas.ProfileUpdate, request: Request, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name.strip()
    if user_update.company is not None:
        current_user.company = user_update.company
    if user_update.job_title is not None:
        current_user.job_title = user_update.job_title

    db.commit()
    db.refresh(current_user)
    write_audit(db, current_user.id, "auth.update_profile", f"User {current_user.email}", ip=request.client.host if request.client else None)
    return current_user


@router.get("/export-data", tags=["Auth"])
def export_my_data(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """GDPR-compliant: export all personal data for the authenticated user."""
    import datetime
    from fastapi.responses import Response
    import json as json_module

    emails = db.query(models.Email).filter(models.Email.user_id == current_user.id).all()
    action_items = db.query(models.ActionItem).filter(models.ActionItem.user_id == current_user.id).all()
    deadlines = db.query(models.Deadline).filter(models.Deadline.user_id == current_user.id).all()
    notifications = db.query(models.Notification).filter(models.Notification.user_id == current_user.id).count()

    export = {
        "exported_at": datetime.datetime.utcnow().isoformat() + "Z",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "company": current_user.company,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        "emails_count": len(emails),
        "emails": [
            {
                "id": e.id,
                "sender_email": e.sender_email,
                "sender_name": e.sender_name,
                "subject": e.subject,
                "received_at": e.received_at.isoformat() if e.received_at else None,
                "category": e.ai_analysis.category if e.ai_analysis else None,
                "priority": e.ai_analysis.priority if e.ai_analysis else None,
            }
            for e in emails
        ],
        "action_items": [
            {"id": a.id, "task": a.task, "status": a.status, "due_date": a.due_date, "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in action_items
        ],
        "deadlines": [
            {"id": d.id, "title": d.title, "due_date": d.due_date, "is_completed": d.is_completed}
            for d in deadlines
        ],
        "notification_count": notifications,
    }

    content = json_module.dumps(export, indent=2, default=str)
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="mailnexa-export-user-{current_user.id}.json"'
        },
    )
