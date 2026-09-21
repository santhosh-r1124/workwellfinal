from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_current_user, get_db
from apps.backend.services import rag_service
from shared.schemas.rag import RagQueryRequest, RagQueryResponse

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=RagQueryResponse)
def query(
    payload: RagQueryRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)
):
    result = rag_service.answer_query(db, payload.query, payload.category, payload.top_k)
    return result
