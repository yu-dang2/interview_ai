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

# 라포 형성 질문 제외 지시 (프롬프트 파일은 수정 불가 → 노드에서 이어붙임).
#
# question_list에서 라포 질문을 코드로 걸러내는 방식은 쓰지 않는다. conversation은
# messages 순서 그대로 나가는데 질문 하나만 빠지면 LLM의 질문-답변 정렬이 통째로 밀린다.
# 그래서 둘 다 그대로 넘기고 "집계에서 빼라"고 지시만 한다.
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
    # 준비된 질문을 다 소진했으면 정상 종료, 남아 있으면 중도 종료로 판정한다.
    # (코드에서 결정해 LLM 에 명시 전달 — LLM 이 재판단하지 않도록)
    #
    # 예전에는 turn_count < MAX_TURNS 로 판정했는데, turn_count 는 주 질문에서만 +1 되고
    # 꼬리질문은 세지 않는다. 본질문 수가 topic_router.MAX_TURNS 보다 적어 그 조건이 항상
    # 참이었고, 정상 완주한 면접도 전부 "중도 종료"로 표기됐다.
    # (질문 수는 프롬프트가 정하므로 여기에 숫자로 못박지 않는다)
    #
    # question_generator 는 질문을 소진하면 current_question_index 를 len(question_list) 로
    # 올리고 is_finished 를 세운다. 그래서 정상 종료 경로에서는 index == len 이 되고,
    # 종료 버튼(graph_runner.finish)으로 들어오면 question_generator 를 거치지 않아
    # index < len 이 유지된다.
    is_early_terminated = state.get("current_question_index", 0) < len(question_list)

    # eval_results 는 답변마다 실시간으로 매긴 점수다(라포 제외, 꼬리질문 포함).
    # 프롬프트 규칙 2·4 가 "입력으로 주어진 각 답변의 평가 결과를 종합·평균하라"고
    # 지시하는데 예전에는 그 입력을 넣지 않아, LLM 이 답변 원문만 보고 재채점했다.
    # 그래서 리포트 총점·코멘트가 실시간 평가와 다른 기준으로 나왔다.
    #
    # question_list 와 짝지어 넘기지 않는다. 꼬리질문은 question_list 에 없어서
    # 순서로 맞추면 어긋난다. 원소마다 order·question 을 달아 그대로 넘긴다.
    payload = {
        "question_list": question_list,
        "conversation": qa_history,
        "eval_keywords": state.get("eval_keywords", []),
        "weakness_areas": state.get("weakness_areas", []),
        "is_early_terminated": is_early_terminated,
    }

    # 비어 있으면 키 자체를 넣지 않는다. 빈 배열을 주면서 "이 점수들을 평균하라"고 하면
    # 모델이 없는 값을 짜맞추려 든다(question_generator 의 reference_knowledge 와 같은 이유).
    # 이 변경 전에 시작된 세션은 체크포인트에 eval_results 가 없어 여기로 떨어지고,
    # 수정 전과 동일하게 동작한다.
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
