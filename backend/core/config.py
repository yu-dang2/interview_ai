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

# 진행 중인 면접의 그래프 상태(LangGraph 체크포인트)를 담는 파일.
# 앱 데이터(DATABASE_URL)와 저장소가 다른 이유: LangGraph 공식 체크포인터에 MySQL 이 없다
# (memory/sqlite/postgres 뿐). 면접이 끝나면 결과는 interview_results 에 남으므로
# 이 파일은 버려도 되는 임시 데이터다.
CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "./interview_checkpoints.db")

# ── 영상 분석 ──────────────────────────────────────────
# 업로드된 면접 영상을 두는 디렉터리. 지금은 로컬 파일이지만 배포 시 S3 로 바꾼다.
# (교체 지점은 backend/services/video_storage.py 세 함수뿐이다.)
#
# 경로에 한글이 들어가면 안 된다. OpenCV(cv2.VideoCapture)가 Windows 에서 비ASCII
# 경로를 열지 못해 "영상을 열 수 없습니다" 로 실패한다. 저장 파일명도 그래서
# 업로드된 원본 이름을 쓰지 않고 UUID 로 만든다.
VIDEO_STORAGE_DIR = os.getenv("VIDEO_STORAGE_DIR", "./uploads/videos")

# 사용자당 보관하는 영상 개수. 초과분은 오래된 것부터 파일·행 모두 지운다.
VIDEO_MAX_PER_USER = int(os.getenv("VIDEO_MAX_PER_USER", "3"))

# N프레임마다 1장만 분석한다. 기본값 1(전 프레임)이면 30분 영상 분석에 30분이 걸린다.
VIDEO_SAMPLE_EVERY = int(os.getenv("VIDEO_SAMPLE_EVERY", "15"))

# 업로드 크기 상한(MB). 초과하면 413.
VIDEO_MAX_UPLOAD_MB = int(os.getenv("VIDEO_MAX_UPLOAD_MB", "200"))

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
