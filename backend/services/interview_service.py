"""
면접 서비스

FastAPI 라우터와 LangGraph 에이전트를 연결하는 레이어.

세션 상태는 LangGraph 체크포인터가 thread_id(=session_id) 로 들고 있고,
DB에는 조회용 기록(세션/대화/결과)을 남긴다.
"""

import asyncio
import json
import logging
import time
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
    INTERVIEW_START_STAGES,
    INTERVIEW_TIME_LIMIT_MIN,
    RAPPORT_QUESTION_TYPES,
    RAPPORT_TRANSITION_MESSAGE,
    REPORT_POLL_INTERVAL_SEC,
    REPORT_WAIT_TIMEOUT_SEC,
)
from backend.database import SessionLocal
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

_REPORT_PENDING = HTTPException(
    status_code=503,
    detail="리포트 생성이 아직 끝나지 않았습니다. 잠시 후 새로고침해주세요.",
)

_REPORT_FAILED = HTTPException(
    status_code=500,
    detail="리포트 생성에 실패했습니다. 면접 기록에서 다시 조회해주세요.",
)

# 리포트 생성이 돌고 있는 세션.
# 중복 실행을 막는 잠금을 겸한다.
# uvicorn --workers 1 을 전제로 한다. (Dockerfile CMD)
#
# 프로세스 안에만 있어 재시작하면 비는데, 그게 의도한 바다.
# status 가 generating_report 인데 이 집합에 없는 세션은
# 생성 도중 컨테이너가 죽은 것이므로 다시 걸어야 한다.
_report_in_flight: set[str] = set()

# create_task 가 돌려준 task 를 들고 있지 않으면 GC 가 가져갈 수 있다.
_report_tasks: set[asyncio.Task] = set()


# 이 노드들이 모두 끝나면 다음 단계로 넘어간 것으로 본다. 위에서부터 순서대로 확인한다.
# question_retriever 는 jd_resume_matcher 와 함께 도는데 먼저 끝나므로, 둘 다 끝나야
# 질문 생성 단계로 본다. (실측: 검색 26초 / 매칭 61초)
_STAGE_PREREQUISITES = (
    ("matching", {"jd_parser", "resume_parser"}),
    ("generating", {"jd_resume_matcher", "question_retriever"}),
)


def _new_session_row(prepared: dict) -> InterviewSession:
    """prepare_session 이 만든 값으로 세션 행을 만든다. 일반 생성과 스트리밍이 함께 쓴다."""
    return InterviewSession(
        session_id=prepared["session_id"],
        status="active",
        persona=prepared["persona"],
        jd_content=prepared["jd_content"],
        users_user_id=prepared["user_id"],
        jds_jd_id=prepared["jd_id"],
        resumes_resume_id=prepared["resume_id"],
    )


def _stage_event(stage: str) -> dict:
    return {"type": "progress", "stage": stage, "label": INTERVIEW_START_STAGES[stage]}


