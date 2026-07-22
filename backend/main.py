from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAIError

import backend.models  # noqa: F401  (create_all 전에 모델을 Base에 등록)
from backend.database import Base, engine
from backend.routers import auth, interview, jd, resume, voice

# 테이블 자동 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Lang-King",
    description="랭체인 & 랭그래프 기반 AI 면접관 백엔드 서버",
    version="1.0.0",
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
