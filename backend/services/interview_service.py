"""
면접 서비스

FastAPI 라우터와 LangGraph 에이전트를 연결하는 레이어.

세션 상태는 LangGraph 체크포인터가 thread_id(=session_id) 로 들고 있고,
DB에는 조회용 기록(세션/대화/결과)을 남긴다.
"""

import json
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.core.config import CLOSING_MESSAGE
from backend.models.models import JD, InterviewMessage, InterviewResult, InterviewSession, Resume
from backend.schemas.interview import (
    ChatResponse,
    FeedbackResponse,
    ResultResponse,
    SessionCreateRequest,
    SessionCreateResponse,
)
from backend.services import graph_runner, report_mapper


class InterviewService:
    def __init__(self, db: Session):
        self.db = db

    # ── 내부 헬퍼 ──────────────────────────────────────

    def _get_session(self, session_id: str) -> InterviewSession:
        session = self.db.get(InterviewSession, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"세션을 찾을 수 없습니다: {session_id}")
        return session

    async def _get_report(self, session_id: str) -> tuple[dict, dict]:
        """(report_result, match_result) 반환. 리포트가 아직 없으면 409."""
        values, _ = await graph_runner.snapshot(session_id)
        report = values.get("report_result") or {}

        if not report:
            # 체크포인트가 날아갔더라도 DB에 저장해둔 리포트로 응답할 수 있다.
            row = (
                self.db.query(InterviewResult)
                .filter(InterviewResult.interview_sessions_session_id == session_id)
                .first()
            )
            if row and row.feedback:
                report = json.loads(row.feedback)

        if not report:
            raise HTTPException(
                status_code=409,
                detail="면접이 아직 종료되지 않아 결과 리포트가 없습니다.",
            )

        return report, values.get("match_result") or {}

    def _log_message(self, session_id: str, role: str, content: str, eval_score: int = 0) -> None:
        self.db.add(
            InterviewMessage(
                role=role,
                content=content,
                eval_score=eval_score,
                interview_sessions_session_id=session_id,
            )
        )

    # ── 세션 생성 ──────────────────────────────────────

    async def create_session(self, req: SessionCreateRequest) -> SessionCreateResponse:
        jd = self.db.get(JD, req.jd_id)
        if jd is None:
            raise HTTPException(status_code=404, detail=f"JD를 찾을 수 없습니다: {req.jd_id}")

        resume = self.db.get(Resume, req.resume_id)
        if resume is None:
            raise HTTPException(
                status_code=404, detail=f"이력서를 찾을 수 없습니다: {req.resume_id}"
            )

        session_id = str(uuid.uuid4())

        init_state = {
            "messages": [],
            "jd_raw": jd.content,
            "resume_raw": resume.content,
            # persona 는 agent 의 PERSONA_MAP 키를 그대로 넘긴다. 설명 문구로 변환하면
            # persona_selector 가 인식하지 못하고 기술 리드로 폴백한다.
            "persona": req.persona,
            "jd_parsed": {},
            "resume_parsed": {},
            "match_result": {},
            "question_list": [],
            "current_question_index": 0,
            "eval_score": 0,
            "eval_result": {},
            "eval_keywords": [],
            "weakness_areas": [],
            "follow_up_count": 0,
            "turn_count": 0,
            "is_finished": False,
            "report_result": {},
        }

        values = await graph_runner.start(session_id, init_state)
        first_question = values["messages"][-1].content if values.get("messages") else ""

        self.db.add(
            InterviewSession(
                session_id=session_id,
                status="active",
                persona=req.persona,
                jd_content=jd.content,
                jds_jd_id=jd.jd_id,
                resumes_resume_id=resume.resume_id,
            )
        )
        self._log_message(session_id, "assistant", first_question)
        self.db.commit()

        return SessionCreateResponse(session_id=session_id, first_question=first_question)

    # ── 답변 처리 ──────────────────────────────────────

    async def process_answer(self, session_id: str, answer: str) -> ChatResponse:
        session = self._get_session(session_id)

        _, finished = await graph_runner.snapshot(session_id)
        if finished:
            raise HTTPException(status_code=409, detail="이미 종료된 면접입니다.")

        values = await graph_runner.resume(session_id, answer)
        _, finished = await graph_runner.snapshot(session_id)

        eval_result = values.get("eval_result") or {}
        eval_score = report_mapper.clamp(values.get("eval_score", 0))
        follow_up_count = values.get("follow_up_count", 0)

        if finished or values.get("is_finished"):
            question_type = "end"
            # report_generator 가 마지막 AIMessage 로 리포트 JSON 전체를 넣기 때문에,
            # 그 덩어리를 채팅창에 그대로 내보내지 않고 마무리 문구로 대체한다.
            next_question = CLOSING_MESSAGE
        else:
            # question_generator 는 새 질문마다 follow_up_count 를 0으로 리셋한다.
            # 따라서 0이 아니라는 건 follow_up_generator 를 거쳤다는 뜻.
            question_type = "follow_up" if follow_up_count > 0 else "next"
            next_question = values["messages"][-1].content if values.get("messages") else ""

        self._log_message(session_id, "user", answer, eval_score)
        self._log_message(session_id, "assistant", next_question)
        session.follow_up_count = follow_up_count

        if question_type == "end":
            self._save_result(session_id, values)
            session.status = "finished"

        self.db.commit()

        return ChatResponse(
            next_question=next_question,
            question_type=question_type,
            realtime_score=report_mapper.to_realtime_score(eval_result),
            realtime_feedback=report_mapper.to_realtime_feedback(eval_result),
        )

    def _save_result(self, session_id: str, values: dict) -> None:
        report = values.get("report_result") or {}
        self.db.add(
            InterviewResult(
                total_score=report_mapper.clamp(report.get("total_score", 0)),
                feedback=json.dumps(report, ensure_ascii=False),
                eval_keywords=json.dumps(values.get("eval_keywords", []), ensure_ascii=False),
                weakness_areas=json.dumps(values.get("weakness_areas", []), ensure_ascii=False),
                interview_sessions_session_id=session_id,
            )
        )

    # ── 종료 / 조회 ────────────────────────────────────

    def end_session(self, session_id: str) -> None:
        """
        세션을 종료 표시만 한다. 상태를 지워버리면 /result, /feedback 이 리포트를 읽기도 전에
        사라지므로 체크포인트도 DB 기록도 남겨둔다.
        """
        session = self._get_session(session_id)
        if session.status != "finished":
            session.status = "ended"
        self.db.commit()

    async def get_result(self, session_id: str) -> ResultResponse:
        self._get_session(session_id)
        report, match_result = await self._get_report(session_id)
        return report_mapper.to_result(session_id, report, match_result)

    async def get_feedback(self, session_id: str) -> FeedbackResponse:
        self._get_session(session_id)
        report, _ = await self._get_report(session_id)
        return report_mapper.to_feedback(report)
