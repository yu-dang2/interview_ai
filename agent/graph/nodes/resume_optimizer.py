import json
import logging

from langchain_core.messages import HumanMessage
from agent.parsers.resume_optimizer_prompt import RESUME_OPTIMIZER_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.utils import call_llm

logger = logging.getLogger(__name__)

EMPTY_OPTIMIZATION = {"matched_keywords": [], "missing_keywords": [], "suggestions": []}


def _keywords(value) -> list:
    return value if isinstance(value, list) else []


def _normalize(raw) -> dict:
    if not isinstance(raw, dict):
        return dict(EMPTY_OPTIMIZATION)

    # 키 이름은 프롬프트 출력과 맞춰야 한다. 어긋나도 예외 없이 빈 배열만 나간다.
    matched = raw.get("matched_keywords", [])
    missing = raw.get("missing_keywords", [])
    optimizations = raw.get("optimizations", [])

    suggestions = []
    for i, item in enumerate(optimizations or [], start=1):
        if not isinstance(item, dict):
            continue
        suggestions.append({
            "id": f"opt-{i}",
            "section": item.get("section", ""),
            "original": item.get("original", ""),
            "improved": item.get("improved", ""),
            "reason": item.get("reason", ""),
        })

    return {
        "matched_keywords": _keywords(matched),
        "missing_keywords": _keywords(missing),
        "suggestions": suggestions,
    }


async def resume_optimizer(state: InterviewState):
    answer_count = sum(
        1 for m in state.get("messages", []) if isinstance(m, HumanMessage)
    )

    if answer_count == 0:
        return {"resume_optimization": dict(EMPTY_OPTIMIZATION)}

    report_result = state.get("report_result", {})
    interview_summary = {
        "summary": report_result.get("summary", {}) if isinstance(report_result, dict) else {},
        "eval_keywords": state.get("eval_keywords", []),
        "weakness_areas": state.get("weakness_areas", []),
    }
    user_content = json.dumps({
        "resume_parsed": state.get("resume_parsed", {}),
        "jd_parsed": state.get("jd_parsed", {}),
        "match_result": state.get("match_result", {}),
        "interview_summary": interview_summary,
    }, ensure_ascii=False)

    try:
        raw = await call_llm(
            RESUME_OPTIMIZER_SYSTEM_PROMPT, user_content, stage="resume_optimizer"
        )
        return {"resume_optimization": _normalize(raw)}
    except Exception as e:
        logger.error(
            "resume_optimizer 실패 — 빈 결과로 폴백: %s: %s",
            type(e).__name__, e,
        )
        return {"resume_optimization": dict(EMPTY_OPTIMIZATION)}
