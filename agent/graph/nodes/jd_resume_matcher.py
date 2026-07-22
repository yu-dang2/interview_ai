"""
jd_resume_matcher 노드
작성: 이현주

예진님 JD_RESUME_MATCHER_SYSTEM_PROMPT 사용하여
JD와 이력서 비교 → 강점/약점/면접 주제 산출.
"""

import json
from agent.parsers.jd_resume_matcher_prompt import JD_RESUME_MATCHER_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.utils import call_llm

# 프롬프트 파일은 수정 불가 → 노드에서 match_score 산출 지시를 이어붙임.
MATCH_SCORE_INSTRUCTION = """

[추가 지시 - 적합도 점수]
위 JSON 최상위에 match_score(JD-이력서 적합도, 0~100 정수) 키를 추가로 포함하세요.
- 필수 기술(required_skills) 충족도를 가장 크게 반영하세요.
- 우대 기술, 경력 연차, 프로젝트 관련성은 보조 지표로 반영하세요.
- 반드시 0~100 사이의 정수 하나로 출력하세요.
"""

# match_score 파싱 실패/범위 밖일 때의 안전한 기본값 (미산출을 낮게 표기해 눈에 띄게)
DEFAULT_MATCH_SCORE = 0


def _clamp_match_score(value) -> int:
    """LLM이 준 match_score를 0~100 정수로 방어적으로 변환 (실패 시 기본값)."""
    try:
        score = int(value)
    except (TypeError, ValueError):
        return DEFAULT_MATCH_SCORE
    return max(0, min(100, score))


async def jd_resume_matcher(state: InterviewState):
    user_content = json.dumps({
        "jd": state["jd_parsed"],
        "resume": state["resume_parsed"]
    }, ensure_ascii=False)
    match_result = await call_llm(
        JD_RESUME_MATCHER_SYSTEM_PROMPT + MATCH_SCORE_INSTRUCTION,
        user_content,
    )
    raw = match_result.get("match_score") if isinstance(match_result, dict) else None
    match_score = _clamp_match_score(raw)
    # 기존 match_result 반환은 그대로 유지, match_score만 추가
    return {"match_result": match_result, "match_score": match_score}
