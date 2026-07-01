"""
resume_parser 노드
작성: 이현주

예진님 RESUME_PARSER_SYSTEM_PROMPT 사용하여 이력서 텍스트 → JSON 구조화.
"""

from agent.parsers.resume_parser_prompt import RESUME_PARSER_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.utils import call_llm


def resume_parser(state: InterviewState):
    resume_parsed = call_llm(RESUME_PARSER_SYSTEM_PROMPT, state["resume_raw"])
    return {"resume_parsed": resume_parsed}
