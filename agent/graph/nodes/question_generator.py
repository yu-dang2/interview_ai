import json
from langchain_core.messages import AIMessage
from agent.parsers.question_generator_prompt import QUESTION_GENERATOR_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.nodes.persona_selector import PERSONA_MAP
from agent.parsers.persona_prompts import PERSONA_TECH_LEAD
from agent.graph.utils import call_llm

RETRIEVAL_INSTRUCTION = """

[추가 지시 - 직무 지식 참고]
아래 reference_knowledge는 이 직무에서 일반적으로 평가하는 관점입니다.
채용공고(JD)와 지원자 이력서가 우선이며, 이 지식은 질문을 더 전문적으로 만들기 위한
보조 참고자료입니다.
- 이 관점을 그대로 질문으로 만들지 마세요. 반드시 지원자 이력서의 구체적 경험과 결합해
  재작성하세요.
- 관련성이 낮은 항목은 무시하세요.
- 참고자료에 있다는 이유만으로 이력서에 근거가 없는 주제를 질문하지 마세요.
"""

# 프롬프트에 실을 카드 필드. 여기 없는 필드는 프롬프트로 나가지 않는다.
_PROMPT_FIELDS = (
    "job_family",
    "trend_2026",
    "real_questions",
    "deep_dive_patterns",
    "common_pitfalls",
    # 구 스키마 호환
    "core_competencies",
    "evaluation_points",
    "industry_trends",
    "interview_perspective",
)


def _to_reference(cards: list) -> list:
    reference = []
    for card in cards or []:
        if not isinstance(card, dict):
            continue
        picked = {f: card[f] for f in _PROMPT_FIELDS if card.get(f)}
        if picked:
            reference.append(picked)
    return reference


async def question_generator(state: InterviewState):
    current_index = state.get("current_question_index", 0)
    question_list = state.get("question_list", [])

    if not question_list:
        persona_prompt = PERSONA_MAP.get(state.get("persona"), PERSONA_TECH_LEAD)
        system_prompt = persona_prompt + QUESTION_GENERATOR_SYSTEM_PROMPT

        payload = {
            "match_result": state["match_result"],
            "resume": state["resume_parsed"]
        }

        # 빈 참고자료를 주면 모델이 없는 자료를 찾으려 들어, 있을 때만 붙인다.
        reference = _to_reference(state.get("retrieved_knowledge", []))
        if reference:
            system_prompt += RETRIEVAL_INSTRUCTION
            payload["reference_knowledge"] = reference

        user_content = json.dumps(payload, ensure_ascii=False)
        result = await call_llm(system_prompt, user_content, stage="question_generator")
        question_list = result.get("questions", [])
        current_index = 0
    else:
        current_index += 1

    if current_index >= len(question_list):
        return {
            "question_list": question_list,
            "current_question_index": current_index,
            "is_finished": True
        }

    current_q = question_list[current_index]
    return {
        "messages": [AIMessage(content=current_q["question"])],
        "question_list": question_list,
        "current_question_index": current_index,
        "turn_count": state.get("turn_count", 0) + 1,
        "follow_up_count": 0
    }
