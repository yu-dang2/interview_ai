"""
persona_selector 노드
작성: 이현주

지원님 UI에서 선택한 페르소나를 PERSONA_MAP으로 연결.
알 수 없는 페르소나면 기본값으로 설정.
LLM 불필요.
"""

from agent.parsers.persona_prompts import PERSONA_STRICT, PERSONA_FRIENDLY, PERSONA_PRACTICAL
from graph.state import InterviewState

PERSONA_MAP = {
    "깐깐한 기술 팀장": PERSONA_STRICT,
    "공감형 인사 담당자": PERSONA_FRIENDLY,
    "실무형 시니어 개발자": PERSONA_PRACTICAL,
}


def persona_selector(state: InterviewState):
    persona = state.get("persona", "깐깐한 기술 팀장")
    if persona not in PERSONA_MAP:
        persona = "깐깐한 기술 팀장"
    return {"persona": persona}
