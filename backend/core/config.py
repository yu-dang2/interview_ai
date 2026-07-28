"""
환경 설정 중앙화

.env 로드는 여기 한 곳에서만 한다.
backend.database, backend.routers.voice 등은 각자 load_dotenv()를 부르지 말고
이 모듈을 import 할 것.
"""

import os
import secrets
from dotenv import load_dotenv

load_dotenv()


# ── LLM ────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ── DB ─────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lang_king.db")

# ── 인증 ───────────────────────────────────────────────
# SECRET_KEY 를 .env 에 지정하지 않으면 기동할 때마다 새 키가 생성된다.
# 개발 중에는 편하지만 서버를 재시작하면 발급해둔 토큰이 전부 무효가 되므로,
# 여러 명이 붙는 통합 테스트나 배포 환경에서는 .env 에 고정값을 넣을 것.
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# ── 면접 진행 ──────────────────────────────────────────
# 면접 종료 시 채팅창에 보여줄 마무리 문구.
# report_generator가 마지막 AIMessage로 리포트 JSON 전체를 넣기 때문에,
# 그 JSON을 그대로 채팅 UI에 내보내지 않으려고 이 문구로 대체한다.
CLOSING_MESSAGE = "면접이 종료되었습니다. 결과 리포트를 확인해 주세요."

# 최종 총점 = 이력서 점수 × RESUME_WEIGHT + 면접 점수 × INTERVIEW_WEIGHT
RESUME_WEIGHT = 0.3
INTERVIEW_WEIGHT = 0.7


def require_openai_key() -> str:
    """OPENAI_API_KEY를 반환. 없으면 즉시 실패시킨다."""
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY가 설정되어 있지 않습니다. "
            "프로젝트 루트의 .env 파일에 OPENAI_API_KEY=... 를 추가해주세요."
        )
    return OPENAI_API_KEY
