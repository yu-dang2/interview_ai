"""
면접 관련 Pydantic 스키마
"""

from pydantic import BaseModel
from typing import Literal


# ── 세션 생성 ──────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    resume_id: int
    jd_id: int
    persona: Literal["기술 리드", "인사 담당자", "임원 면접관"]


class SessionCreateResponse(BaseModel):
    session_id: str
    first_question: str


# ── 채팅 ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    answer: str


class RealtimeScore(BaseModel):
    total: int
    logic: int
    communication: int
    expertise: int
    attitude: int
    problem_solving: int


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
    logic: int
    communication: int
    expertise: int
    attitude: int
    problem_solving: int


class ResultSummary(BaseModel):
    strength: str
    improvement: str
    recommendation: str


class ResultResponse(BaseModel):
    session_id: str
    resume_score: int
    interview_score: int
    total_score: int
    radar_chart: RadarChart
    summary: ResultSummary


# ── 피드백 보고서 ──────────────────────────────────────

class FeedbackItem(BaseModel):
    question_number: int
    question: str
    my_answer: str
    score: int
    improved_answer: str


class FeedbackResponse(BaseModel):
    total_questions: int
    average_score: int
    feedbacks: list[FeedbackItem]