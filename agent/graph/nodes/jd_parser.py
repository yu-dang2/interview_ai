"""
jd_parser 노드
작성: 이현주

예진님 parse_jd_from_text() 호출하여 JD 텍스트 → JSON 구조화.
"""

from agent.parsers.jd_parser import parse_jd_from_text
from agent.graph.state import InterviewState


async def jd_parser(state: InterviewState):
    result = await parse_jd_from_text(state["jd_raw"])
    jd_parsed = result.data if hasattr(result, "data") else result
    return {"jd_parsed": jd_parsed}
