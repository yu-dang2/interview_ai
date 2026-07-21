from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import auth, resume, jd, interview, voice
from backend.database import engine, Base

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


@app.get("/", tags=["Health"])
def root():
    return {"status": "서버 정상 작동 중", "version": "1.0.0"}