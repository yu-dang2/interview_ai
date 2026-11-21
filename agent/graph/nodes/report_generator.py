import json
from langchain_core.messages import AIMessage, HumanMessage
from agent.parsers.report_generator_prompt import REPORT_GENERATOR_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.utils import call_llm

# 답변이 없는 세션의 고정 문구 (백엔드와 합의한 문구라 바꾸지 말 것)
NO_ANSWER_MESSAGE = "평가할 답변이 없어 리포트를 생성할 수 없습니다."

EARLY_TERMINATION_INSTRUCTION = """

[추가 지시 - 중도 종료 여부]
입력 JSON의 is_early_terminated 값을 그대로 사용하세요(직접 재판단하지 마세요).
is_early_terminated가 true이면 면접이 중도에 종료된 것이므로, 답변이 있는 문항만
기준으로 평가하고 summary.improvements의 첫 문장에
"면접이 중도에 종료되어 답변한 문항만으로 평가된 결과입니다."를 반드시 포함하세요.
"""

# 라포 질문 제외 지시. 코드로 걸러내면 대화와 질문의 순서가 어긋나 지시로 처리한다.
RAPPORT_EXCLUSION_INSTRUCTION = """

[추가 지시 - 라포 질문 제외]
question_list에서 type이 "라포"인 질문은 지원자의 긴장을 풀기 위한 라포 형성 질문이며
평가 대상이 아닙니다. 해당 질문과 그 답변은 다음에서 완전히 제외하세요.
- total_score 계산
- category_scores 계산 (5개 항목 모두)
- question_feedbacks (개별 항목으로 만들지 마세요)
나머지 질문만으로 점수를 산출하고, 라포 질문 답변이 부실하더라도 그것을 근거로
summary나 category_comments에서 감점하듯 서술하지 마세요.
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

    # 질문을 다 쓰면 index == len(question_list) 가 되므로, 남아 있으면 중도 종료다.
    is_early_terminated = state.get("current_question_index", 0) < len(question_list)

    payload = {
        "question_list": question_list,
        "conversation": qa_history,
        "eval_keywords": state.get("eval_keywords", []),
        "weakness_areas": state.get("weakness_areas", []),
        "is_early_terminated": is_early_terminated,
    }

    # 빈 배열을 넣으면 모델이 없는 점수를 지어내므로, 비어 있으면 키를 넣지 않는다.
    eval_results = state.get("eval_results", [])
    if eval_results:
        payload["eval_results"] = eval_results

    user_content = json.dumps(payload, ensure_ascii=False)

    report_result = await call_llm(
        REPORT_GENERATOR_SYSTEM_PROMPT
        + EARLY_TERMINATION_INSTRUCTION
        + RAPPORT_EXCLUSION_INSTRUCTION,
        user_content,
        stage="report_generator",
    )

    return {
        "messages": [AIMessage(content=json.dumps(report_result, ensure_ascii=False))],
        "report_result": report_result,
        "is_finished": True
    }
