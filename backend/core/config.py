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

# 이 시간을 넘겨도 analyzing 이면 실패로 본다.
# 분석 도중 서버가 죽으면 상태가 영구히 analyzing 으로 남아 프론트가 끝없이 폴링한다.
VIDEO_ANALYZE_TIMEOUT_MIN = int(os.getenv("VIDEO_ANALYZE_TIMEOUT_MIN", "30"))

# 영상 분석(mediapipe)은 protobuf 4.25 를 요구해, 백엔드 프로세스(protobuf 7·chromadb)와
# 같은 파이썬에 함께 살 수 없다. 그래서 mediapipe 를 격리한 별도 venv 의 파이썬으로
# video/analyze_runner.py 를 subprocess 실행하고 결과 JSON 만 받는다.
# 경로에 한글이 있으면 mediapipe 의 .binarypb 로드가 실패하므로 ASCII 경로여야 한다.
# 팀원마다 venv 위치가 다르면 VIDEO_ANALYZER_PYTHON 환경변수로 덮어쓴다.
VIDEO_ANALYZER_PYTHON = os.getenv("VIDEO_ANALYZER_PYTHON", r"C:\mp_venv\Scripts\python.exe")

# ── 인증 ───────────────────────────────────────────────
# SECRET_KEY 를 .env 에 지정하지 않으면 기동할 때마다 새 키가 생성된다.
# 개발 중에는 편하지만 서버를 재시작하면 발급해둔 토큰이 전부 무효가 되므로,
# 여러 명이 붙는 통합 테스트나 배포 환경에서는 .env 에 고정값을 넣을 것.
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# ── 배포 ───────────────────────────────────────────────
# 실행 환경. "production" 이면 디버그용 엔드포인트를 노출하지 않는다.
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT.lower() in ("production", "prod")

# CORS 허용 출처. 쉼표로 구분한다.
# 개발 기본값은 로컬 Streamlit 이고, 배포 시에는 실제 프론트 주소를 넣는다.
# "*" 를 그대로 두면 아무 사이트에서나 토큰을 실어 API 를 호출할 수 있다.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501"
    ).split(",")
    if origin.strip()
]

# ── 사용량 제한 ────────────────────────────────────────
# 요청 수가 아니라 LLM 호출이 일어나는 지점을 막는다. 비용은 거기서 발생한다.
# 면접 1회에 gpt-5-mini 호출이 십수 번 나가므로 세션 생성이 가장 비싼 동작이다.
#
# 현재 규모를 고려해 DB 카운트로 세는 방식으로 구현했다. 사용자가 늘어나면
# Redis 기반 큐로 전환할 예정이다.
#
# ※ 아래 기본값(하루 10회 / 동시 3개)은 임시로 잡은 값이다. 베타 테스트 참가자가
#   몇 번씩 써볼지에 따라 달라져야 해서 회의에서 논의 예정이다.
#
# 0 이하로 두면 제한을 끈다 (개발 중 편의).
INTERVIEW_DAILY_LIMIT = int(os.getenv("INTERVIEW_DAILY_LIMIT", "10"))
INTERVIEW_ACTIVE_LIMIT = int(os.getenv("INTERVIEW_ACTIVE_LIMIT", "3"))

# ── 면접 제한 시간 ──────────────────────────────────────
# 화면 타이머와 같은 값이다. 프론트가 0초에 종료를 걸어주지만, 탭을 열어둔 채
# 계속 답변하면 서버가 막을 방법이 없어 여기서도 확인한다.
INTERVIEW_TIME_LIMIT_MIN = int(os.getenv("INTERVIEW_TIME_LIMIT_MIN", "30"))

# 이 시간이 지나도 active 로 남아 있는 세션은 정리한다.
# 브라우저를 그냥 닫으면 종료 요청이 오지 않아 세션이 영원히 active 로 남고,
# 동시 진행 제한(INTERVIEW_ACTIVE_LIMIT)에 걸려 새 면접을 시작하지 못한다.
# 제한 시간의 두 배로 잡아, 진행 중인 면접을 건드리지 않게 여유를 둔다.
INTERVIEW_STALE_AFTER_MIN = int(
    os.getenv("INTERVIEW_STALE_AFTER_MIN", str(INTERVIEW_TIME_LIMIT_MIN * 2))
)

# ── 면접 진행 ──────────────────────────────────────────
# 면접 종료 시 채팅창에 보여줄 마무리 문구.
# report_generator가 마지막 AIMessage로 리포트 JSON 전체를 넣기 때문에,
# 그 JSON을 그대로 채팅 UI에 내보내지 않으려고 이 문구로 대체한다.
CLOSING_MESSAGE = "면접이 종료되었습니다. 결과 리포트를 확인해 주세요."

# 라포 형성 질문(자기소개·지원 동기) 다음 질문 앞에 붙이는 안내.
# 가벼운 질문에서 평가 질문으로 곧바로 넘어가면 흐름이 끊긴다.
# 페르소나마다 다음에 오는 질문 유형이 달라서 "기술 질문"으로 특정하지 않는다.
RAPPORT_TRANSITION_MESSAGE = "답변 감사합니다. 이제 본격적으로 면접 질문을 시작하겠습니다."

# 라포 형성 질문으로 볼 question_list 의 type 값.
# 8/20 요청대로 프롬프트가 "라포"로 바뀌었고(d60536d), agent 쪽 판별값
# (agent/graph/utils.py 의 RAPPORT_TYPE)도 "라포"로 맞춰졌다(3bcacbe).
# "자기소개"는 그 사이 시작된 세션이 남아 있을 수 있어 남겨둔 것이라,
# 진행 중이던 면접이 모두 끝나면 지운다.
RAPPORT_QUESTION_TYPES = ("라포", "자기소개")

# 면접 시작 진행 단계. 첫 질문까지 90~140초가 걸려서 화면이 멈춰 보이므로,
# 어느 단계인지 흘려보낸다. (2026-08-21 지원님 요청)
#
# 문구는 프론트가 바꿀 수 있어야 해서 stage 키와 함께 내보낸다. label 은 참고용이다.
INTERVIEW_START_STAGES = {
    "parsing": "이력서·채용공고 읽는 중",
    "matching": "직무 적합도 분석 중",
    "generating": "맞춤 질문 만드는 중",
}

# 최종 총점 = 이력서 점수 × RESUME_WEIGHT + 면접 점수 × INTERVIEW_WEIGHT
# 3 : 7 은 2026-08-16 회의에서 확정한 비율이다.
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
