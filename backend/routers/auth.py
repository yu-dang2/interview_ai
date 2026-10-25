"""
인증 라우터

엔드포인트:
    POST /auth/register - 이메일 회원가입
    POST /auth/login    - 이메일 로그인 (JWT 발급)
    POST /auth/logout   - 로그아웃
    GET  /auth/me       - 현재 로그인한 사용자
    GET  /auth/kakao    - 카카오 OAuth 로그인
    GET  /auth/google   - 구글 OAuth 로그인
"""

import secrets
import time
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from backend.core.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_REDIRECT_URI,
)
from backend.core.deps import current_user
from backend.core.security import create_access_token, hash_password, verify_password
from backend.database import get_db
from backend.models.models import User
from backend.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse
)

router = APIRouter(prefix="/auth", tags=["Auth"])

# ── 구글 로그인 임시 저장소 ────────────────────────────
# state 는 CSRF 방지용이다.
# 이게 없으면 공격자가 자기 구글 계정으로 받은 code 를 피해자 브라우저에서 열게 만들어,
# 피해자가 공격자 계정으로 로그인된 상태가 되게 할 수 있다.
#
# 메모리에 두는 이유: 수명이 10분이라 재시작하면 사라져도 진행 중이던 로그인만 실패한다.
# 다시 누르면 된다. 이걸 위해 Redis 를 붙일 이유가 없다.
# uvicorn --workers 1 을 전제로 한다. (Dockerfile CMD)
_GOOGLE_STATE_TTL_SEC = 600

_google_states: dict[str, float] = {}      # state -> 만료 시각(monotonic)

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"


def _sweep_google_states() -> None:
    """만료된 state 를 치운다. 발급할 때마다 한 번씩 돌면 충분하다."""
    now = time.monotonic()
    for key in [k for k, exp in _google_states.items() if exp <= now]:
        _google_states.pop(key, None)


def _issue_google_state() -> str:
    _sweep_google_states()
    state = secrets.token_urlsafe(24)
    _google_states[state] = time.monotonic() + _GOOGLE_STATE_TTL_SEC
    return state


def _consume_google_state(state: str) -> bool:
    """한 번 쓴 state 는 지운다. 같은 code 를 두 번 쓰지 못하게 한다."""
    expires = _google_states.pop(state, None)
    return expires is not None and expires > time.monotonic()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """이메일 회원가입"""
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다.")

    user = User(
        user_name=req.name,
        email=req.email,
        password=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(user_id=user.user_id, name=user.user_name, email=user.email)


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """이메일 로그인"""
    user = db.query(User).filter(User.email == req.email).first()
    # 이메일이 없는 경우와 비밀번호가 틀린 경우를 같은 응답으로 묶는다.
    # 구분해서 알려주면 가입 여부를 캐낼 수 있다.
    if user is None or not verify_password(req.password, user.password or ""):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    return LoginResponse(access_token=create_access_token(user.user_id))


@router.post("/logout")
def logout():
    """
    로그아웃

    JWT 는 서버가 상태를 들고 있지 않아 발급된 토큰을 무효화할 수 없다.
    실제 로그아웃은 클라이언트가 토큰을 지우는 것으로 끝난다.
    (블랙리스트가 필요해지면 Redis 등 별도 저장소를 붙여야 한다.)
    """
    return {"message": "로그아웃 되었습니다."}


@router.get("/me", response_model=RegisterResponse)
def me(user: User = Depends(current_user)):
    """현재 로그인한 사용자 정보. 토큰 검증이 도는지 확인하는 용도로도 쓴다."""
    return RegisterResponse(user_id=user.user_id, name=user.user_name, email=user.email)


@router.get("/kakao")
def kakao_login():
    """카카오 OAuth 로그인"""
    # TODO: 카카오 OAuth 구현
    raise HTTPException(
        status_code=501,
        detail="카카오 로그인은 준비 중입니다. 이메일로 로그인해주세요.",
    )


@router.get("/google")
def google_login():
    """
    구글 인증 화면으로 보낸다.

    JSON 이 아니라 302 를 돌려준다. 화면이 이 주소로 그냥 이동하면 되도록 만든 것이다.
    fetch 로 부르면 리디렉션이 따라가지지 않으므로, 프론트는 location 을 바꿔야 한다.

    키가 없으면 501 을 돌려준다. 화면은 이걸 받으면 버튼을 숨기거나 안내만 띄우면 된다.
    이메일 로그인은 그대로 동작한다.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=501,
            detail="구글 로그인이 설정되지 않았습니다. 이메일로 로그인해주세요.",
        )

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        # openid 를 넣어야 id_token 이 함께 와서 userinfo 를 따로 부르지 않아도 된다.
        "scope": "openid email profile",
        "state": _issue_google_state(),
        # 재동의 없이도 이메일을 다시 받기 위해 필요하다.
        "include_granted_scopes": "true",
        # 매번 계정 선택 화면을 띄운다. 계정이 여러 개일 때 의도한 것으로 붙게 한다.
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}", status_code=302)