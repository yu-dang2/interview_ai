"""
인증 관련 Pydantic 스키마
"""

from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.core.security import BCRYPT_MAX_BYTES


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def _fits_bcrypt(cls, v: str) -> str:
        # bcrypt 는 72바이트를 넘는 입력을 조용히 잘라낸다. 그러면 73바이트 이후가
        # 달라도 같은 비밀번호로 로그인되므로, 글자 수가 아니라 바이트 수로 막는다.
        if len(v.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise ValueError(f"비밀번호는 {BCRYPT_MAX_BYTES}바이트를 넘을 수 없습니다.")
        return v


class RegisterResponse(BaseModel):
    user_id: int
    name: str
    email: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ExchangeRequest(BaseModel):
    """소셜 로그인 후 화면이 일회용 코드를 액세스 토큰으로 바꿀 때 쓴다.

    토큰을 리디렉션 주소에 직접 실어 보내면 브라우저 기록·서버 접근 로그·리퍼러에
    그대로 남는다. 수명이 짧은 일회용 코드만 주소에 싣고, 교환은 화면 서버가 한다.
    """

    code: str = Field(min_length=10, max_length=200)