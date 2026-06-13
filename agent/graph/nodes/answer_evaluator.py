"""
answer_evaluator 노드

예진님 ANSWER_EVALUATOR_SYSTEM_PROMPT + 페르소나 조합하여 답변 평가.
good_answer_criteria도 함께 전달하여 정확한 평가 유도.
eval_result의 score가 topic_router 분기 판단의 핵심 값.
"""

import json
from langchain_core.messages import HumanMessage
from agent.parsers.answer_evaluator_prompt import ANSWER_EVALUATOR_SYSTEM_PROMPT
from graph.state import InterviewState
from graph.nodes.persona_selector import PERSONA_MAP
from agent.parsers.persona_prompts import PERSONA_STRICT
from graph.utils import call_llm


def answer_evaluator(state: InterviewState):
    question_list = state.get("question_list", [])
    current_index = state.get("current_question_index", 0)
    current_q = question_list[current_index] if question_list else {}

    # 마지막 사용자 답변 가져오기
    user_answer = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            user_answer = msg.content
            break

    persona_prompt = PERSONA_MAP.get(state.get("persona"), PERSONA_STRICT)
    system_prompt = persona_prompt + ANSWER_EVALUATOR_SYSTEM_PROMPT
    user_content = json.dumps({
        "question": current_q.get("question", ""),
        "good_answer_criteria": current_q.get("good_answer_criteria", ""),
        "answer": user_answer
    }, ensure_ascii=False)

    eval_result = call_llm(system_prompt, user_content)
    return {
        "eval_score": eval_result.get("score", 0),
        "eval_result": eval_result,
        "eval_keywords": eval_result.get("strengths", []),
        "weakness_areas": eval_result.get("weaknesses", [])
    }
