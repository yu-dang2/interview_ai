"""
persona_selector 노드
작성: 이현주

지원님 UI에서 선택한 페르소나를 PERSONA_MAP으로 연결.
알 수 없는 페르소나면 기본값으로 설정.
LLM 불필요.
"""

from agent.parsers.persona_prompts import PERSONA_TECH_LEAD, PERSONA_HR, PERSONA_EXECUTIVE
from agent.graph.state import InterviewState

PERSONA_MAP = {
    "기술 리드": PERSONA_TECH_LEAD,
    "인사 담당자": PERSONA_HR,
    "임원 면접관": PERSONA_EXECUTIVE,
}


def persona_selector(state: InterviewState):
    persona = state.get("persona", "기술 리드")
    if persona not in PERSONA_MAP:
        persona = "기술 리드"
    return {"persona": persona}
