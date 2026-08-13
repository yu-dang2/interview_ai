"""
agent 출력 → backend 응답 스키마 어댑터

agent 쪽 프롬프트가 내보내는 키와 backend/schemas/interview.py 의 필드 이름이 여러 군데
어긋나 있다. 그 차이를 전부 이 파일 한 곳에 모아둔다. agent 쪽 프롬프트는 이미 작성·검증이
끝났으므로 리네임을 요청하지 않고, 백엔드가 흡수한다.

── agent 계약 (이 파일이 소비하는 키. 바뀌면 알려주세요) ──────────────

answer_evaluator (agent/parsers/answer_evaluator_prompt.py) — 전부 최상위 flat 키:
    eval_score, logic_score, communication_score, expertise_score,
    attitude_score, problem_solving_score, feedback,
    strengths[], weaknesses[], eval_keywords[], follow_up_needed, follow_up_focus
    ※ 모든 점수 0~100. 중첩된 "scores": {...} 객체는 존재하지 않는다.

report_generator (agent/parsers/report_generator_prompt.py):
    total_score, grade,
    category_scores{logic_score, communication_score, expertise_score,
                    attitude_score, problem_solving_score},
    summary{strengths, improvements, recommended_study},
    keywords[],
    question_feedbacks[{question, user_answer, score, improved_answer}]

jd_resume_matcher (agent/parsers/jd_resume_matcher_prompt.py):
    matching_skills[], missing_skills[], ... (점수 없음 → resume_score 는 여기서 근사한다)
"""

from backend.core.config import INTERVIEW_WEIGHT, RESUME_WEIGHT
from backend.schemas.interview import (
    FeedbackItem,
    FeedbackResponse,
    RadarChart,
    RealtimeFeedbackItem,
    RealtimeScore,
    ResultResponse,
    ResultSummary,
)

# RadarChart / RealtimeScore 필드명 → agent 가 쓰는 flat 키
_SCORE_KEYS = {
    "logic": "logic_score",
    "communication": "communication_score",
    "expertise": "expertise_score",
    "attitude": "attitude_score",
    "problem_solving": "problem_solving_score",
}


def clamp(value, lo: int = 0, hi: int = 100) -> int:
    """LLM이 105 같은 값을 뱉을 수 있으므로 0~100으로 자른다."""
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return lo


def _as_list(value) -> list[str]:
    """LLM이 리스트 대신 문자열 하나를 뱉는 경우를 방어."""
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _join(value) -> str:
    return "\n".join(_as_list(value))


# ── 실시간 (매 답변마다) ───────────────────────────────

def to_realtime_score(eval_result: dict) -> RealtimeScore:
    """
    eval_score 는 이미 0~100 이다 (topic_router 의 THRESHOLD=70 도 이 스케일 전제).
    예전 코드가 ×10 을 해서 최대 1000이 나가던 버그를 여기서 바로잡는다.
    """
    return RealtimeScore(
        total=clamp(eval_result.get("eval_score", 0)),
        **{field: clamp(eval_result.get(key, 0)) for field, key in _SCORE_KEYS.items()},
    )


def to_realtime_feedback(eval_result: dict) -> list[RealtimeFeedbackItem]:
    return [
        RealtimeFeedbackItem(type="positive", text=s)
        for s in _as_list(eval_result.get("strengths"))
    ] + [
        RealtimeFeedbackItem(type="suggestion", text=w)
        for w in _as_list(eval_result.get("weaknesses"))
    ]


# ── 최종 리포트 ────────────────────────────────────────

def estimate_resume_score(match_result: dict) -> int:
    """
    ResultResponse.resume_score 에 넣을 값.

    jd_resume_matcher 는 리스트만 리턴하고 점수를 주지 않아서, 보유 스킬 대비 매칭 비율로
    결정론적 근사치를 계산한다 (LLM 추가 호출 없음, 설명 가능).
    agent 쪽에서 match_score(0~100)를 내주면 그 값을 그대로 쓰도록 바꿀 것.
    """
    if not isinstance(match_result, dict):
        return 0

    explicit = match_result.get("match_score")
    if explicit is not None:
        return clamp(explicit)

    matching = len(_as_list(match_result.get("matching_skills")))
    missing = len(_as_list(match_result.get("missing_skills")))
    return clamp(round(100 * matching / max(1, matching + missing)))


def weighted_total(resume_score: int, interview_score: int) -> int:
    """최종 총점. 저장할 때와 응답할 때가 어긋나지 않도록 한 곳에서만 계산한다."""
    return clamp(round(resume_score * RESUME_WEIGHT + interview_score * INTERVIEW_WEIGHT))


# ── 저장용 (agent 출력 → InterviewResult 컬럼) ─────────

def resolve_resume_score(values: dict) -> int:
    """
    이력서 점수를 정한다.

    jd_resume_matcher 가 match_score(0~100)를 State 최상위에 넣어주므로 그 값을 쓴다.
    그 값이 없던 시절에 만든 근사(매칭/누락 스킬 개수 비율)는 폴백으로만 남긴다.
    """
    explicit = values.get("match_score")
    if explicit is not None:
        return clamp(explicit)
    return estimate_resume_score(values.get("match_result") or {})


