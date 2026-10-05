from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.api.auth import get_current_user

router = APIRouter(tags=["Actions & Deadlines"])

@router.get("/actions", response_model=List[schemas.ActionItemSchema])
def list_action_items(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.ActionItem).filter(models.ActionItem.user_id == current_user.id).order_by(models.ActionItem.created_at.desc()).all()

@router.patch("/actions/{action_id}/toggle", response_model=schemas.ActionItemSchema)
def toggle_action_item(
    action_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    action = db.query(models.ActionItem).filter(
        models.ActionItem.id == action_id,
        models.ActionItem.user_id == current_user.id
    ).first()

    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")

    action.status = "completed" if action.status == "pending" else "pending"
    db.commit()
    db.refresh(action)
    return action

@router.get("/deadlines", response_model=List[schemas.DeadlineSchema])
def list_deadlines(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.Deadline).filter(models.Deadline.user_id == current_user.id).order_by(models.Deadline.due_date.asc()).all()

@router.patch("/deadlines/{deadline_id}/toggle", response_model=schemas.DeadlineSchema)
def toggle_deadline(
    deadline_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dl = db.query(models.Deadline).filter(
        models.Deadline.id == deadline_id,
        models.Deadline.user_id == current_user.id
    ).first()

    if not dl:
        raise HTTPException(status_code=404, detail="Deadline not found")

    dl.is_completed = not dl.is_completed
    db.commit()
    db.refresh(dl)
    return dl
