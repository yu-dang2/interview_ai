import json
from langchain_core.messages import AIMessage, HumanMessage
from agent.parsers.answer_evaluator_prompt import (
    ANSWER_EVALUATOR_SYSTEM_PROMPT,
    VOICE_INPUT_NOTICE,
)
from agent.graph.state import InterviewState
from agent.graph.nodes.persona_selector import PERSONA_MAP
from agent.parsers.persona_prompts import PERSONA_TECH_LEAD
from agent.graph.utils import call_llm, is_rapport_question

# 라포 질문 점수. topic_router.THRESHOLD 보다 높아야 꼬리질문이 붙지 않는다.
RAPPORT_NEUTRAL_SCORE = 80

# eval_results 에 담을 세부 점수 키(리포트 category_scores 와 같음). 여기 없는 필드는 리포트로 안 나간다.
CATEGORY_SCORE_FIELDS = (
    "logic_score",
    "communication_score",
    "expertise_score",
    "attitude_score",
    "problem_solving_score",
)


def _last_question(messages: list) -> str:
    """방금 답변한 질문(마지막 AIMessage). 꼬리질문은 question_list 에 없어 여기서 꺼낸다."""
    for msg in reversed(messages or []):
        if isinstance(msg, AIMessage):
            return msg.content
    return ""


def to_score_entry(eval_result: dict, order: int, question: str, is_follow_up: bool) -> dict:
    entry = {
        "order": order,
        "question": question,
        "is_follow_up": is_follow_up,
        "eval_score": eval_result.get("eval_score", 0),
    }
    for field in CATEGORY_SCORE_FIELDS:
        if eval_result.get(field) is not None:
            entry[field] = eval_result[field]
    return entry


async def answer_evaluator(state: InterviewState):
    question_list = state.get("question_list", [])
    current_index = state.get("current_question_index", 0)
    current_q = question_list[current_index] if question_list else {}

    if is_rapport_question(current_q):
        return {
            "eval_score": RAPPORT_NEUTRAL_SCORE,
            "eval_result": {},
            "eval_keywords": [],
            "weakness_areas": [],
            "eval_results": []
        }

    user_answer = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            user_answer = msg.content
            break

    persona_prompt = PERSONA_MAP.get(state.get("persona"), PERSONA_TECH_LEAD)
    system_prompt = persona_prompt + ANSWER_EVALUATOR_SYSTEM_PROMPT
    if state.get("input_type", "text") == "voice":
        system_prompt += VOICE_INPUT_NOTICE
    user_content = json.dumps({
        "question": current_q.get("question", ""),
        "good_answer_criteria": current_q.get("good_answer_criteria", ""),
        "answer": user_answer
    }, ensure_ascii=False)

    eval_result = await call_llm(system_prompt, user_content, stage="answer_evaluator")

    # follow_up_count 가 0 이 아니면 방금 답한 것이 꼬리질문이다.
    entry = to_score_entry(
        eval_result,
        order=len(state.get("eval_results", [])) + 1,
        question=_last_question(state.get("messages", [])),
        is_follow_up=state.get("follow_up_count", 0) > 0,
    )

    return {
        "eval_score": eval_result.get("eval_score", 0),
        "eval_result": eval_result,
        "eval_keywords": eval_result.get("eval_keywords", []),
        "weakness_areas": eval_result.get("weaknesses", []),
        "eval_results": [entry]
    }
