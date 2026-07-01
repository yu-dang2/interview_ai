"""
follow_up_generator 노드
작성: 이현주

예진님 FOLLOW_UP_GENERATOR_SYSTEM_PROMPT + 페르소나 조합하여 꼬리질문 생성.
eval_result의 follow_up_focus를 받아서 허점 파고들기.
최대 3회 제한은 topic_router에서 관리.
"""

import json
from langchain_core.messages import HumanMessage, AIMessage
from agent.parsers.follow_up_prompt import FOLLOW_UP_GENERATOR_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.nodes.persona_selector import PERSONA_MAP
from agent.parsers.persona_prompts import PERSONA_TECH_LEAD
from agent.graph.utils import call_llm


def follow_up_generator(state: InterviewState):
    count = state.get("follow_up_count", 0)
    eval_result = state.get("eval_result", {})

    persona_prompt = PERSONA_MAP.get(state.get("persona"), PERSONA_TECH_LEAD)
    system_prompt = persona_prompt + FOLLOW_UP_GENERATOR_SYSTEM_PROMPT

    # 최근 대화 맥락 + follow_up_focus 전달
    recent_context = []
    for msg in state.get("messages", [])[-4:]:
        if isinstance(msg, HumanMessage):
            recent_context.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            recent_context.append({"role": "assistant", "content": msg.content})

    user_content = json.dumps({
        "recent_conversation": recent_context,
        "follow_up_focus": eval_result.get("follow_up_focus", "")
    }, ensure_ascii=False)

    result = call_llm(system_prompt, user_content)
    return {
        "messages": [AIMessage(content=result.get("follow_up_question", ""))],
        "follow_up_count": count + 1
    }
