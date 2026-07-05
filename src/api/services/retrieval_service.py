import json
import math

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

from src.api.models.chunk import Chunk
from src.api.config import get_settings
from src.ingestion.embedder import EmbeddingClient

settings = get_settings()


class ChunkResult:
    def __init__(self, chunk_id: str, content: str, score: float, source_type: str = "", document_id: str = ""):
        self.chunk_id = chunk_id
        self.content = content
        self.score = score
        self.source_type = source_type
        self.document_id = document_id


async def hybrid_search(
    db: AsyncSession,
    query_text: str,
    tenant_id: str,
    embedder: EmbeddingClient,
    top_k: int = 20,
) -> list[ChunkResult]:
    query_emb = await embedder.embed(query_text)
    vector_results = await _vector_search(db, query_emb, tenant_id, top_k)
    keyword_results = await _keyword_search(db, query_text, tenant_id, top_k)
    return _reciprocal_rank_fusion(vector_results, keyword_results, top_k)


async def _vector_search(
    db: AsyncSession, query_emb: list[float], tenant_id: str, top_k: int
) -> list[ChunkResult]:
    stmt = (
        select(Chunk)
        .where(Chunk.tenant_id == tenant_id, Chunk.embedding.isnot(None))
        .order_by(Chunk.embedding.cosine_distance(Vector(query_emb)))  # type: ignore
        .limit(top_k)
    )
    result = await db.execute(stmt)
    chunks = result.scalars().all()
    return [
        ChunkResult(
            chunk_id=c.id,
            content=c.content,
            score=1.0,  # will be re-ranked
            document_id=c.document_id,
        )
        for c in chunks
    ]


async def _keyword_search(
    db: AsyncSession, query_text: str, tenant_id: str, top_k: int
) -> list[ChunkResult]:
    tsquery = " & ".join(query_text.split()[:10])
    if not tsquery:
        return []
    stmt = (
        select(Chunk)
        .where(
            Chunk.tenant_id == tenant_id,
            text("to_tsvector('english', content) @@ to_tsquery('english', :q)"),
        )
        .params(q=tsquery)
        .limit(top_k)
    )
    try:
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        return [
            ChunkResult(chunk_id=c.id, content=c.content, score=0.8, document_id=c.document_id)
            for c in chunks
        ]
    except Exception:
        return []


def _reciprocal_rank_fusion(
    vector_results: list[ChunkResult],
    keyword_results: list[ChunkResult],
    top_k: int,
    k: int = 60,
) -> list[ChunkResult]:
    scores: dict[str, float] = {}
    results_map: dict[str, ChunkResult] = {}

    for rank, r in enumerate(vector_results):
        scores[r.chunk_id] = scores.get(r.chunk_id, 0) + 1.0 / (k + rank)
        results_map[r.chunk_id] = r

    for rank, r in enumerate(keyword_results):
        scores[r.chunk_id] = scores.get(r.chunk_id, 0) + 1.0 / (k + rank)
        results_map[r.chunk_id] = r

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]
    for r in results_map.values():
        r.score = scores.get(r.chunk_id, 0)
    return [results_map[cid] for cid in sorted_ids]


async def rerank(
    chunks: list[ChunkResult], rerank_top_k: int = 5
) -> list[ChunkResult]:
    valid = [c for c in chunks if c.content.strip()]
    valid.sort(key=lambda x: x.score, reverse=True)
    return valid[:rerank_top_k]
