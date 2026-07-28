"""
면접 관련 Pydantic 스키마

점수는 전부 0~100 스케일이다. agent 쪽 프롬프트(answer_evaluator, report_generator)와
topic_router 의 THRESHOLD=70 이 모두 이 스케일을 전제한다.
"""

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
