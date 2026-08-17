"""
면접 서비스

FastAPI 라우터와 LangGraph 에이전트를 연결하는 레이어.

세션 상태는 LangGraph 체크포인터가 thread_id(=session_id) 로 들고 있고,
DB에는 조회용 기록(세션/대화/결과)을 남긴다.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.config import (
    CLOSING_MESSAGE,
    INTERVIEW_ACTIVE_LIMIT,
    INTERVIEW_DAILY_LIMIT,
    INTERVIEW_STALE_AFTER_MIN,
    INTERVIEW_TIME_LIMIT_MIN,
)
from backend.models.models import (
    JD,
    InterviewMessage,
    InterviewQuestionFeedback,
    InterviewResult,
    InterviewResumeOptimization,
    InterviewSession,
    InterviewVideo,
    Resume,
    User,
)
from backend.schemas.interview import (
    ChatResponse,
    FeedbackResponse,
    ResultResponse,
    ResumeOptimizationResponse,
    ResumeSuggestion,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionListItem,
    SessionListResponse,
    SessionListSummary,
)
from backend.services import graph_runner, report_mapper

logger = logging.getLogger(__name__)

_NO_REPORT = HTTPException(
    status_code=409,
    detail="면접이 아직 종료되지 않아 결과 리포트가 없습니다.",
)


class InterviewService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    # ── 내부 헬퍼 ──────────────────────────────────────

    def _get_session(self, session_id: str) -> InterviewSession:
        """내 세션만 반환. 없거나 남의 것이면 404.

        답변 전송·종료·결과 조회가 모두 이 헬퍼를 거치므로, 소유권 검사를 여기 한 곳에
        두면 전체 경로에 적용된다.
        """
        session = self.db.get(InterviewSession, session_id)
        if session is None or session.users_user_id != self.user.user_id:
            raise HTTPException(status_code=404, detail="면접 기록을 찾을 수 없습니다.")
        return session

    def _get_result_row(self, session_id: str) -> InterviewResult | None:
        """저장된 결과 행. 면접이 끝났다면 여기에 완전한 리포트가 들어 있다."""
        return (
            self.db.query(InterviewResult)
            .filter(InterviewResult.interview_sessions_session_id == session_id)
            .first()
        )

    async def _checkpoint_values(self, session_id: str) -> dict:
        """
        체크포인트의 State 를 읽는 폴백.

        정상 흐름이라면 면접 종료 시 _save_result 가 DB 에 남기므로 여기까지 오지 않는다.
        체크포인트 파일은 언제든 지울 수 있는 임시 데이터라 이쪽을 우선하면 안 된다.
        """
        values, _ = await graph_runner.snapshot(session_id)
        return values

    def _log_message(self, session_id: str, role: str, content: str, eval_score: int = 0) -> None:
        self.db.add(
            InterviewMessage(
                role=role,
                content=content,
                eval_score=eval_score,
                interview_sessions_session_id=session_id,
            )
        )

    # ── 사용량 제한 ────────────────────────────────────

    def _sweep_stale_sessions(self) -> int:
        """
        오래 방치된 active 세션을 abandoned 로 정리하고 처리한 개수를 반환한다.

        브라우저를 그냥 닫으면 종료 요청이 오지 않아 세션이 계속 active 로 남는다.
        그대로 두면 동시 진행 제한에 걸려 본인이 새 면접을 시작하지 못한다.
        (실제로 7/29~8/11 사이 14건이 쌓여 429 가 났다)

        기준은 created_at 이다. 마지막 활동 시각 컬럼을 두는 편이 정확하지만,
        interview_sessions 에는 이미 데이터가 있어 컬럼을 더하려면 테이블을 다시
        만들어야 한다. 면접이 제한 시간 안에 끝나므로 생성 시각만으로 충분하고,
        그 두 배를 기다려 진행 중인 면접은 건드리지 않는다.
        """
        if INTERVIEW_STALE_AFTER_MIN <= 0:
            return 0

        cutoff = datetime.now() - timedelta(minutes=INTERVIEW_STALE_AFTER_MIN)
        stale = (
            self.db.query(InterviewSession)
            .filter(
                InterviewSession.users_user_id == self.user.user_id,
                InterviewSession.status == "active",
                InterviewSession.created_at < cutoff,
            )
            .all()
        )
        for session in stale:
            session.status = "abandoned"
        if stale:
            self.db.commit()
            logger.info(
                "방치된 면접 %d건을 정리했습니다 (user_id=%s, %d분 초과)",
                len(stale), self.user.user_id, INTERVIEW_STALE_AFTER_MIN,
            )
        return len(stale)

    def _check_usage_limit(self) -> None:
        """
        면접 생성 횟수를 제한한다.

        요청 수를 재는 일반적인 rate limit 대신 세션 생성만 막는 이유: 비용은 LLM
        호출에서 발생하고, 면접 1회에 십수 번이 나간다. 조회 API 를 아무리 많이 불러도
        비용이 안 드는 반면 세션 생성은 한 번이 비싸다.

        Redis 없이 DB 카운트로 센다. 사용자 수가 적어 이 정도로 충분하고,
        인프라를 늘리지 않아도 된다.
        """
        # 세는 것보다 먼저 정리한다. 방치된 세션이 동시 제한을 차지하고 있으면
        # 실제로는 진행 중인 게 없는데도 거절된다.
        self._sweep_stale_sessions()

        if INTERVIEW_DAILY_LIMIT > 0:
            since = datetime.now() - timedelta(days=1)
            recent = (
                self.db.query(func.count(InterviewSession.session_id))
                .filter(
                    InterviewSession.users_user_id == self.user.user_id,
                    InterviewSession.created_at >= since,
                )
                .scalar()
            )
            if recent >= INTERVIEW_DAILY_LIMIT:
                raise HTTPException(
                    status_code=429,
                    detail=f"하루에 면접을 {INTERVIEW_DAILY_LIMIT}회까지 진행할 수 있습니다. "
                           "내일 다시 시도해주세요.",
                )

        if INTERVIEW_ACTIVE_LIMIT > 0:
            active = (
                self.db.query(func.count(InterviewSession.session_id))
                .filter(
                    InterviewSession.users_user_id == self.user.user_id,
                    InterviewSession.status == "active",
                )
                .scalar()
            )
            if active >= INTERVIEW_ACTIVE_LIMIT:
                raise HTTPException(
                    status_code=429,
                    detail=f"진행 중인 면접이 {INTERVIEW_ACTIVE_LIMIT}개입니다. "
                           "기존 면접을 끝내거나 종료한 뒤 새로 시작해주세요.",
                )

    # ── 세션 생성 ──────────────────────────────────────

    async def create_session(self, req: SessionCreateRequest) -> SessionCreateResponse:
        # LLM 호출 전에 막는다. 그래프를 돌린 뒤 거절하면 비용은 이미 나간 뒤다.
        self._check_usage_limit()

        # 남의 JD·이력서로 세션을 만들 수 없도록 소유자까지 확인한다.
        jd = self.db.get(JD, req.jd_id)
        if jd is None or jd.users_user_id != self.user.user_id:
            raise HTTPException(status_code=404, detail="선택한 직무 기술서를 찾을 수 없습니다.")

        resume = self.db.get(Resume, req.resume_id)
        if resume is None or resume.users_user_id != self.user.user_id:
            raise HTTPException(
                status_code=404, detail="선택한 이력서를 찾을 수 없습니다."
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
            # 답변마다 resume() 이 덮어쓴다. 첫 질문 생성 시점에는 답변이 없으므로 "text".
            "input_type": "text",
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
                users_user_id=self.user.user_id,
                jds_jd_id=jd.jd_id,
                resumes_resume_id=resume.resume_id,
            )
        )
        self._log_message(session_id, "assistant", first_question)
        self.db.commit()

        return SessionCreateResponse(session_id=session_id, first_question=first_question)

    # ── 답변 처리 ──────────────────────────────────────

    async def process_answer(
        self, session_id: str, answer: str, input_type: str = "text"
    ) -> ChatResponse:
        session = self._get_session(session_id)

        _, finished = await graph_runner.snapshot(session_id)
        if finished:
            raise HTTPException(status_code=409, detail="이미 종료된 면접입니다.")

        # 제한 시간 확인. 화면 타이머가 0이 되면 프론트가 종료를 걸어주지만, 탭을
        # 열어둔 채 계속 답변하면 서버가 막을 방법이 없다. 여기서 거절만 하고
        # 리포트를 자동 생성하지는 않는다. 종료는 LLM 을 두 번 부르는 동작이라
        # 사용자가 종료 버튼을 눌렀을 때 하는 편이 낫다.
        if INTERVIEW_TIME_LIMIT_MIN > 0 and session.created_at:
            elapsed_min = (datetime.now() - session.created_at).total_seconds() / 60
            if elapsed_min > INTERVIEW_TIME_LIMIT_MIN:
                raise HTTPException(
                    status_code=409,
                    detail=f"면접 시간 {INTERVIEW_TIME_LIMIT_MIN}분이 지났습니다. "
                           "면접을 종료하고 결과를 확인해주세요.",
                )

        values = await graph_runner.resume(session_id, answer, input_type)
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
        """
        리포트를 컬럼으로 펴서 저장한다.

        match_result 를 함께 읽는 게 중요하다. resume_score 는 여기서만 계산할 수 있고,
        저장하지 않으면 체크포인트가 사라진 뒤 0 으로 떨어진다.
        """
        report = values.get("report_result") or {}

        result = InterviewResult(
            **report_mapper.to_result_columns(values),
            eval_keywords=json.dumps(values.get("eval_keywords", []), ensure_ascii=False),
            weakness_areas=json.dumps(values.get("weakness_areas", []), ensure_ascii=False),
            # 컬럼 매핑이 틀렸을 때 재계산할 수 있도록 원본을 남긴다.
            raw_report=json.dumps(report, ensure_ascii=False),
            interview_sessions_session_id=session_id,
        )
        result.question_feedbacks = [
            InterviewQuestionFeedback(**row)
            for row in report_mapper.to_question_feedback_rows(report)
        ]

        # resume_optimizer 가 종료 직전에 만든다. 없을 수도 있어 있을 때만 붙인다.
        optimization = values.get("resume_optimization") or {}
        if any(
            optimization.get(key)
            for key in ("matched_keywords", "missing_keywords", "suggestions")
        ):
            result.resume_optimization = InterviewResumeOptimization(
                matched_keywords=json.dumps(
                    optimization.get("matched_keywords") or [], ensure_ascii=False
                ),
                missing_keywords=json.dumps(
                    optimization.get("missing_keywords") or [], ensure_ascii=False
                ),
                suggestions=json.dumps(
                    optimization.get("suggestions") or [], ensure_ascii=False
                ),
            )

        self.db.add(result)

    # ── 기록 목록 (마이페이지) ─────────────────────────

    def list_sessions(self, limit: int = 20) -> SessionListResponse:
        """
        내 면접 기록을 최신순으로. 결과·영상 유무를 한 번에 붙여 내보낸다.

        영상은 세션당 여러 개일 수 있어서 outerjoin 하면 세션 행이 중복된다.
        그래서 세션↔결과만 조인(1:1)하고, 영상은 별도 한 방 조회로 붙인다.
        """
        base = self.db.query(InterviewSession).filter(
            InterviewSession.users_user_id == self.user.user_id
        )
        total = base.count()

        rows = (
            base.outerjoin(
                InterviewResult,
                InterviewResult.interview_sessions_session_id == InterviewSession.session_id,
            )
            .with_entities(InterviewSession, InterviewResult)
            .order_by(InterviewSession.created_at.desc())
            .limit(limit)
            .all()
        )

        # 세션별 최신 영상 id. 목록에 나온 세션만 조회한다.
        session_ids = [session.session_id for session, _ in rows]
        video_map = {}
        if session_ids:
            video_map = dict(
                self.db.query(
                    InterviewVideo.interview_sessions_session_id,
                    func.max(InterviewVideo.video_id),
                )
                .filter(InterviewVideo.interview_sessions_session_id.in_(session_ids))
                .group_by(InterviewVideo.interview_sessions_session_id)
                .all()
            )

        sessions = []
        for session, result in rows:
            video_id = video_map.get(session.session_id)
            sessions.append(
                SessionListItem(
                    session_id=session.session_id,
                    created_at=session.created_at,
                    persona=session.persona,
                    status=session.status,
                    resume_score=result.resume_score if result else None,
                    interview_score=result.interview_score if result else None,
                    total_score=result.total_score if result else None,
                    grade=result.grade if result else None,
                    has_video=video_id is not None,
                    video_url=f"/mypage/videos/{video_id}/file" if video_id else None,
                )
            )

        return SessionListResponse(total=total, summary=self._summary(), sessions=sessions)

    def _summary(self) -> SessionListSummary:
        """상단 통계 카드용 집계. 목록이 잘려도 맞도록 전체 결과를 대상으로 한다."""
        results = (
            self.db.query(InterviewResult)
            .join(
                InterviewSession,
                InterviewResult.interview_sessions_session_id == InterviewSession.session_id,
            )
            .filter(InterviewSession.users_user_id == self.user.user_id)
        )

        count, avg_interview = results.with_entities(
            func.count(InterviewResult.result_id),
            func.avg(InterviewResult.interview_score),
        ).one()

        # "현재 이력서 점수" 는 가장 최근 면접에서 산출된 값이다.
        latest = results.order_by(InterviewResult.created_at.desc()).first()

        return SessionListSummary(
            total_interviews=count or 0,
            average_interview_score=round(float(avg_interview), 1) if avg_interview else None,
            latest_resume_score=latest.resume_score if latest else None,
        )

    # ── 종료 / 조회 ────────────────────────────────────

    async def end_session(self, session_id: str) -> None:
        """
        면접을 중도 종료하고 리포트까지 만든다.

        예전에는 status 만 바꿔서, 종료 버튼으로 끝내면 리포트가 생성되지 않았다.
        (10턴을 완주한 경우에만 report_generator 가 돌았다.)
        이제 그래프에 종료 신호를 넣어 report_generator 를 태운다.
        """
        session = self._get_session(session_id)

        if self._get_result_row(session_id) is None:
            values = await graph_runner.finish(session_id)
            if values.get("report_result"):
                self._save_result(session_id, values)

        session.status = "finished"
        self.db.commit()

    async def get_result(self, session_id: str) -> ResultResponse:
        session = self._get_session(session_id)

        # DB 우선. 체크포인트를 지워도 완료된 면접의 점수는 그대로 나와야 한다.
        row = self._get_result_row(session_id)
        if row is not None:
            return report_mapper.to_result_from_row(session_id, row, session.persona)

        values = await self._checkpoint_values(session_id)
        if not values.get("report_result"):
            raise _NO_REPORT
        return report_mapper.to_result(session_id, values, session.persona)

    async def get_resume_optimization(self, session_id: str) -> ResumeOptimizationResponse:
        """면접 종료 시 생성된 이력서 최적화 제안."""
        session = self._get_session(session_id)

        row = self._get_result_row(session_id)
        optimization = row.resume_optimization if row else None

        if optimization is None:
            # 아직 저장 전이면 체크포인트에서 읽어본다.
            values = await self._checkpoint_values(session_id)
            data = values.get("resume_optimization") or {}
            if not any(
                data.get(key)
                for key in ("matched_keywords", "missing_keywords", "suggestions")
            ):
                raise HTTPException(
                    status_code=409,
                    detail="면접이 아직 종료되지 않아 이력서 최적화 결과가 없습니다.",
                )
            matched = data.get("matched_keywords") or []
            missing = data.get("missing_keywords") or []
            suggestions = data.get("suggestions") or []
        else:
            matched = json.loads(optimization.matched_keywords or "[]")
            missing = json.loads(optimization.missing_keywords or "[]")
            suggestions = json.loads(optimization.suggestions or "[]")

        return ResumeOptimizationResponse(
            session_id=session_id,
            resume_id=session.resumes_resume_id,
            matched_keywords=[str(k) for k in matched],
            missing_keywords=[str(k) for k in missing],
            suggestions=[ResumeSuggestion(**s) for s in suggestions if isinstance(s, dict)],
        )

    async def get_feedback(self, session_id: str) -> FeedbackResponse:
        self._get_session(session_id)

        row = self._get_result_row(session_id)
        if row is not None:
            return report_mapper.to_feedback_from_rows(row.question_feedbacks)

        values = await self._checkpoint_values(session_id)
        if not values.get("report_result"):
            raise _NO_REPORT
        return report_mapper.to_feedback(values["report_result"])
