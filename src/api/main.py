from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from src.api.config import get_settings
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


app.include_router(auth.router)
app.include_router(query.router)
app.include_router(admin.router)
app.include_router(metrics.router)
