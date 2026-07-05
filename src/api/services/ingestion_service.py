import uuid
import hashlib
from typing import BinaryIO

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.document import Document
from src.api.models.chunk import Chunk
from src.api.models.tenant import Tenant
from src.ingestion.extractors import extract_text
from src.ingestion.chunker import chunk_text
from src.ingestion.embedder import EmbeddingClient


async def ingest_document(
    db: AsyncSession,
    tenant_id: str,
    source_type: str,
    file_stream: BinaryIO,
    filename: str,
    embedder: EmbeddingClient,
) -> tuple[str, int]:
    raw_text = extract_text(file_stream, source_type)
    file_content = raw_text.encode("utf-8")
    file_hash = hashlib.sha256(file_content).hexdigest()

    existing = await db.execute(
        select(Document).where(
            Document.tenant_id == tenant_id,
            Document.uri == filename,
            Document.content_hash == file_hash,
        )
    )
    if existing.scalar_one_or_none():
        doc = existing.scalar_one()
        return doc.id, 0

    doc = Document(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        source_type=source_type,
        uri=filename,
        content_hash=file_hash,
    )
    db.add(doc)
    await db.flush()

    chunks = chunk_text(raw_text, meta={"document_id": doc.id, "source_type": source_type})
    chunk_objects = []
    texts_for_embedding = []

    for i, c in enumerate(chunks):
        cid = str(uuid.uuid4())
        chunk_objects.append(
            Chunk(
                id=cid,
                document_id=doc.id,
                tenant_id=tenant_id,
                content=c["content"],
                metadata_json=str(c["metadata"]),
            )
        )
        texts_for_embedding.append((cid, c["content"]))

    await db.flush()

    embeddings = await embedder.embed_batch([t[1] for t in texts_for_embedding])
    for (cid, _), emb in zip(texts_for_embedding, embeddings):
        await db.execute(
            select(Chunk).where(Chunk.id == cid)  # just to validate
        )
        stmt = (
            select(Chunk).where(Chunk.id == cid)
        )
        result = await db.execute(stmt)
        chunk = result.scalar_one()
        chunk.embedding = emb

    await db.flush()

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one()
    tenant.kb_version = Tenant.kb_version + 1  # type: ignore

    return doc.id, len(chunk_objects)
