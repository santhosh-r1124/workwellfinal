from pydantic import BaseModel


class RagQueryRequest(BaseModel):
    query: str
    category: str | None = None
    top_k: int = 4


class RagSource(BaseModel):
    title: str
    url: str | None = None
    category: str | None = None


class RagQueryResponse(BaseModel):
    answer: str
    sources: list[RagSource]
