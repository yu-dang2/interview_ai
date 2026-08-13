"""
FastAPI 의존성

인증이 필요한 엔드포인트는 current_user 를, 로그인 여부에 따라 동작만 달라지는
엔드포인트는 optional_current_user 를 쓴다.

    @router.get("/me")
    def me(user: User = Depends(current_user)):
        ...

면접·이력서·JD 라우터에 소유권(users_user_id) 연결과 함께 적용 완료. 토큰 없이
호출하면 401 이므로, 통합 테스트는 로그인해서 받은 토큰을 헤더에 실어야 한다.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.security import decode_access_token
from backend.database import get_db
from backend.models.models import User

# auto_error=False 라야 토큰이 없을 때 FastAPI 가 먼저 403 을 내지 않고
# 우리 쪽 분기(필수/선택)로 넘어온다.
_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="인증이 필요합니다.",
    headers={"WWW-Authenticate": "Bearer"},
)


def optional_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """토큰이 없거나 유효하지 않으면 None."""
    if cred is None:
        return None
    user_id = decode_access_token(cred.credentials)
    if user_id is None:
        return None
    return db.get(User, user_id)


def current_user(user: User | None = Depends(optional_current_user)) -> User:
    """토큰이 없거나 유효하지 않으면 401."""
    if user is None:
        raise _CREDENTIALS_ERROR
    return user
