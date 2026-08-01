import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAIError

import backend.models  # noqa: F401  (create_all 전에 모델을 Base에 등록)
from backend.database import Base, engine
from backend.routers import auth, interview, jd, mypage, resume, voice
from backend.services import graph_runner

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
    yield
    await graph_runner.close()


app = FastAPI(
    title="Lang-King",
    description="랭체인 & 랭그래프 기반 AI 면접관 백엔드 서버",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Streamlit 연동 시 출처 제한 권장
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

@app.get("/test-llm")
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
        elapsed = time.time() - start
        return {"result": "성공", "elapsed": elapsed, "content": response.choices[0].message.content}
    except Exception as e:
        elapsed = time.time() - start
        return {"result": "실패", "elapsed": elapsed, "error": f"{type(e).__name__}: {e}"}
