import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.config import get_settings
from src.api.database import get_db
from src.api.models.user import User
from src.common.exceptions import UnauthorizedException, ForbiddenException

security_scheme = HTTPBearer(auto_error=False)

settings = get_settings()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _create_access_token(sub: str, tenant_id: str, role: str) -> str:
    payload = {
        "sub": sub,
        "tenant_id": tenant_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _create_refresh_token(sub: str) -> str:
    payload = {
        "sub": sub,
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def create_user(db: AsyncSession, tenant_id: str, email: str, password: str, role: str = "customer") -> User:
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        email=email,
        hashed_password=_hash_password(password),
        role=role,
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not _verify_password(password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")
    return user


async def login(db: AsyncSession, email: str, password: str) -> tuple[str, str, User]:
    user = await authenticate_user(db, email, password)
    access_token = _create_access_token(sub=user.id, tenant_id=user.tenant_id, role=user.role)
    refresh_token = _create_refresh_token(sub=user.id)
    return access_token, refresh_token, user


async def refresh_access_token(refresh_token: str) -> tuple[str, str]:
    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid refresh token")
        new_access = _create_access_token(
            sub=payload["sub"],
            tenant_id=payload.get("tenant_id", ""),
            role=payload.get("role", "customer"),
        )
        new_refresh = _create_refresh_token(sub=payload["sub"])
        return new_access, new_refresh
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Refresh token expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedException("Invalid refresh token")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedException("Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    if credentials is None:
        raise UnauthorizedException("Not authenticated")
    return decode_token(credentials.credentials)


def require_role(allowed_roles: list[str]):
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in allowed_roles:
            raise ForbiddenException("Insufficient permissions")
        return current_user
    return role_checker
