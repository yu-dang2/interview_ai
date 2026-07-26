"""
report_generator 노드
작성: 이현주

예진님 REPORT_GENERATOR_SYSTEM_PROMPT 사용하여 전체 면접 기록을 종합 리포트로 생성.
"""

import json
from langchain_core.messages import AIMessage, HumanMessage
from agent.parsers.report_generator_prompt import REPORT_GENERATOR_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.edges.topic_router import MAX_TURNS
from agent.graph.utils import call_llm

# 답변이 하나도 없는 세션의 고정 리포트 문구 (백엔드 합의 확정 문구 — 정확히 이대로 사용)
NO_ANSWER_MESSAGE = "평가할 답변이 없어 리포트를 생성할 수 없습니다."

# 중도 종료 세션 보충 지시 (프롬프트 파일은 수정 불가 → 노드에서 이어붙임).
# 코드가 판정한 is_early_terminated 값을 LLM이 그대로 쓰도록 강제한다.
EARLY_TERMINATION_INSTRUCTION = """

[추가 지시 - 중도 종료 여부]
입력 JSON의 is_early_terminated 값을 그대로 사용하세요(직접 재판단하지 마세요).
is_early_terminated가 true이면 면접이 중도에 종료된 것이므로, 답변이 있는 문항만
기준으로 평가하고 summary.improvements의 첫 문장에
"면접이 중도에 종료되어 답변한 문항만으로 평가된 결과입니다."를 반드시 포함하세요.
"""


async def report_generator(state: InterviewState):
    question_list = state.get("question_list", [])

    qa_history = []
    answer_count = 0
    for msg in state.get("messages", []):
        if isinstance(msg, HumanMessage):
            qa_history.append({"role": "user", "content": msg.content})
            answer_count += 1
        elif isinstance(msg, AIMessage):
            qa_history.append({"role": "assistant", "content": msg.content})

    # 답변 0개: LLM 호출 없이 고정 리포트 반환 (백엔드 합의)
    if answer_count == 0:
        report_result = {
            "total_score": 0,
            "is_early_terminated": True,
            "summary": {
                "strengths": NO_ANSWER_MESSAGE,
                "improvements": NO_ANSWER_MESSAGE,
                "recommended_study": NO_ANSWER_MESSAGE,
            },
            "question_feedbacks": [],
        }
        return {
            "messages": [AIMessage(content=NO_ANSWER_MESSAGE)],
            "report_result": report_result,
            "is_finished": True,
        }

    # 답변 1개 이상: 진행된 답변만 기준으로 평가.
    # 정상 종료(10턴 완료)가 아니면 중도 종료로 판정 — turn_count로 코드에서 결정해 명시 전달.
    is_early_terminated = state.get("turn_count", 0) < MAX_TURNS
    user_content = json.dumps({
        "question_list": question_list,
        "conversation": qa_history,
        "eval_keywords": state.get("eval_keywords", []),
        "weakness_areas": state.get("weakness_areas", []),
        "is_early_terminated": is_early_terminated,
    }, ensure_ascii=False)

    report_result = await call_llm(
        REPORT_GENERATOR_SYSTEM_PROMPT + EARLY_TERMINATION_INSTRUCTION,
        user_content,
    )

    return {
        "messages": [AIMessage(content=json.dumps(report_result, ensure_ascii=False))],
        "report_result": report_result,
        "is_finished": True
    }
