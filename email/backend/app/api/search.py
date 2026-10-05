from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.auth import get_current_user
from app.database import get_db
from app.ratelimit import ai_limiter
from app.services import rag_assistant, search
from app.services.audit import write_audit
from app.api.emails import _format_email_item

router = APIRouter(prefix="/search", tags=["Search & AI Assistant"])


@router.post("/ai", response_model=schemas.AIAssistantResponse, dependencies=[Depends(ai_limiter)])
def query_ai_assistant(
    query_in: schemas.AIAssistantQuery,
    req_http: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not query_in.question.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty")

    conv = None
    if query_in.conversation_id:
        conv = (
            db.query(models.AIConversation)
            .filter(
                models.AIConversation.id == query_in.conversation_id,
                models.AIConversation.user_id == current_user.id,
            )
            .first()
        )

    if not conv:
        conv = models.AIConversation(
            user_id=current_user.id,
            title=query_in.question[:40].strip() or "New Conversation",
        )
        db.add(conv)
        db.flush()

    user_msg = models.AIMessage(
        conversation_id=conv.id,
        sender="user",
        content=query_in.question.strip(),
    )
    db.add(user_msg)
    db.flush()

    answer, cited_emails, applied_filters = rag_assistant.process_assistant_query(
        question=query_in.question,
        db=db,
        user_id=current_user.id,
        conversation_id=conv.id,
    )
    cited_ids = [e.id for e in cited_emails]

    assistant_msg = models.AIMessage(
        conversation_id=conv.id,
        sender="assistant",
        content=answer,
        cited_email_ids=cited_ids,
        filters=applied_filters,
    )
    db.add(assistant_msg)
    db.commit()

    write_audit(
        db,
        current_user.id,
        "search.ai_assistant",
        f"Conversation #{conv.id}",
        {"question": query_in.question[:100], "cited_count": len(cited_emails)},
        ip=req_http.client.host if req_http.client else None,
    )

    return {
        "answer": answer,
        "conversation_id": conv.id,
        "cited_emails": [_format_email_item(e) for e in cited_emails],
        "filters": applied_filters,
    }


@router.get("", response_model=List[schemas.EmailListItem])
def search_emails(
    q: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    sentiment: Optional[str] = None,
    unread_only: bool = False,
    reply_required_only: bool = False,
    starred_only: bool = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    f = search.EmailFilters(
        q=q,
        categories=[category] if category else [],
        priorities=[priority] if priority else [],
        sentiments=[sentiment] if sentiment else [],
        is_read=False if unread_only else None,
        reply_required=True if reply_required_only else None,
        is_starred=True if starred_only else None,
    )
    emails, _ = search.run_search(db, current_user.id, f)
    return [_format_email_item(e) for e in emails]


@router.post("/structured", response_model=List[schemas.EmailListItem])
def structured_search(
    tree: Dict[str, Any],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        emails, _ = search.run_structured(db, current_user.id, tree)
        return [_format_email_item(e) for e in emails]
    except search.SearchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
