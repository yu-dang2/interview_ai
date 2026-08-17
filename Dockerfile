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

# 영상·체크포인트가 저장될 위치. compose 에서 볼륨으로 마운트한다.
# 마운트하지 않으면 컨테이너를 재시작할 때마다 진행 중이던 면접과 영상이 사라진다.
RUN mkdir -p /app/uploads/videos /app/data
ENV VIDEO_STORAGE_DIR=/app/uploads/videos \
    CHECKPOINT_DB_PATH=/app/data/interview_checkpoints.db \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# 워커를 1로 두는 이유: LangGraph 체크포인터가 SQLite 파일이라 여러 프로세스가
# 같은 파일을 쓰면 잠금 충돌이 난다. 동시 접속을 늘리려면 Postgres 체크포인터로
# 옮겨야 하고, 그건 별도 작업이다.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
