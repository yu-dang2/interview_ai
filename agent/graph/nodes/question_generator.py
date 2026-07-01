"""
question_generator 노드
작성: 이현주

예진님 QUESTION_GENERATOR_SYSTEM_PROMPT + 페르소나 조합하여 질문 목록 생성.
- 첫 실행: 질문 목록 생성 후 첫 번째 질문 반환
- 이후 실행: 다음 질문으로 인덱스 이동
- 질문 소진 시 is_finished = True로 설정하여 종료 트리거
"""

import json
from langchain_core.messages import AIMessage
from agent.parsers.question_generator_prompt import QUESTION_GENERATOR_SYSTEM_PROMPT
from graph.state import InterviewState
from graph.nodes.persona_selector import PERSONA_MAP
from agent.parsers.persona_prompts import PERSONA_TECH_LEAD
from graph.utils import call_llm


def question_generator(state: InterviewState):
    current_index = state.get("current_question_index", 0)
    question_list = state.get("question_list", [])

    # 첫 실행: 예진님 프롬프트로 질문 목록 생성
    if not question_list:
        persona_prompt = PERSONA_MAP.get(state.get("persona"), PERSONA_TECH_LEAD)
        system_prompt = persona_prompt + QUESTION_GENERATOR_SYSTEM_PROMPT
        user_content = json.dumps({
            "match_result": state["match_result"],
            "resume": state["resume_parsed"]
        }, ensure_ascii=False)
        result = call_llm(system_prompt, user_content)
        question_list = result.get("questions", [])
        current_index = 0
    else:
        # 이후 실행: 다음 질문으로 이동
        current_index += 1

    # 질문 소진 시 종료
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
        "follow_up_count": 0    # 새 주제 시작 시 꼬리질문 횟수 초기화
    }
