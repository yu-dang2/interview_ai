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

import logging
import secrets
import time
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from backend.core.config import (
    FRONTEND_BASE_URL,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)
from backend.core.deps import current_user
from backend.core.security import create_access_token, hash_password, verify_password
from backend.database import get_db
from backend.models.models import User
from backend.schemas.auth import (
    ExchangeRequest,
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse
)

logger = logging.getLogger(__name__)

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
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# ── 로그인 완료 코드 임시 저장소 ────────────────────────
# 로그인이 끝나면 액세스 토큰을 화면에 넘겨야 하는데, 리디렉션 주소에 토큰을 직접 실으면
# 브라우저 기록·서버 접근 로그·리퍼러 헤더에 그대로 남는다. 24시간짜리 토큰이라 한 번
# 새면 그동안 계속 쓸 수 있다.
#
# 그래서 주소에는 수명 60초짜리 일회용 코드만 싣고, 화면 서버가 /auth/exchange 로
# 바꿔 간다. 코드가 새어도 60초 안에 먼저 써야 하고, 한 번 쓰면 사라진다.
_LOGIN_CODE_TTL_SEC = 60

_login_codes: dict[str, tuple[str, float]] = {}   # code -> (액세스 토큰, 만료 시각)


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


def _issue_login_code(access_token: str) -> str:
    """액세스 토큰을 맡아두고 교환용 코드를 돌려준다."""
    now = time.monotonic()
    for key in [k for k, (_, exp) in _login_codes.items() if exp <= now]:
        _login_codes.pop(key, None)
    code = secrets.token_urlsafe(32)
    _login_codes[code] = (access_token, now + _LOGIN_CODE_TTL_SEC)
    return code


def _consume_login_code(code: str) -> str | None:
    """코드를 액세스 토큰으로 바꾼다. 한 번 쓰면 사라진다."""
    item = _login_codes.pop(code, None)
    if item is None:
        return None
    access_token, expires = item
    return access_token if expires > time.monotonic() else None


def _fail(reason: str) -> RedirectResponse:
    """로그인 실패를 화면에 알린다.

    구글에서 돌아오는 길이라 사용자는 브라우저에 있다. JSON 오류를 띄우면 빈 화면을
    보게 되므로, 로그인 화면으로 돌려보내고 사유만 짧게 붙인다.
    자세한 원인은 서버 로그에만 남긴다.
    """
    return RedirectResponse(
        f"{FRONTEND_BASE_URL}/?login_error={reason}", status_code=302
    )


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


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """
    구글이 인증을 마치고 사용자를 돌려보내는 자리.

    이 주소는 사용자가 직접 여는 곳이 아니라 구글이 브라우저를 보내는 곳이다.
    그래서 실패해도 JSON 을 던지지 않고 화면으로 돌려보낸다.

    - 하는 일
    code 를 구글 토큰으로 바꾸고, 거기서 이메일을 꺼내 사용자를 찾거나 만든 뒤
    우리 액세스 토큰을 발급한다. 토큰은 주소에 싣지 않고 일회용 코드로 바꿔 넘긴다.

    - 사용자 테이블을 바꾸지 않은 이유
    구글 고유 ID 컬럼을 두는 편이 정석이지만, create_all 은 이미 있는 테이블에 컬럼을
    더하지 못해 운영 중인 DB 를 손으로 고쳐야 한다. 이메일이 이미 고유 키라 그것으로
    맞춰도 같은 사람을 가리킨다.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return _fail("not_configured")

    # 사용자가 동의 화면에서 취소하면 code 없이 error 만 온다.
    if error:
        logger.info("구글 로그인 취소 또는 거부: %s", error)
        return _fail("cancelled")

    if not code or not state:
        return _fail("invalid_request")

    # state 는 우리가 발급한 것만 통과시킨다. 공격자가 자기 계정으로 받은 code 를
    # 피해자 브라우저에서 열게 만드는 것을 막는다.
    if not _consume_google_state(state):
        logger.warning("구글 로그인 state 불일치 또는 만료")
        return _fail("expired")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
        res.raise_for_status()
        id_token = res.json().get("id_token")
    except Exception as e:
        # 구글 응답에는 클라이언트 시크릿이 섞여 있을 수 있어 본문을 그대로 남기지 않는다.
        logger.error("구글 토큰 교환 실패: %s: %s", type(e).__name__, e)
        return _fail("google_error")

    if not id_token:
        logger.error("구글 응답에 id_token 이 없습니다.")
        return _fail("google_error")

    # 서명을 다시 확인하지 않는 이유:
    # 이 토큰은 브라우저를 거치지 않고 구글 토큰 엔드포인트에서 HTTPS 로 직접 받았다.
    # 중간에 끼어들 수 있는 구간이 없어 구글 문서도 이 경우 검증 생략을 허용한다.
    try:
        claims = jwt.decode(id_token, options={"verify_signature": False})
    except jwt.PyJWTError as e:
        logger.error("id_token 해석 실패: %s", e)
        return _fail("google_error")

    email = (claims.get("email") or "").strip().lower()
    if not email:
        return _fail("no_email")

    # 이메일로 계정을 찾기 때문에 소유가 확인된 이메일만 받는다.
    # 확인되지 않은 주소를 믿으면 남의 계정으로 들어갈 수 있다.
    if not claims.get("email_verified"):
        logger.warning("구글 계정의 이메일이 확인되지 않았습니다.")
        return _fail("email_unverified")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        # 비밀번호는 비워 둔다. verify_password 가 빈 해시에 False 를 돌려주므로
        # 이메일 로그인으로는 들어올 수 없고 구글로만 들어온다.
        user = User(
            user_name=(claims.get("name") or email.split("@")[0])[:50],
            email=email,
            password=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("구글 로그인으로 계정 생성: user_id=%s", user.user_id)

    login_code = _issue_login_code(create_access_token(user.user_id))
    return RedirectResponse(
        f"{FRONTEND_BASE_URL}/?login={login_code}", status_code=302
    )


@router.post("/exchange", response_model=LoginResponse)
def exchange(req: ExchangeRequest):
    """일회용 코드를 액세스 토큰으로 바꾼다.

    화면 서버가 부르는 자리다. 코드는 한 번 쓰면 사라지고 60초 뒤 만료된다.
    """
    access_token = _consume_login_code(req.code)
    if access_token is None:
        raise HTTPException(
            status_code=400,
            detail="로그인 정보가 만료되었습니다. 다시 로그인해주세요.",
        )
    return LoginResponse(access_token=access_token)