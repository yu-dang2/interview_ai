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


def to_result(session_id: str, report: dict, match_result: dict) -> ResultResponse:
    category = report.get("category_scores", {}) or {}
    summary = report.get("summary", {}) or {}

    interview_score = clamp(report.get("total_score", 0))
    resume_score = estimate_resume_score(match_result)

    return ResultResponse(
        session_id=session_id,
        resume_score=resume_score,
        interview_score=interview_score,
        total_score=clamp(round(resume_score * RESUME_WEIGHT + interview_score * INTERVIEW_WEIGHT)),
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
