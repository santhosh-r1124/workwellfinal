from pydantic import BaseModel, Field

# Long enough for anything a person types about their week, short enough
# that an unbounded body cannot be turned into model spend - which on a
# free tier is the whole day's quota in one request.
MAX_MESSAGE_CHARS = 2000


class ChatMessageIn(BaseModel):
    employee_id: str
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class ChatMessageOut(BaseModel):
    session_id: str
    reply: str
    sources: list[dict] = []
    safety_flagged: bool = False
    # True when the reply is a deterministic fallback rather than model text,
    # so the UI can be honest about which one the employee is reading.
    degraded: bool = False
