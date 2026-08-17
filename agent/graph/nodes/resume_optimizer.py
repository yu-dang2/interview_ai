"""
resume_optimizer 노드
작성: 이현주

면접 종료 시 이력서 자동 최적화 제안을 생성한다.
예진님 RESUME_OPTIMIZER_SYSTEM_PROMPT 사용 (JD·이력서·면접 근거 기반 문구 개선).

- report_generator 다음에 실행되므로 report_result가 State에 이미 존재 → 면접 근거로 재사용
  (전체 대화록 재전송 대신 리포트 요약 + 누적 키워드/약점을 넘겨 토큰 절약 + 환각 억제).
- 프롬프트 출력 키를 화면·DB 기준으로 정규화하고(matched_jd_keywords→matched_keywords,
  optimizations→suggestions) 각 제안에 id를 부여한다. 프롬프트 파일은 수정 금지 영역이라 노드에서 변환.
- 실패 격리: 리포트는 성공했는데 최적화만 실패해도 면접 전체가 실패하면 안 되므로,
  LLM/파싱 실패 시 빈 결과를 반환하고 그래프는 정상 종료한다.
- 답변 0개(중도 이탈) 세션: 면접 근거가 없어 환각 위험이 커 LLM 미호출로 빈 결과 반환.
  (report_generator의 "평가할 답변 없음" 처리와 일관)
"""

import json
import logging

from langchain_core.messages import HumanMessage
from agent.parsers.resume_optimizer_prompt import RESUME_OPTIMIZER_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.utils import call_llm

logger = logging.getLogger(__name__)

# 실패/스킵 시 반환할 빈 결과 (화면·DB 기준 구조 유지)
EMPTY_OPTIMIZATION = {"matched_keywords": [], "suggestions": []}


def _normalize(raw) -> dict:
    """
    프롬프트 출력을 화면·DB 기준으로 변환한다.
      matched_jd_keywords → matched_keywords
      optimizations       → suggestions (각 원소에 id 부여)
    section/original/improved는 그대로, reason은 유지(화면 미사용, 향후 활용).
    """
    if not isinstance(raw, dict):
        return dict(EMPTY_OPTIMIZATION)

    matched = raw.get("matched_jd_keywords", [])
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
        "matched_keywords": matched if isinstance(matched, list) else [],
        "suggestions": suggestions,
    }


async def resume_optimizer(state: InterviewState):
    # 답변 수 = 사용자 HumanMessage 수 (report_generator와 동일 기준)
    answer_count = sum(
        1 for m in state.get("messages", []) if isinstance(m, HumanMessage)
    )

    # 답변 0개(중도 이탈): 면접 근거가 없어 환각 위험 → LLM 미호출로 빈 결과
    if answer_count == 0:
        return {"resume_optimization": dict(EMPTY_OPTIMIZATION)}

    # 면접 근거: report_generator가 이미 만든 요약 + 누적 키워드/약점을 재사용
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

    # 실패 격리: 최적화 실패가 면접 전체를 실패시키지 않도록 빈 결과로 폴백
    try:
        raw = await call_llm(RESUME_OPTIMIZER_SYSTEM_PROMPT, user_content)
        return {"resume_optimization": _normalize(raw)}
    except Exception as e:
        logger.error(
            "resume_optimizer 실패 — 빈 결과로 폴백: %s: %s",
            type(e).__name__, e,
        )
        return {"resume_optimization": dict(EMPTY_OPTIMIZATION)}