def to_result_columns(values: dict) -> dict:
    """
    그래프 State 를 interview_results 컬럼 값으로 편다.

    match_score 가 State 최상위에 있어서 report 만이 아니라 State 전체를 받는다.
    이 매핑을 서비스가 아니라 여기 두는 이유: agent 키 ↔ 우리 필드 대응이 이 파일에
    모여 있어야 agent 쪽이 바뀔 때 한 곳만 고치면 된다.
    """
    report = values.get("report_result") or {}
    category = report.get("category_scores", {}) or {}
    summary = report.get("summary", {}) or {}

    resume_score = resolve_resume_score(values)
    interview_score = clamp(report.get("total_score", 0))

    columns = {
        "resume_score": resume_score,
        "interview_score": interview_score,
        "total_score": weighted_total(resume_score, interview_score),
        "grade": report.get("grade"),
        "summary_strength": _join(summary.get("strengths")),
        "summary_improvement": _join(summary.get("improvements")),
        "summary_recommendation": _join(summary.get("recommended_study")),
    }
    # 컬럼 이름과 agent 키가 같아서 그대로 쓴다 (logic_score, communication_score, ...)
    columns.update({key: clamp(category.get(key, 0)) for key in _SCORE_KEYS.values()})
    return columns


def to_question_feedback_rows(report: dict) -> list[dict]:
    """리포트의 question_feedbacks 배열 → InterviewQuestionFeedback 행 값들."""
    raw = report.get("question_feedbacks") or []
    return [
        {
            # 리포트에 번호가 없으므로 to_feedback 과 동일하게 리스트 순서로 매긴다.
            "question_number": i,
            "question": str(item.get("question", "")),
            "user_answer": str(item.get("user_answer", "")),   # agent 쪽 키는 user_answer
            "score": clamp(item.get("score", 0)),
            "improved_answer": str(item.get("improved_answer", "")),
        }
        for i, item in enumerate(raw, start=1)
        if isinstance(item, dict)
    ]


# ── 조회용 (InterviewResult 행 → 응답 스키마) ──────────

def to_result_from_row(session_id: str, row, persona: str | None = None) -> ResultResponse:
    """
    저장된 결과 행을 그대로 응답으로 바꾼다.

    체크포인트가 없어도 이 경로만으로 완전한 리포트가 나와야 한다.
    (예전에는 resume_score 를 체크포인트의 match_result 에서 계산해서, 체크포인트를
     지우면 0 으로 떨어졌다.)
    """
    return ResultResponse(
        session_id=session_id,
        persona=persona,
        resume_score=clamp(row.resume_score),
        interview_score=clamp(row.interview_score),
        total_score=clamp(row.total_score),
        grade=row.grade,
        radar_chart=RadarChart(
            **{field: clamp(getattr(row, key, 0)) for field, key in _SCORE_KEYS.items()}
        ),
        summary=ResultSummary(
            strength=row.summary_strength or "",
            improvement=row.summary_improvement or "",
            recommendation=row.summary_recommendation or "",
        ),
    )


def to_feedback_from_rows(rows) -> FeedbackResponse:
    """저장된 질문별 피드백 행들을 응답으로 바꾼다."""
    items = [
        FeedbackItem(
            question_number=row.question_number,
            question=row.question or "",
            my_answer=row.user_answer or "",
            score=clamp(row.score),
            improved_answer=row.improved_answer or "",
        )
        for row in rows
    ]
    average = round(sum(item.score for item in items) / len(items)) if items else 0
    return FeedbackResponse(
        total_questions=len(items),
        average_score=clamp(average),
        feedbacks=items,
    )


# ── 조회용 (체크포인트 State → 응답 스키마) ───────────
# 아직 결과가 저장되지 않은 진행 중 세션의 폴백 경로다.

def to_result(session_id: str, values: dict, persona: str | None = None) -> ResultResponse:
    report = values.get("report_result") or {}
    category = report.get("category_scores", {}) or {}
    summary = report.get("summary", {}) or {}

    interview_score = clamp(report.get("total_score", 0))
    resume_score = resolve_resume_score(values)

    return ResultResponse(
        session_id=session_id,
        persona=persona,
        resume_score=resume_score,
        interview_score=interview_score,
        total_score=weighted_total(resume_score, interview_score),
        grade=report.get("grade"),
        radar_chart=RadarChart(
            **{field: clamp(category.get(key, 0)) for field, key in _SCORE_KEYS.items()}
        ),
        summary=ResultSummary(
            strength=_join(summary.get("strengths")),
            improvement=_join(summary.get("improvements")),
            recommendation=_join(summary.get("recommended_study")),
        ),
    )


def to_feedback(report: dict) -> FeedbackResponse:
    raw = report.get("question_feedbacks") or []

    items = [
        FeedbackItem(
            # 리포트에 번호가 없으므로 리스트 순서에서 백엔드가 만든다.
            question_number=i,
            question=str(item.get("question", "")),
            my_answer=str(item.get("user_answer", "")),   # agent 쪽 키는 user_answer
            score=clamp(item.get("score", 0)),
            improved_answer=str(item.get("improved_answer", "")),
        )
        for i, item in enumerate(raw, start=1)
        if isinstance(item, dict)
    ]

    # turn_count 가 아니라 실제 피드백 개수. 꼬리질문이 붙으면 둘이 갈라진다.
    average = round(sum(item.score for item in items) / len(items)) if items else 0

    return FeedbackResponse(
        total_questions=len(items),
        average_score=clamp(average),
        feedbacks=items,
    )
