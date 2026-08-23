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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
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
    """구글 OAuth 로그인"""
    # TODO: 구글 OAuth 구현
    raise HTTPException(
        status_code=501,
        detail="구글 로그인은 준비 중입니다. 이메일로 로그인해주세요.",
    )