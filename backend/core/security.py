"""
비밀번호 해싱 · JWT 발급/검증

라우터는 여기서만 암호 관련 함수를 가져다 쓴다.
bcrypt/PyJWT 를 직접 부르는 코드가 라우터에 흩어지지 않게 한다.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from backend.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, SECRET_KEY

# bcrypt 는 72바이트를 넘는 입력을 조용히 잘라낸다. 그러면 73바이트 이후가 달라도
# 같은 비밀번호로 통과하므로, 잘라내기 전에 스키마(RegisterRequest)에서 막는다.
BCRYPT_MAX_BYTES = 72


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    # DB 에 평문이나 깨진 해시가 들어 있으면 bcrypt 가 ValueError 를 던진다.
    # 인증 실패로 처리해야지 500 이 나가면 안 된다.
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # JWT 표준상 sub 는 문자열이어야 한다.
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """유효하면 user_id, 만료·위조·형식 오류면 None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return None
