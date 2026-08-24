"""
면접 라우터

모든 엔드포인트가 인증을 요구하며, 세션은 생성한 사용자에게 귀속된다.
남의 세션은 조회되지 않는다.

엔드포인트:
    POST /interview/sessions           - 면접 세션 생성 (면접 시작)
    POST /interview/sessions/stream    - 면접 세션 생성 + 준비 진행 상황 스트리밍
    GET  /interview/sessions           - 내 면접 기록 목록 (마이페이지)
    POST /interview/sessions/{id}/chat - 텍스트 답변 전송
    POST /interview/sessions/{id}/end  - 면접 종료
    GET  /interview/sessions/{id}/result   - 결과 리포트 조회
    GET  /interview/sessions/{id}/feedback - 질문별 피드백 보고서 조회
    GET  /interview/sessions/{id}/resume-optimization - 이력서 최적화 제안 조회
    POST /interview/sessions/{id}/video          - 면접 영상 업로드 (분석은 백그라운드)
    GET  /interview/sessions/{id}/video-metrics  - 영상 분석 상태/결과 조회 (폴링용)

    영상 두 개는 video/README.md 합의 경로로도 받는다 (sessions 없는 형태):
    POST /interview/{id}/video
    GET  /interview/{id}/video-metrics
"""

import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.core.deps import current_user
from backend.database import get_db
from backend.models.models import User
from backend.schemas.interview import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionListResponse,
    ChatRequest,
    ChatResponse,
    ResultResponse,
    ResumeOptimizationResponse,
    FeedbackResponse,
)
from backend.schemas.video import VideoMetricsResponse, VideoUploadResponse
from backend.services import video_service
from backend.services.interview_service import InterviewService, stream_session
from backend.services.video_service import VideoService

router = APIRouter(prefix="/interview", tags=["Interview"])


@router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(
    req: SessionCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """면접 세션 생성 및 첫 질문 반환"""
    service = InterviewService(db, user)
    return await service.create_session(req)


@router.post("/sessions/stream")
async def create_session_stream(
    req: SessionCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """
    면접 세션 생성 (진행 상황 스트리밍)

    첫 질문까지 90~140초가 걸려 화면이 멈춰 보이는 문제 때문에 만들었다.
    위 /sessions 와 결과는 같고, 준비 과정을 단계별로 흘려보내는 점만 다르다.

    한 줄에 JSON 하나씩 내려간다.

        {"type":"progress","stage":"parsing","label":"이력서·채용공고 읽는 중"}
        {"type":"progress","stage":"matching","label":"직무 적합도 분석 중"}
        {"type":"progress","stage":"generating","label":"맞춤 질문 만드는 중"}
        {"type":"done","session_id":"...","first_question":"..."}

    progress 는 "지금부터 이 단계" 라는 뜻이다. stage 는 고정값이고 label 은 참고용이라,
    화면 문구를 바꾸려면 stage 로 매핑하면 된다.

    거절해야 하는 요청(인증·사용량 초과·소유권)은 prepare_session 이 스트리밍 시작 전에
    걸러내므로 지금처럼 상태 코드로 나간다. 본문이 나가기 시작한 뒤에 생긴 오류만
    {"type":"error","detail":"..."} 로 내려간다.
    """
    service = InterviewService(db, user)
    prepared = service.prepare_session(req)

    async def lines():
        async for event in stream_session(prepared):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """
    내 면접 기록 목록 (최신순).

    마이페이지 표에 필요한 점수·영상 유무를 한 번에 내보내고, 상단 통계 카드용
    집계는 summary 로 따로 준다. summary 는 limit 과 무관하게 전체를 대상으로 한다.
    """
    service = InterviewService(db, user)
    return service.list_sessions(limit)


@router.post("/sessions/{session_id}/chat", response_model=ChatResponse)
async def chat(
    session_id: str,
    req: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """답변 전송 → 다음 질문 + 실시간 점수/피드백 반환"""
    service = InterviewService(db, user)
    return await service.process_answer(session_id, req.answer, req.input_type)


@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """
    면접 종료.

    중도 종료여도 리포트를 생성한다. 그래프에 종료 신호를 넣어 report_generator 를
    태우므로 LLM 호출이 발생하고 수십 초가 걸릴 수 있다.
    """
    service = InterviewService(db, user)
    await service.end_session(session_id)
    return {"message": "면접이 종료되었습니다."}


@router.get("/sessions/{session_id}/result", response_model=ResultResponse)
async def get_result(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """면접 결과 리포트 조회"""
    service = InterviewService(db, user)
    return await service.get_result(session_id)


@router.get("/sessions/{session_id}/feedback", response_model=FeedbackResponse)
async def get_feedback(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """질문별 피드백 보고서 조회"""
    service = InterviewService(db, user)
    return await service.get_feedback(session_id)


@router.get(
    "/sessions/{session_id}/resume-optimization",
    response_model=ResumeOptimizationResponse,
)
async def get_resume_optimization(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """
    이력서 최적화 제안 조회.

    면접 종료 직전 resume_optimizer 가 만든 결과다. 같은 이력서로 여러 번 면접하면
    결과도 여러 개라 resume_id 가 아니라 세션 단위로 조회한다.
    """
    service = InterviewService(db, user)
    return await service.get_resume_optimization(session_id)


# ── 영상 분석 ──────────────────────────────────────────
# 시선 지표는 면접 점수(5개 역량)에 반영하지 않는 보조 코칭 값이라 결과 리포트와 분리돼 있다.
#
# 경로가 두 벌인 이유: video/README.md 가 /interview/{id}/video 로 합의돼 있고,
# 이 라우터의 나머지 엔드포인트는 /interview/sessions/{id}/... 컨벤션을 쓴다.
# 둘 다 받아 어느 쪽으로 붙여도 동작하게 한다. 세그먼트 수가 달라 충돌하지 않는다.
#
# 프론트는 업로드·조회 모두 짧은 쪽(/interview/{id}/video, /interview/{id}/video-metrics)을
# 부른다. 긴 쪽은 지금 부르는 곳이 없으므로, 한쪽으로 모으려면 긴 쪽을 지우면 된다.

@router.post("/{session_id}/video", response_model=VideoUploadResponse, status_code=202)
@router.post("/sessions/{session_id}/video", response_model=VideoUploadResponse, status_code=202)
async def upload_video(
    session_id: str,
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """
    면접 영상 업로드. (multipart/form-data, 필드명 video)

    분석은 몇 분씩 걸리므로 여기서 기다리지 않는다. 저장만 하고 202 로 접수한 뒤
    /video-metrics 를 폴링해서 status 가 done 이 되는 것을 확인하면 된다.
    """
    service = VideoService(db, user)
    response = await service.upload(session_id, video)
    # add_task 를 commit 이후에 걸어야 백그라운드 쪽에서 행을 못 찾는 일이 없다.
    # (동기 함수라 FastAPI 가 스레드풀에서 돌린다 → 이벤트 루프를 막지 않는다)
    background_tasks.add_task(video_service.analyze, response.video_id)
    return response


@router.get("/{session_id}/video-metrics", response_model=VideoMetricsResponse)
@router.get("/sessions/{session_id}/video-metrics", response_model=VideoMetricsResponse)
def get_video_metrics(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """영상 분석 상태/결과 조회. status: analyzing → done 또는 failed."""
    service = VideoService(db, user)
    return service.metrics(session_id)