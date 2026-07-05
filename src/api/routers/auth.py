from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from src.api.services.auth_service import login, refresh_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login_endpoint(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    access_token, refresh_token, _ = await login(db, req.email, req.password)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_endpoint(req: RefreshRequest):
    access_token, refresh_token = await refresh_access_token(req.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
