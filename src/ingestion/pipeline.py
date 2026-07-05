from typing import BinaryIO

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services.ingestion_service import ingest_document
from src.ingestion.embedder import EmbeddingClient


async def run_ingestion_pipeline(
    db: AsyncSession,
    tenant_id: str,
    source_type: str,
    file_stream: BinaryIO,
    filename: str,
) -> tuple[str, int]:
    embedder = EmbeddingClient()
    doc_id, chunk_count = await ingest_document(db, tenant_id, source_type, file_stream, filename, embedder)

    from src.api.services.cache_service import SemanticCache
    from src.api.models.tenant import Tenant
    from sqlalchemy import select

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one()

    from src.api.config import get_settings
    settings = get_settings()

    from redis.asyncio import Redis
    redis = Redis.from_url(settings.REDIS_URL)
    cache = SemanticCache(redis)
    await cache.invalidate_tenant(tenant_id, tenant.kb_version)
    await redis.close()

    return doc_id, chunk_count
