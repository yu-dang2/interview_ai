"""
report_generator 노드
작성: 이현주

예진님 REPORT_GENERATOR_SYSTEM_PROMPT 사용하여 전체 면접 기록을 종합 리포트로 생성.
"""

import json
from langchain_core.messages import AIMessage, HumanMessage
from agent.parsers.report_generator_prompt import REPORT_GENERATOR_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.utils import call_llm


async def report_generator(state: InterviewState):
    question_list = state.get("question_list", [])

    qa_history = []
    for msg in state.get("messages", []):
        if isinstance(msg, HumanMessage):
            qa_history.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            qa_history.append({"role": "assistant", "content": msg.content})

    user_content = json.dumps({
        "question_list": question_list,
        "conversation": qa_history,
        "eval_keywords": state.get("eval_keywords", []),
        "weakness_areas": state.get("weakness_areas", [])
    }, ensure_ascii=False)

    report_result = await call_llm(REPORT_GENERATOR_SYSTEM_PROMPT, user_content)

    return {
        "messages": [AIMessage(content=json.dumps(report_result, ensure_ascii=False))],
        "report_result": report_result,
        "is_finished": True
    }
