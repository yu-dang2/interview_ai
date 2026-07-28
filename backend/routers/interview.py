"""
면접 라우터

모든 엔드포인트가 인증을 요구하며, 세션은 생성한 사용자에게 귀속된다.
남의 세션은 조회되지 않는다.

엔드포인트:
    POST /interview/sessions           - 면접 세션 생성 (면접 시작)
    POST /interview/sessions/{id}/chat - 텍스트 답변 전송
    POST /interview/sessions/{id}/end  - 면접 종료
    GET  /interview/sessions/{id}/result   - 결과 리포트 조회
    GET  /interview/sessions/{id}/feedback - 질문별 피드백 보고서 조회
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.core.deps import current_user
from backend.database import get_db
from backend.models.models import User
from backend.schemas.interview import (
    SessionCreateRequest,
    SessionCreateResponse,
    ChatRequest,
    ChatResponse,
    ResultResponse,
    FeedbackResponse,
)
from backend.services.interview_service import InterviewService

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
def end_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """면접 종료"""
    service = InterviewService(db, user)
    service.end_session(session_id)
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