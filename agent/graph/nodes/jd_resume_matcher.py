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


async def jd_resume_matcher(state: InterviewState):
    user_content = json.dumps({
        "jd": state["jd_parsed"],
        "resume": state["resume_parsed"]
    }, ensure_ascii=False)
    match_result = await call_llm(JD_RESUME_MATCHER_SYSTEM_PROMPT, user_content)
    return {"match_result": match_result}
