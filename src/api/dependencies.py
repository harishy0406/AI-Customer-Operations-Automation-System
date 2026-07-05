from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.api.services.auth_service import decode_token
from src.common.exceptions import UnauthorizedException, ForbiddenException

security = HTTPBearer(auto_error=False)


async def get_current_user_dep(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if credentials is None:
        raise UnauthorizedException("Not authenticated")
    return decode_token(credentials.credentials)


async def require_admin(
    current_user: dict = Depends(get_current_user_dep),
) -> dict:
    if current_user.get("role") not in ("admin", "ops_manager"):
        raise ForbiddenException("Admin or Ops Manager role required")
    return current_user


async def require_agent_or_admin(
    current_user: dict = Depends(get_current_user_dep),
) -> dict:
    if current_user.get("role") not in ("agent", "admin", "ops_manager"):
        raise ForbiddenException("Agent or Admin role required")
    return current_user