async def stream_session(prepared: dict):
    """
    면접을 시작하면서 진행 단계를 이벤트로 내보낸다.

    첫 질문까지 90~140초가 걸려 화면이 멈춰 보이는 문제 때문에 만들었다.
    한 줄에 JSON 하나씩(NDJSON) 나가고, 마지막 done 이 기존 세션 생성 응답과 같다.

    DB 세션을 여기서 새로 연다. 요청 의존성으로 받은 세션은 응답 본문이 나가기 전에
    닫히므로 그대로 쓰면 안 된다.

    오류는 이벤트로 보낸다. 본문이 나가기 시작한 뒤에는 상태 코드를 바꿀 수 없다.
    거절해야 하는 경우는 prepare_session 이 스트리밍 시작 전에 이미 걸러낸다.
    """
    session_id = prepared["session_id"]

    # 첫 단계는 그래프를 돌리기 전에 보낸다. 노드 이벤트는 "끝났을 때" 오기 때문에
    # 그것만 기다리면 첫 15초 동안 화면에 아무것도 못 띄운다.
    yield _stage_event("parsing")

    finished_nodes: set[str] = set()
    sent_stages = {"parsing"}

    try:
        async for node_name in graph_runner.start_stream(session_id, prepared["init_state"]):
            finished_nodes.add(node_name)
            for stage, required in _STAGE_PREREQUISITES:
                if stage not in sent_stages and required <= finished_nodes:
                    sent_stages.add(stage)
                    yield _stage_event(stage)

        values, _ = await graph_runner.snapshot(session_id)
        first_question = values["messages"][-1].content if values.get("messages") else ""

        db = SessionLocal()
        try:
            db.add(_new_session_row(prepared))
            db.add(
                InterviewMessage(
                    role="assistant",
                    content=first_question,
                    interview_sessions_session_id=session_id,
                )
            )
            db.commit()
        finally:
            db.close()

        yield {
            "type": "done",
            "session_id": session_id,
            "first_question": first_question,
        }

    except Exception as e:
        # 세션 행을 아직 안 만들었으므로 사용량 카운트에도 잡히지 않는다.
        logger.exception("면접 시작 실패 (session_id=%s): %s", session_id, e)
        yield {
            "type": "error",
            "detail": "면접 준비 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.",
        }


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
        (실제로 7/29~8/11 사이 14건이 쌓여 429 가 발생)

        기준은 created_at. 마지막 활동 시각 컬럼을 두는 편이 정확하지만,
        interview_sessions 에는 이미 데이터가 있어 컬럼을 더하려면 테이블을 다시 만들어야한다.
        면접이 제한 시간 안에 끝나므로 생성 시각만으로 충분하고,
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

        요청 수를 재는 일반적인 rate limit 대신 세션 생성만 막는 이유: 
        비용은 LLM 호출에서 발생하고, 면접 1회에 십수 번이 나간다. 
        조회 API 를 아무리 많이 불러도 비용이 안 드는 반면 세션 생성은 한 번이 비싸다.

        Redis 없이 DB 카운트로 센다. 사용자 수가 적어 이 정도로 충분하고, 인프라를 늘리지 않아도 된다.
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

    def prepare_session(self, req: SessionCreateRequest) -> dict:
        """
        세션을 만들기 전 확인을 끝내고 그래프 초기 상태를 준비한다.

        스트리밍 응답은 본문이 나가기 시작하면 상태 코드를 바꿀 수 없다. 
        그래서 거절해야 하는 경우(사용량 초과·소유권)를 전부 여기서 끝내고, 
        스트리밍은 통과한 뒤에만 시작한다.

        ORM 객체 대신 값만 담아 돌려준다. 스트리밍 중에는 요청 때 쓰던 DB 세션이
        이미 닫혀 있어 ORM 객체를 그대로 들고 가면 쓸 수 없다.
        """
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

        return {
            "session_id": str(uuid.uuid4()),
            "user_id": self.user.user_id,
            "jd_id": jd.jd_id,
            "resume_id": resume.resume_id,
            "persona": req.persona,
            "jd_content": jd.content,
            "init_state": {
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
            },
        }

    async def create_session(self, req: SessionCreateRequest) -> SessionCreateResponse:
        prepared = self.prepare_session(req)
        session_id = prepared["session_id"]

        values = await graph_runner.start(session_id, prepared["init_state"])
        first_question = values["messages"][-1].content if values.get("messages") else ""

        self.db.add(_new_session_row(prepared))
        self._log_message(session_id, "assistant", first_question)
        self.db.commit()

        return SessionCreateResponse(session_id=session_id, first_question=first_question)

    # ── 답변 처리 ──────────────────────────────────────

    def _is_rapport_pending(self, values: dict) -> bool:
        """
        지금 답변을 기다리는 질문이 라포 형성 질문인지.

        라포 질문은 채점하지 않기로 해서 answer_evaluator 가 고정 점수(RAPPORT_NEUTRAL_SCORE=80)를 내보낸다. 
        답변 내용과 무관한 값이라 화면에 그대로 보여주면 성의 없이 답해도 80점이 뜨므로, 
        프론트가 패널을 숨길 수 있도록 응답에 표시해 준다. (8/20 확정)

        꼬리질문 차례면 라포가 아니다. question_generator 가 새 질문마다
        follow_up_count 를 0으로 되돌리므로 0이 아니면 follow_up_generator 를 거친 것이다.
        """
        if values.get("follow_up_count", 0):
            return False

        questions = values.get("question_list") or []
        index = values.get("current_question_index", 0)
        if not 0 <= index < len(questions):
            return False

        question = questions[index]
        return (
            isinstance(question, dict)
            and question.get("type") in RAPPORT_QUESTION_TYPES
        )

    def _asked_within_limit(self, session: InterviewSession) -> bool:
        """
        마지막으로 내보낸 질문이 제한 시간 안에 나갔는지.

        답변을 보낸 시각이 아니라 질문이 나간 시각을 본다. 
        29분에 받은 질문에 31분에 답하는 것까지 막으면 질문을 받고도 답할 기회가 없어진다.
        답변이 길수록 그렇게 되기 쉽다.

        유예 시간 같은 값을 따로 두지 않아도 한 번만 열린다.
        이 답변으로 나오는 다음 질문은 제한 시간을 넘긴 시각에 기록되므로 그 답변은 거절된다.

        기준 시각은 assistant 메시지의 created_at 이다. 
        질문을 내보낼 때마다 _log_message 가 행을 남기므로 별도 컬럼이 필요 없다.
        """
        row = (
            self.db.query(InterviewMessage.created_at)
            .filter(
                InterviewMessage.interview_sessions_session_id == session.session_id,
                InterviewMessage.role == "assistant",
            )
            # created_at 은 같은 초에 여러 건이 찍힐 수 있어 PK 로 정렬한다.
            .order_by(InterviewMessage.message_id.desc())
            .first()
        )
        if row is None or row[0] is None:
            return False

        elapsed_min = (row[0] - session.created_at).total_seconds() / 60
        return elapsed_min <= INTERVIEW_TIME_LIMIT_MIN

    async def process_answer(
        self, session_id: str, answer: str, input_type: str = "text"
    ) -> ChatResponse:
        session = self._get_session(session_id)

        pending, finished = await graph_runner.snapshot(session_id)
        if finished:
            raise HTTPException(status_code=409, detail="이미 종료된 면접입니다.")

        # 지금 답변하는 질문이 라포 형성 질문인지. 
        # 그래프를 재개하면 상태가 다음 질문으로 넘어가므로 재개 전에 봐둔다.
        is_rapport = self._is_rapport_pending(pending)

        # 제한 시간 확인. 화면 타이머가 0이 되면 프론트가 종료를 걸어주지만, 
        # 탭을 열어둔 채 계속 답변하면 서버가 막을 방법이 없다. 
        # 여기서 거절만 하고 리포트를 자동 생성하지는 않는다. 
        # 종료는 LLM 을 두 번 부르는 동작이라 사용자가 종료 버튼을 눌렀을 때 하는 편이 낫다.
        if INTERVIEW_TIME_LIMIT_MIN > 0 and session.created_at:
            elapsed_min = (datetime.now() - session.created_at).total_seconds() / 60
            if elapsed_min > INTERVIEW_TIME_LIMIT_MIN and not self._asked_within_limit(session):
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
            # 라포 질문에서 평가 질문으로 곧바로 넘어가면 흐름이 끊긴다. 
            # 화면에 나가는 문장에만 붙이고 그래프가 들고 있는 질문은 그대로 둔다. 
            # 노드에서 붙이면 report_generator 가 이 문구까지 질문으로 읽는다.
            if is_rapport and next_question:
                next_question = f"{RAPPORT_TRANSITION_MESSAGE}\n\n{next_question}"

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
            is_rapport=is_rapport,
            realtime_score=report_mapper.to_realtime_score(eval_result),
            realtime_feedback=report_mapper.to_realtime_feedback(eval_result),
        )

    def _realtime_scores(self, session_id: str) -> list[int]:
        """
        답변마다 매긴 실시간 평가 점수를 순서대로. 라포 질문 답변은 뺀다.

        답변을 받을 때 interview_messages 에 함께 남겨둔 값이라 다시 채점하지 않는다.
        라포 답변은 채점 대상이 아닌데도 중립 점수(80)가 들어가 있어, 평균에 섞이면 점수가 올라간다. 
        첫 질문이 라포이므로 첫 답변 하나를 뺀다.
        """
        rows = (
            self.db.query(InterviewMessage.eval_score)
            .filter(
                InterviewMessage.interview_sessions_session_id == session_id,
                InterviewMessage.role == "user",
            )
            .order_by(InterviewMessage.message_id)
            .all()
        )
        scores = [row[0] for row in rows if row[0] is not None]
        return scores[1:] if scores else []

    def _save_result(self, session_id: str, values: dict) -> None:
        """
        리포트를 컬럼으로 펴서 저장한다.

        match_result 를 함께 읽는 게 중요하다. resume_score 는 여기서만 계산할 수 있고,
        저장하지 않으면 체크포인트가 사라진 뒤 0 으로 떨어진다.

        점수는 실시간 평가 결과로 맞춘다. 같은 답변을 report_generator 가 다시 채점해서
        화면 세 곳(실시간 · 피드백 보고서 · 결과 리포트)의 숫자가 서로 달랐다.
        프롬프트도 "각 답변의 평가 결과를 종합·평균해 산출" 하도록 지시하고 있어
        방향은 같고, 그 계산을 여기서 확실히 한다.
        """
        report = values.get("report_result") or {}

        feedback_rows = report_mapper.to_question_feedback_rows(report)
        realtime = self._realtime_scores(session_id)

        # 답변 수와 피드백 항목 수가 같을 때만 점수를 바꿔 끼운다. 
        # 꼬리질문이 섞이거나 리포트가 항목을 합치면 개수가 어긋나는데, 
        # 그때 순서로 짝지으면 엉뚱한 질문에 엉뚱한 점수가 붙는다. 
        # 어긋나면 리포트 점수를 그대로 두고 로그만 남긴다.
        if realtime and len(realtime) == len(feedback_rows):
            for row, score in zip(feedback_rows, realtime):
                row["score"] = score
        elif realtime:
            logger.warning(
                "실시간 점수 %d개와 리포트 피드백 %d개가 맞지 않아 점수를 그대로 둡니다 "
                "(session_id=%s)",
                len(realtime), len(feedback_rows), session_id,
            )

        # 면접 점수는 질문별 점수의 평균이다. 
        # 위에서 바꿔 끼웠으면 실시간 평균과 같아지고,
        # 개수가 어긋나 그대로 뒀으면 최소한 리포트 안에서는 총점과 질문별이 맞는다.
        interview_score = report_mapper.average_score([r["score"] for r in feedback_rows])

        result = InterviewResult(
            **report_mapper.to_result_columns(values, interview_score=interview_score),
            eval_keywords=json.dumps(values.get("eval_keywords", []), ensure_ascii=False),
            weakness_areas=json.dumps(values.get("weakness_areas", []), ensure_ascii=False),
            # 컬럼 매핑이 틀렸을 때 재계산할 수 있도록 원본을 남긴다.
            raw_report=json.dumps(report, ensure_ascii=False),
            interview_sessions_session_id=session_id,
        )
        result.question_feedbacks = [
            InterviewQuestionFeedback(**row) for row in feedback_rows
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

    def accept_end(self, session_id: str) -> bool:
        """
        면접 종료를 접수한다. 리포트는 여기서 만들지 않고, 라우터가 백그라운드로 건다.

        - 분리 이유
        리포트 생성은 LLM 을 여러 번 호출해 수십 초 걸린다.
        요청이 그만큼 열려 있으면 중간 구간(브라우저·CDN·프록시)의 타임아웃에 끊기는데,
        uvicorn 은 연결이 끊겨도 핸들러를 중단하지 않아 리포트는 생성되지만 완성 신호만 전달되지 않는다.
        이때 재요청이 오면 결과 행이 아직 없어 리포트를 두 번 만든다.
        그래서 /end 응답으로 완성을 알리지 않고, 완성은 GET /result 가 상태를 보고 판단한다.

        - 설명
        분리의 부작용으로, 접수만 되고 생성이 안 걸리면
        세션이 generating_report 상태로 남아 주체 없이 멈춘다.
        이를 막으려고 접수가 '라우터가 생성 작업을 걸어야 하는지'를 판단해 반환한다.

        - 반환값 (라우터에 주는 지시)
        True  → 처음 접수했다. 라우터가 generate_report 를 백그라운드로 건다.
        False → 이미 리포트가 있거나 생성이 돌고 있다. 그대로 응답한다.
        """
        session = self._get_session(session_id)

        if self._get_result_row(session_id) is not None:
            # 10턴을 완주하면 마지막 /chat 이 이미 만들어 둔다.
            # 상태만 맞춘다.
            session.status = "finished"
            self.db.commit()
            return False

        if session_id in _report_in_flight:
            # 30분 초과 경로는 /end 가 두 번 불린다.
            # (Streamlit 서버가 한 번, 브라우저 오버레이가 한 번)
            # 막지 않으면 리포트가 두 번 생성된다.
            return False

        # add_task 가 걸리기 전에 같은 요청이 또 들어와도 여기서 막힌다.
        _report_in_flight.add(session_id)
        session.status = "generating_report"
        self.db.commit()
        return True

    async def get_result(self, session_id: str) -> ResultResponse:
        session = self._get_session(session_id)

        # DB 우선. 체크포인트를 지워도 완료된 면접의 점수는 그대로 나와야 한다.
        row = self._get_result_row(session_id)
        if row is not None:
            return report_mapper.to_result_from_row(session_id, row, session.persona)

        # 접수만 끝난 상태로 들어오는 경우다.
        # 완성을 /end 응답으로 알리지 않기 때문에 여기서 기다려 준다.
        if session.status == "generating_report":
            row = await self._wait_for_report(session_id)
            if row is not None:
                return report_mapper.to_result_from_row(session_id, row, session.persona)
            # 대기 상한을 넘겼거나 그사이 실패로 끝났다.
            # 어느 쪽인지는 상태를 다시 읽어야 알 수 있다.
            self.db.rollback()
            session = self._get_session(session_id)

        if session.status == "generating_report":
            raise _REPORT_PENDING
        if session.status == "report_failed":
            raise _REPORT_FAILED

        values = await self._checkpoint_values(session_id)
        if not values.get("report_result"):
            raise _NO_REPORT
        return report_mapper.to_result(session_id, values, session.persona)

    async def _wait_for_report(self, session_id: str) -> InterviewResult | None:
        """
        백그라운드 생성이 끝날 때까지 기다린다. 결과 행이 생기면 그걸 돌려준다.

        - 돌 때마다 rollback 하는 이유
        MySQL 기본 격리수준(REPEATABLE READ)에서는 한 트랜잭션 안에서 다시 조회해도
        다른 커넥션이 커밋한 행이 보이지 않는다.
        스냅샷을 버려야 백그라운드가 넣은 행이 읽힌다.

        - 중단된 생성을 다시 거는 이유
        BackgroundTasks 는 큐가 아니라 프로세스 메모리에 있는 함수 목록이다.
        생성 중에 컨테이너가 재시작되면 작업은 사라지고 세션 상태만 남는다.
        _report_in_flight 가 비어 있으면 그 경우이므로 여기서 다시 건다.
        """
        if session_id not in _report_in_flight:
            logger.warning("리포트 생성이 중단된 세션을 다시 시작합니다: %s", session_id)
            _report_in_flight.add(session_id)
            _spawn_report(session_id)

        deadline = time.monotonic() + REPORT_WAIT_TIMEOUT_SEC
        while time.monotonic() < deadline:
            await asyncio.sleep(REPORT_POLL_INTERVAL_SEC)

            self.db.rollback()
            row = self._get_result_row(session_id)
            if row is not None:
                return row

            session = self.db.get(InterviewSession, session_id)
            if session is None or session.status != "generating_report":
                return None      # 실패로 끝났거나 세션이 사라졌다

        logger.warning(
            "리포트 생성 대기가 %d초를 넘었습니다: %s", REPORT_WAIT_TIMEOUT_SEC, session_id
        )
        return None

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


# ── 리포트 생성 (백그라운드) ────────────────────────────


async def generate_report(session_id: str) -> None:
    """
    리포트를 만들어 저장한다. accept_end 가 True 를 돌려준 뒤 라우터가 거는 작업이다.

    - async 인 이유
    LLM 호출은 await 로 기다리는 I/O 라 이벤트 루프를 막지 않는다.
    영상 분석을 동기 함수로 둔 것과 이유가 반대다.
    그쪽은 cv2 가 CPU 를 붙들어 루프를 통째로 막기 때문에 스레드풀로 보낸다.

    - DB 세션을 새로 여는 이유
    요청에서 쓰던 세션은 응답이 나가는 시점에 닫힌다.
    이 함수는 그 뒤에 도므로 자기 세션이 필요하다.

    실패해도 예외를 밖으로 던지지 않는다.
    기다리는 요청이 없어서 던져도 받는 곳이 없고, 조용히 사라지면
    GET /result 가 영원히 생성 중으로 본다.
    그래서 세션을 report_failed 로 바꿔 기록을 남긴다.
    """
    values: dict = {}
    failed = False
    try:
        values = await graph_runner.finish(session_id)
    except Exception:
        logger.exception("리포트 생성 실패: %s", session_id)
        failed = True

    db = SessionLocal()
    try:
        session = db.get(InterviewSession, session_id)
        if session is None:      # 그새 지워졌다
            return

        if failed:
            session.status = "report_failed"
        elif values.get("report_result"):
            user = db.get(User, session.users_user_id)
            InterviewService(db, user)._save_result(session_id, values)
            session.status = "finished"
        else:
            # 예외는 없었는데 리포트가 비어 있다. report_generator 가 안 돌았다는 뜻이다.
            logger.error("리포트 생성 결과가 비어 있습니다: %s", session_id)
            session.status = "report_failed"

        db.commit()
    except Exception:
        logger.exception("리포트 저장 실패: %s", session_id)
        db.rollback()
    finally:
        db.close()
        # 잠금을 반드시 풀어야 한다.
        # 남겨두면 미아 복구가 동작하지 않아 다시 걸 수 없게 된다.
        _report_in_flight.discard(session_id)


def _spawn_report(session_id: str) -> None:
    """
    BackgroundTasks 없이 생성 작업을 띄운다. 중단된 생성을 되살릴 때만 쓴다.

    GET /result 는 BackgroundTasks 를 받지 않아 이쪽으로 건다.
    create_task 가 돌려준 task 를 들고 있지 않으면 GC 가 가져갈 수 있어 집합에 담아둔다.
    """
    task = asyncio.create_task(generate_report(session_id))
    _report_tasks.add(task)
    task.add_done_callback(_report_tasks.discard)
