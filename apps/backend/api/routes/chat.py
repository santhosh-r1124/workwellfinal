from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_current_user, get_db
from apps.backend.models import User
from apps.backend.services import chat_service
from shared.schemas.chat import ChatMessageIn, ChatMessageOut

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatMessageOut)
def chat(
    payload: ChatMessageIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    # Always chat as the authenticated employee - payload.employee_id is
    # informational only and never trusted for authorization.
    result = chat_service.handle_message(db, user.id, payload.session_id, payload.message)
    return result
