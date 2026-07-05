import json
import uuid
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.config import get_settings
from src.api.models.conversation import Conversation, Message
from src.api.services.retrieval_service import ChunkResult
from src.ingestion.embedder import EmbeddingClient
from src.llm.providers import LLMClient, get_llm_client

settings = get_settings()

SYSTEM_PROMPT_TEMPLATE = """You are a helpful customer support assistant. Answer the customer's question based ONLY on the provided context. If the context does not contain enough information to answer, say so honestly.

Guidelines:
- Cite sources using [Source: document_id] markers when referencing specific information.
- Do not make up facts or use information outside the provided context.
- Be concise but thorough.
- If you cannot find relevant information, say: "I don't have enough information to answer that question accurately."

Context:
{context}

Conversation History:
{history}
"""


def build_prompt(
    query: str,
    context_chunks: list[ChunkResult],
    history: list[dict] | None = None,
) -> tuple[str, str]:
    context_parts = []
    for i, chunk in enumerate(context_chunks):
        context_parts.append(f"[Source: {chunk.document_id}] {chunk.content}")
    context_str = "\n\n".join(context_parts)

    history_str = ""
    if history:
        history_str = "\n".join(
            f"{'Customer' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in history[-5:]
        )

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        context=context_str,
        history=history_str or "No prior conversation history.",
    )
    return system_prompt, context_str


async def generate_response(
    query: str,
    context_chunks: list[ChunkResult],
    conversation_id: str,
    db: AsyncSession,
    llm_client: LLMClient | None = None,
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    if llm_client is None:
        llm_client = get_llm_client()

    system_prompt, context_str = build_prompt(query, context_chunks, history)
    citations = [
        {"source_id": c.document_id, "chunk_content": c.content[:200], "score": c.score}
        for c in context_chunks[:5]
    ]

    full_response = ""
    async for chunk in llm_client.stream(system_prompt, query):
        full_response += chunk
        yield chunk

    msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="assistant",
        content=full_response,
        citations=json.dumps(citations),
        groundedness_score=None,
        cached=False,
    )
    db.add(msg)


async def get_or_create_conversation(
    db: AsyncSession, tenant_id: str, conversation_id: str | None = None, customer_ref: str | None = None
) -> Conversation:
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.tenant_id == tenant_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv

    conv = Conversation(
        id=conversation_id or str(uuid.uuid4()),
        tenant_id=tenant_id,
        customer_ref=customer_ref,
    )
    db.add(conv)
    await db.flush()
    return conv


async def get_conversation_history(
    db: AsyncSession, conversation_id: str, max_turns: int = 5
) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.role.in_(["user", "assistant"]))
        .order_by(Message.created_at.desc())
        .limit(max_turns * 2)
    )
    messages = result.scalars().all()
    history = [
        {"role": m.role, "content": m.content}
        for m in reversed(messages)
    ]
    return history
