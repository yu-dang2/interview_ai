"""
면접 관련 Pydantic 스키마

점수는 전부 0~100 스케일이다. agent 쪽 프롬프트(answer_evaluator, report_generator)와
topic_router 의 THRESHOLD=70 이 모두 이 스케일을 전제한다.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

Score = Annotated[int, Field(ge=0, le=100)]


# ── 세션 생성 ──────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    resume_id: int
    jd_id: int
    # agent/graph/nodes/persona_selector.py 의 PERSONA_MAP 키와 1:1로 맞춰져 있다.
    persona: Literal["기술 리드", "인사 담당자", "임원 면접관"]


class SessionCreateResponse(BaseModel):
    session_id: str
    first_question: str


# ── 채팅 ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    answer: str
    # "voice" 면 answer_evaluator 가 STT 말버릇을 감점하지 않도록 프롬프트를 덧붙인다.
    input_type: Literal["text", "voice"] = "text"


class RealtimeScore(BaseModel):
    total: Score
    logic: Score
    communication: Score
    expertise: Score
    attitude: Score
    problem_solving: Score


class RealtimeFeedbackItem(BaseModel):
    type: Literal["positive", "suggestion"]
    text: str


class ChatResponse(BaseModel):
    next_question: str
    question_type: Literal["follow_up", "next", "end"]
    realtime_score: RealtimeScore
    realtime_feedback: list[RealtimeFeedbackItem]


# ── 결과 리포트 ────────────────────────────────────────

class RadarChart(BaseModel):
    logic: Score
    communication: Score
    expertise: Score
    attitude: Score
    problem_solving: Score


class ResultSummary(BaseModel):
    strength: str
    improvement: str
    recommendation: str


class ResultResponse(BaseModel):
    session_id: str
    # 화면 상단에 "OO 면접관"으로 표시된다. 이 값이 없으면 프론트가 기본값으로
    # 폴백해 임원 면접을 봤는데 기술 리드로 적히는 문제가 생긴다.
    persona: str | None = None
    resume_score: Score
    interview_score: Score
    total_score: Score
    grade: str | None = None       # report_generator 가 내주는 등급 (A+, B+ ...)
    radar_chart: RadarChart
    summary: ResultSummary


# ── 피드백 보고서 ──────────────────────────────────────

class FeedbackItem(BaseModel):
    question_number: int
    question: str
    my_answer: str
    score: Score
    improved_answer: str


class FeedbackResponse(BaseModel):
    total_questions: int
    average_score: Score
    feedbacks: list[FeedbackItem]


# ── 이력서 최적화 ──────────────────────────────────────

class ResumeSuggestion(BaseModel):
    id: str | int | None = None
    section: str = ""          # 경력 요약 / 프로젝트 성과 / 기술 스택 ...
    original: str = ""
    improved: str = ""
    reason: str = ""


class ResumeOptimizationResponse(BaseModel):
    """
    면접 종료 시 resume_optimizer 가 만든 제안.

    면접 결과에 딸린 값이라 세션 단위로 조회한다. 같은 이력서로 여러 번 면접하면
    결과도 여러 개이므로 resume_id 만으로는 어느 것인지 정할 수 없다.
    """

    session_id: str
    resume_id: int | None = None
    matched_keywords: list[str] = []
    suggestions: list[ResumeSuggestion] = []


# ── 면접 기록 목록 (마이페이지) ────────────────────────

class SessionListItem(BaseModel):
    session_id: str
    created_at: datetime
    persona: str | None = None
    status: str

    # 아직 끝나지 않았거나 중단된 면접은 결과가 없어 전부 None 이다.
    resume_score: Score | None = None
    interview_score: Score | None = None
    total_score: Score | None = None
    grade: str | None = None

    has_video: bool = False
    # 영상 재생용 경로. 인증이 필요해 <video src> 에 바로 넣을 수 없다.
    video_url: str | None = None


class SessionListSummary(BaseModel):
    """
    마이페이지 상단 통계 카드용. 목록이 limit 으로 잘려도 값이 맞도록
    전체 결과를 대상으로 따로 집계한다.

    리포트를 JSON 한 컬럼에 넣던 시절에는 이 집계가 불가능했다.
    """

    total_interviews: int                      # 결과가 남은(완료된) 면접 수
    average_interview_score: float | None = None
    latest_resume_score: Score | None = None


class SessionListResponse(BaseModel):
    total: int                                 # 세션 전체 개수 (limit 과 무관)
    summary: SessionListSummary
    sessions: list[SessionListItem]
