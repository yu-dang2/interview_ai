"""
인증 라우터

엔드포인트:
    POST /auth/register - 이메일 회원가입
    POST /auth/login    - 이메일 로그인
    POST /auth/logout   - 로그아웃
    GET  /auth/kakao    - 카카오 OAuth 로그인
    GET  /auth/google   - 구글 OAuth 로그인
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=RegisterResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """이메일 회원가입"""
    # TODO: 회원가입 로직 구현
    pass


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """이메일 로그인"""
    # TODO: 로그인 로직 구현
    pass


@router.post("/logout")
def logout():
    """로그아웃"""
    # TODO: 로그아웃 로직 구현
    return {"message": "로그아웃 되었습니다."}


@router.get("/kakao")
def kakao_login():
    """카카오 OAuth 로그인"""
    # TODO: 카카오 OAuth 구현
    raise HTTPException(status_code=501, detail="카카오 OAuth 미구현")


@router.get("/google")
def google_login():
    """구글 OAuth 로그인"""
    # TODO: 구글 OAuth 구현
    raise HTTPException(status_code=501, detail="구글 OAuth 미구현")