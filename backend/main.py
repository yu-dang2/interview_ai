import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAIError
from sqlalchemy import text

import backend.models  # noqa: F401  (create_all 전에 모델을 Base에 등록)
from backend.core.config import CORS_ORIGINS, IS_PRODUCTION
from backend.database import Base, engine
from backend.routers import auth, interview, jd, mypage, resume, voice
from backend.services import graph_runner, video_service

# 테이블 자동 생성
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    그래프 초기화/정리.

    체크포인터(AsyncSqliteSaver)가 async 컨텍스트 매니저라 모듈 import 시점에 만들 수 없다.
    그래서 그래프 컴파일을 여기서 한다. yield 이전이 기동, 이후가 종료 처리다.
    """
    await graph_runner.init()
    # 이전 프로세스가 영상 분석 도중 죽었다면 analyzing 인 채로 남아 있다.
    # 그대로 두면 프론트가 끝없이 폴링하므로 기동 시 정리한다.
    video_service.fail_orphaned_analyses()
    yield
    await graph_runner.close()


app = FastAPI(
    title="Lang-King",
    description="랭체인 & 랭그래프 기반 AI 면접관 백엔드 서버",
    version="1.0.0",
    lifespan=lifespan,
)

# allow_credentials=True 와 allow_origins=["*"] 는 함께 쓸 수 없다(브라우저가 거부).
# 그리고 "*" 를 두면 아무 사이트에서나 토큰을 실어 API 를 호출할 수 있다.
# 배포 시 CORS_ORIGINS 환경변수에 실제 프론트 주소를 넣는다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(jd.router)
app.include_router(interview.router)
app.include_router(voice.router)
app.include_router(mypage.router)


# ── LLM 예외 처리 ──────────────────────────────────────
# agent 의 call_llm 은 API 오류(OpenAIError)와 JSON 파싱 실패(JSONDecodeError)를 내부에서
# 재시도(지수 백오프)한 뒤, 그래도 실패하면 원인을 감싼 RuntimeError 를 던진다.
# 따라서 요청 처리 중 튀어나오는 LLM 실패는 RuntimeError 형태다. 스택트레이스 대신 503으로 변환한다.

@app.exception_handler(RuntimeError)
def handle_llm_runtime_error(request: Request, exc: RuntimeError):
    return JSONResponse(
        status_code=503,
        content={"detail": "AI 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요."},
    )


@app.exception_handler(OpenAIError)
def handle_openai_error(request: Request, exc: OpenAIError):
    return JSONResponse(
        status_code=503,
        content={"detail": "AI 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요."},
    )


@app.get("/", tags=["Health"])
def root():
    return {"status": "서버 정상 작동 중", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health():
    """
    컨테이너 헬스체크용. DB 연결까지 확인한다.

    "/" 는 프로세스가 살아 있는지만 보므로, DB 가 죽었는데도 정상으로 보고한다.
    오케스트레이터가 이 값을 보고 재기동을 판단하려면 의존 자원까지 확인해야 한다.
    """
    checks = {"database": False}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass

    healthy = all(checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "healthy" if healthy else "unhealthy", "checks": checks},
    )


# 디버그용 LLM 호출 확인. 인증이 없어 배포 환경에서는 노출하지 않는다.
if not IS_PRODUCTION:

    @app.get("/test-llm", tags=["Debug"])
    async def test_llm():
        import time

        from agent.graph.utils import get_client

        client = get_client()
        start = time.time()
        try:
            response = await client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": "안녕하세요라고만 답하세요."}],
            )
            return {
                "result": "성공",
                "elapsed": time.time() - start,
                "content": response.choices[0].message.content,
            }
        except Exception as e:
            return {
                "result": "실패",
                "elapsed": time.time() - start,
                "error": f"{type(e).__name__}: {e}",
            }
