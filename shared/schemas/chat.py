from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    employee_id: str
    session_id: str | None = None
    message: str


class ChatMessageOut(BaseModel):
    session_id: str
    reply: str
    sources: list[dict] = []
    safety_flagged: bool = False
    # True when the reply is a deterministic fallback rather than model text,
    # so the UI can be honest about which one the employee is reading.
    degraded: bool = False
