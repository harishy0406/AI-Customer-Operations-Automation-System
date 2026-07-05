import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from src.api.database import get_db
from src.api.dependencies import get_current_user_dep
from src.api.models.conversation import Message
from src.api.schemas.query import QueryRequest
from src.api.services.cache_service import SemanticCache
from src.api.services.generation_service import generate_response, get_or_create_conversation, get_conversation_history, build_prompt
from src.api.services.hallucination_service import score_groundedness, determine_action
from src.api.services.retrieval_service import hybrid_search, rerank
from src.common.logger import get_logger
from src.ingestion.embedder import EmbeddingClient

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["query"])


@router.post("/query")
async def query_endpoint(
    req: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_dep),
):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["sub"]
    request_id = str(uuid.uuid4())

    conv = await get_or_create_conversation(db, tenant_id, req.conversation_id)
    history = await get_conversation_history(db, conv.id, req.max_history_turns)

    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        role="user",
        content=req.query,
    )
    db.add(user_msg)
    await db.flush()

    embedder = EmbeddingClient()

    try:
        cache = SemanticCache(db)  # placeholder — will wire Redis via app state
    except Exception:
        cache = None

    query_embedding = await embedder.embed(req.query)
    cached_response = None
    if cache:
        cached_response = await cache.get(query_embedding, tenant_id, 0)

    if cached_response:
        logger.info("Cache hit", extra={"request_id": request_id, "tenant_id": tenant_id})
        citations = cached_response.get("citations", [])
        groundedness = cached_response.get("groundedness_score")
        cached_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            role="assistant",
            content=cached_response["answer"],
            citations=json.dumps(citations),
            groundedness_score=groundedness,
            cached=True,
        )
        db.add(cached_msg)
        await db.commit()

        async def stream_cached():
            yield json.dumps({
                "answer": cached_response["answer"],
                "conversation_id": conv.id,
                "citations": citations,
                "groundedness_score": groundedness,
                "cached": True,
                "request_id": request_id,
            })

        return EventSourceResponse(stream_cached())

    logger.info("Cache miss, running RAG pipeline", extra={"request_id": request_id, "tenant_id": tenant_id})

    retrieved = await hybrid_search(db, req.query, tenant_id, embedder)
    reranked = await rerank(retrieved)

    async def event_generator():
        answer_parts = []
        citations_data = [
            {"source_id": c.document_id, "chunk_content": c.content[:200], "score": c.score}
            for c in reranked
        ]

        _, context_str = build_prompt(req.query, reranked, history)

        async for chunk in generate_response(req.query, reranked, conv.id, db, history=history):
            answer_parts.append(chunk)
            yield {"event": "token", "data": chunk}

        full_answer = "".join(answer_parts)

        hall_result = await score_groundedness(full_answer, context_str)
        action = determine_action(hall_result["score"])

        final = {
            "answer": full_answer,
            "conversation_id": conv.id,
            "citations": citations_data,
            "groundedness_score": hall_result["score"],
            "cached": False,
            "request_id": request_id,
            "action": action,
        }

        if cache:
            await cache.set(query_embedding, final, tenant_id, 0)

        yield {"event": "complete", "data": json.dumps(final)}

    return EventSourceResponse(event_generator())
