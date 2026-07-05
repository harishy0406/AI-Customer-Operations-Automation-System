from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["metrics"])

QUERY_COUNT = Counter("queries_total", "Total number of queries", ["tenant_id", "status"])
CACHE_HITS = Counter("cache_hits_total", "Total cache hits", ["tenant_id"])
CACHE_MISSES = Counter("cache_misses_total", "Total cache misses", ["tenant_id"])
LLM_LATENCY = Histogram("llm_latency_seconds", "LLM call latency", buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0])
QUERY_LATENCY = Histogram("query_latency_seconds", "Total query latency", buckets=[0.5, 1.0, 2.0, 5.0, 8.0, 15.0])


@router.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest(REGISTRY))
