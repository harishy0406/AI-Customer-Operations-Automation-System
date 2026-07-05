from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.dependencies import get_current_user_dep, require_admin
from src.api.models.audit import AuditLog
from src.api.models.conversation import Message
from src.api.schemas.admin import DashboardMetrics, IngestionResponse
from src.common.logger import get_logger
from src.ingestion.pipeline import run_ingestion_pipeline

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.post("/documents", response_model=IngestionResponse)
async def upload_document(
    file: UploadFile = File(...),
    source_type: str = Form("auto"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    tenant_id = current_user["tenant_id"]

    if source_type == "auto":
        ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else "txt"
        source_type = {"pdf": "pdf", "md": "markdown", "html": "html", "csv": "csv", "txt": "markdown"}.get(ext, "markdown")

    content = await file.read()
    import io
    stream = io.BytesIO(content)

    doc_id, chunk_count = await run_ingestion_pipeline(db, tenant_id, source_type, stream, file.filename or "unknown")

    db.add(AuditLog(
        tenant_id=tenant_id,
        actor_id=current_user["sub"],
        action="document_upload",
        payload=f'{{"document_id": "{doc_id}", "chunks": {chunk_count}}}',
    ))
    await db.flush()

    return IngestionResponse(document_id=doc_id, status="success", chunks_created=chunk_count)


@router.get("/dashboard/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    tenant_id = current_user["tenant_id"]

    result = await db.execute(
        select(func.count()).select_from(Message).where(Message.role == "assistant")
    )
    total_queries = result.scalar() or 0

    result = await db.execute(
        select(func.count()).select_from(Message).where(
            Message.role == "assistant",
            Message.groundedness_score >= 0.9,
        )
    )
    safe_count = result.scalar() or 0

    result = await db.execute(
        select(func.avg(Message.groundedness_score)).where(Message.role == "assistant")
    )
    avg_groundedness = result.scalar() or 0.0

    result = await db.execute(
        select(func.count()).select_from(Message).where(Message.cached.is_(True))
    )
    cached_count = result.scalar() or 0

    return DashboardMetrics(
        total_queries=total_queries,
        deflection_rate=safe_count / max(total_queries, 1),
        hallucination_rate=1.0 - (avg_groundedness or 0),
        cache_hit_rate=cached_count / max(total_queries, 1),
        avg_latency_ms=0.0,
        avg_cost_per_query=0.0,
    )
