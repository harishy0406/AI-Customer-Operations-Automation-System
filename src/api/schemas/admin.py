from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    total_queries: int
    deflection_rate: float
    hallucination_rate: float
    cache_hit_rate: float
    avg_latency_ms: float
    avg_cost_per_query: float


class EvalRunResponse(BaseModel):
    id: str
    prompt_version: str
    metrics: dict
    created_at: str


class IngestionResponse(BaseModel):
    document_id: str
    status: str
    chunks_created: int
