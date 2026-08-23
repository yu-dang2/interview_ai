# 백엔드 API 서버 이미지
#
# mediapipe 가 Python 3.13 을 지원하지 않아 3.12 로 고정한다.
# slim 이미지에는 OpenCV 가 필요로 하는 시스템 라이브러리가 없어 따로 설치한다.
FROM python:3.12-slim

# libgl1 / libglib2.0-0 : cv2 import 시 필요 (없으면 ImportError: libGL.so.1)
# 나머지는 mediapipe 가 참조하는 그래픽·미디어 라이브러리
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성을 먼저 복사해 레이어 캐시를 살린다.
# 코드만 바뀌면 pip install 을 다시 하지 않는다.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY agent/ ./agent/
COPY backend/ ./backend/
COPY video/ ./video/

# 화면(Streamlit)도 같은 이미지에 담는다. compose 의 web 서비스가 실행 명령만
# 바꿔서 쓴다. 이미지를 두 벌 만들면 의존성 설치가 두 번 돌고 버전도 갈릴 수 있다.
COPY frontend/ ./frontend/

# 직무 지식 카드 원본과 인덱스 생성 스크립트.
# 인덱스(data/knowledge_index/)는 임베딩 결과라 이미지에 굽지 않는다. 빌드마다
# OpenAI 를 호출하게 되고 빌드 시점에 키가 필요해진다. 컨테이너를 띄운 뒤
# 아래 명령으로 한 번 만들면 볼륨에 남는다.
#   docker compose exec api python scripts/build_knowledge_index.py
COPY data/ ./data/
COPY scripts/ ./scripts/

# 쓰기 대상은 /app/var 로 모은다. compose 에서 볼륨으로 마운트해야
# 컨테이너를 재시작해도 진행 중이던 면접과 영상이 남는다.
#
# /app/data(카드 원본)와 분리하는 이유: 같은 경로에 볼륨을 걸면 이미지에 넣은
# 파일이 볼륨에 가려져, 카드를 고쳐 다시 빌드해도 반영되지 않는다.
RUN mkdir -p /app/uploads/videos /app/var
ENV VIDEO_STORAGE_DIR=/app/uploads/videos \
    CHECKPOINT_DB_PATH=/app/var/interview_checkpoints.db \
    KNOWLEDGE_INDEX_PATH=/app/var/knowledge_index \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# 워커를 1로 두는 이유: LangGraph 체크포인터가 SQLite 파일이라 여러 프로세스가
# 같은 파일을 쓰면 잠금 충돌이 난다. 동시 접속을 늘리려면 Postgres 체크포인터로
# 옮겨야 하고, 그건 별도 작업이다.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
