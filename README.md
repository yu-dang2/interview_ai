# interview_ai

2026 한이음 드림업 공모전 : 랭체인 &amp; 랭그래프 기반 지능형 취업 뽀개기 AI 면접관
<br>
<br>


👩‍💻 담당 역할
- Backend Development
- FastAPI 서버 개발
- API 설계 및 구현
- Database 설계 및 연동
- AI 서비스(STT/LLM) 연동
- Docker 기반 배포
<br>


✅ 수행 내용
- FastAPI 백엔드 프로젝트 구조 설계
- REST API 구현
- Router / Schema / Service 구조 구성
- SQLite 및 Database 설정
- ERD 기반 데이터 모델 반영
- STT(OpenAI GPT-4o-transcribe) 연동
- Swagger API 문서 작성
<br>

🛠️ Tech Stack
- Python
- FastAPI
- SQLite
- SQLAlchemy
- OpenAI API
=======

---

## 실행 환경

| | |
|---|---|
| Python | **3.12** (3.13 은 mediapipe 미지원) |
| DB | MySQL 8.0 |
| 백엔드 | FastAPI + uvicorn |
| 프론트 | Streamlit |

## 로컬 실행

### 1. 가상환경

`python -m venv` 를 쓰면 시스템 기본 파이썬이 잡힐 수 있다. **버전을 명시**한다.

```bash
py -3.12 -m venv venv          # Windows
python3.12 -m venv venv        # macOS / Linux

venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux
```

### 2. 의존성

```bash
pip install -r requirements.txt
```

> mediapipe·opencv 가 포함되어 있어 처음 설치는 몇 분 걸린다. Python 3.13 에서는 설치가 실패한다.

### 3. DB

MySQL 에 데이터베이스와 계정을 만든다. 테이블은 서버 기동 시 자동 생성된다.

```sql
CREATE DATABASE interview_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'interview_ai'@'localhost' IDENTIFIED BY '비밀번호';
GRANT ALL PRIVILEGES ON interview_ai.* TO 'interview_ai'@'localhost';
```

### 4. 환경변수

`.env.example` 을 복사해 `.env` 를 만들고 값을 채운다.

```bash
cp .env.example .env
```

**`SECRET_KEY` 는 반드시 채운다.** 비워두면 서버를 재시작할 때마다 새로 생성되어 발급된 토큰이 전부 무효가 된다.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5. 실행

```bash
uvicorn backend.main:app --port 8000     # 백엔드
streamlit run frontend/app.py            # 프론트 (다른 터미널)
```

- API 문서: http://127.0.0.1:8000/docs
- 헬스체크: http://127.0.0.1:8000/health

---

## Docker 로 실행

MySQL 까지 함께 뜨므로 로컬에 MySQL 을 설치하지 않아도 된다.

```bash
cp .env.example .env      # OPENAI_API_KEY, SECRET_KEY 를 채운다
docker compose up --build
```

```bash
docker compose down       # 중지 (데이터는 볼륨에 남는다)
docker compose down -v    # 볼륨까지 삭제
```

**영상과 체크포인트는 볼륨에 저장된다.** 마운트를 빼면 컨테이너를 재시작할 때마다 업로드된 영상과 진행 중이던 면접이 사라진다.

---

## 배포 시 확인할 것

| 항목 | 설정 |
|---|---|
| `ENVIRONMENT` | `production` — 디버그 엔드포인트가 노출되지 않는다 |
| `CORS_ORIGINS` | 실제 프론트 주소. `*` 로 두면 아무 사이트에서나 API 호출이 가능하다 |
| `SECRET_KEY` | 고정값. 바뀌면 전원 로그아웃된다 |
| `INTERVIEW_DAILY_LIMIT` | 면접 생성 횟수 제한. LLM 비용에 직결된다 |

**동시 접속**은 현재 워커 1개 기준이다. LangGraph 체크포인터가 SQLite 파일이라 여러 프로세스가 같은 파일을 쓰면 잠금 충돌이 난다. 늘리려면 Postgres 체크포인터로 옮겨야 한다.

**개인정보**는 업로드 시점에 비식별화된다(`backend/core/masking.py`). 이메일·전화번호·주민번호·주소·생년월일이 자리표시자로 바뀐 뒤 저장·전송되므로, DB 와 LLM 어디에도 원문이 남지 않는다.

---

## 폴더 구조

```
agent/        LangGraph 에이전트 (그래프·노드·프롬프트)
backend/      FastAPI 서버
  core/       설정·인증·비식별화
  models/     SQLAlchemy 모델
  routers/    엔드포인트
  schemas/    Pydantic 스키마
  services/   비즈니스 로직
  tests/      통합 확인 스크립트·시나리오
frontend/     Streamlit 화면
video/        영상 분석 모듈
docs/         회의록·설계 문서
```

## 테스트

```bash
python backend/tests/demo_flow_check.py    # 데모 경로 백엔드 확인 (LLM 호출 발생)
```

화면 확인 시나리오는 `backend/tests/README.md` 에 있다.
