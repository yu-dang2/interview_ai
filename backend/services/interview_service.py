"""
면접 서비스

FastAPI 라우터와 LangGraph 에이전트를 연결하는 레이어.
"""

import uuid
from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

try:
    from agent.graph.interview_agent import graph
except Exception as e:
    print(f"[경고] agent 로드 실패 (agent 미완성): {e}")
    graph = None

from backend.schemas.interview import (
    SessionCreateRequest,
    SessionCreateResponse,
    ChatResponse,
    RealtimeScore,
    RealtimeFeedbackItem,
    ResultResponse,
    RadarChart,
    ResultSummary,
    FeedbackResponse,
    FeedbackItem,
)

# 세션 상태 임시 저장 (추후 DB로 교체 권장)
_session_store: dict = {}

PERSONA_MAP = {
    "기술 리드": "깐깐한 기술 팀장",
    "인사 담당자": "공감형 인사 담당자",
    "임원 면접관": "전략적 비즈니스 역량 검증",
}


class InterviewService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, req: SessionCreateRequest) -> SessionCreateResponse:
        if graph is None:
            raise RuntimeError("agent 미완성 - 이현주 작업 완료 후 사용 가능")
        session_id = str(uuid.uuid4())
        jd_raw = f"jd_id={req.jd_id} 에 해당하는 JD 텍스트"
        resume_raw = f"resume_id={req.resume_id} 에 해당하는 이력서 텍스트"
        state = {
            "messages": [],
            "jd_raw": jd_raw,
            "resume_raw": resume_raw,
            "jd_parsed": {},
            "resume_parsed": {},
            "match_result": {},
            "question_list": [],
            "current_question_index": 0,
            "persona": PERSONA_MAP.get(req.persona, "깐깐한 기술 팀장"),
            "eval_score": 0,
            "eval_result": {},
            "eval_keywords": [],
            "weakness_areas": [],
            "follow_up_count": 0,
            "turn_count": 0,
            "is_finished": False,
        }
        current_state = graph.invoke(state)
        _session_store[session_id] = current_state
        first_question = current_state["messages"][-1].content if current_state["messages"] else ""
        return SessionCreateResponse(
            session_id=session_id,
            first_question=first_question,
        )

    def process_answer(self, session_id: str, answer: str) -> ChatResponse:
        if graph is None:
            raise RuntimeError("agent 미완성 - 이현주 작업 완료 후 사용 가능")
        current_state = _session_store.get(session_id)
        if not current_state:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")
        current_state["messages"] = current_state["messages"] + [HumanMessage(content=answer)]
        from langgraph.graph import StateGraph, START, END
        from agent.graph.state import InterviewState
        from agent.graph.nodes.answer_evaluator import answer_evaluator
        from agent.graph.nodes.follow_up_generator import follow_up_generator
        from agent.graph.nodes.report_generator import report_generator
        from agent.graph.edges.topic_router import topic_router
        sub_graph = StateGraph(InterviewState)
        sub_graph.add_node("answer_evaluator", answer_evaluator)
        sub_graph.add_node("follow_up_generator", follow_up_generator)
        sub_graph.add_node("report_generator", report_generator)
        sub_graph.add_edge(START, "answer_evaluator")
        sub_graph.add_conditional_edges("answer_evaluator", topic_router)
        sub_graph.add_edge("follow_up_generator", "answer_evaluator")
        sub_graph.add_edge("report_generator", END)
        sub_graph = sub_graph.compile()
        current_state = sub_graph.invoke(current_state)
        _session_store[session_id] = current_state
        next_question = current_state["messages"][-1].content if current_state["messages"] else ""
        is_finished = current_state.get("is_finished", False)
        follow_up_count = current_state.get("follow_up_count", 0)
        if is_finished:
            question_type = "end"
        elif follow_up_count > 0:
            question_type = "follow_up"
        else:
            question_type = "next"
        eval_result = current_state.get("eval_result", {})
        scores = eval_result.get("scores", {})
        realtime_score = RealtimeScore(
            total=current_state.get("eval_score", 0) * 10,
            logic=scores.get("logic", 0),
            communication=scores.get("communication", 0),
            expertise=scores.get("expertise", 0),
            attitude=scores.get("attitude", 0),
            problem_solving=scores.get("problem_solving", 0),
        )
        strengths = eval_result.get("strengths", [])
        weaknesses = eval_result.get("weaknesses", [])
        realtime_feedback = (
            [RealtimeFeedbackItem(type="positive", text=s) for s in strengths]
            + [RealtimeFeedbackItem(type="suggestion", text=w) for w in weaknesses]
        )
        return ChatResponse(
            next_question=next_question,
            question_type=question_type,
            realtime_score=realtime_score,
            realtime_feedback=realtime_feedback,
        )

    def end_session(self, session_id: str):
        if session_id in _session_store:
            del _session_store[session_id]

    def get_result(self, session_id: str) -> ResultResponse:
        current_state = _session_store.get(session_id)
        if not current_state:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")
        eval_keywords = current_state.get("eval_keywords", [])
        weakness_areas = current_state.get("weakness_areas", [])
        return ResultResponse(
            session_id=session_id,
            resume_score=0,
            interview_score=current_state.get("eval_score", 0) * 10,
            total_score=0,
            radar_chart=RadarChart(
                logic=0,
                communication=0,
                expertise=0,
                attitude=0,
                problem_solving=0,
            ),
            summary=ResultSummary(
                strength=", ".join(eval_keywords) if eval_keywords else "",
                improvement=", ".join(weakness_areas) if weakness_areas else "",
                recommendation="",
            ),
        )

    def get_feedback(self, session_id: str) -> FeedbackResponse:
        current_state = _session_store.get(session_id)
        if not current_state:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")
        return FeedbackResponse(
            total_questions=current_state.get("turn_count", 0),
            average_score=current_state.get("eval_score", 0) * 10,
            feedbacks=[],
        )