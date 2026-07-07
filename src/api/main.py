from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from src.api.config import get_settings
from src.api.database import engine
from src.api.routers import auth, query, admin, metrics
from src.common.logger import setup_logging, get_logger
from src.common.middleware import RequestIDMiddleware
from src.common.exceptions import AppException

settings = get_settings()
setup_logging(level=settings.LOG_LEVEL, fmt=settings.LOG_FORMAT)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    app.state.redis = redis
    logger.info("Application startup complete")
    yield
    await redis.close()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}


@app.get("/health/live")
async def liveness_check():
    return {"status": "ok", "service": settings.APP_NAME}


async def check_database() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database readiness check failed")
        return False


async def check_redis(app_instance: FastAPI) -> bool:
    try:
        redis: Redis = app_instance.state.redis
        pong = await redis.ping()
        return bool(pong)
    except Exception:
        logger.exception("Redis readiness check failed")
        return False


@app.get("/health/ready")
async def readiness_check():
    database_ok = await check_database()
    redis_ok = await check_redis(app)
    is_ready = database_ok and redis_ok

    response = {
        "status": "ok" if is_ready else "degraded",
        "service": settings.APP_NAME,
        "checks": {
            "database": "ok" if database_ok else "failed",
            "redis": "ok" if redis_ok else "failed",
        },
    }

    if is_ready:
        return response

    return JSONResponse(status_code=503, content=response)


app.include_router(auth.router)
app.include_router(query.router)
app.include_router(admin.router)
app.include_router(metrics.router)
