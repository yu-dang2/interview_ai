from agent.parsers.persona_prompts import PERSONA_TECH_LEAD, PERSONA_HR, PERSONA_EXECUTIVE
from agent.graph.state import InterviewState

PERSONA_MAP = {
    "기술 리드": PERSONA_TECH_LEAD,
    "인사 담당자": PERSONA_HR,
    "임원 면접관": PERSONA_EXECUTIVE,
}


async def persona_selector(state: InterviewState):
    persona = state.get("persona", "기술 리드")
    if persona not in PERSONA_MAP:
        persona = "기술 리드"
    return {"persona": persona}
