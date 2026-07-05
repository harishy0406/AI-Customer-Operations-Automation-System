from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    conversation_id: str | None = None
    max_history_turns: int = 5


class Citation(BaseModel):
    source_id: str
    chunk_content: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    conversation_id: str
    citations: list[Citation]
    groundedness_score: float | None = None
    cached: bool = False
    request_id: str = ""
