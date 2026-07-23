"""
AI 면접관 에이전트 - 그래프 조립 및 실행

사용자 답변 수신은 노드가 아닌 while 루프에서 처리.
유정님 FastAPI 연동 시 실행 루프 부분 변경 예정.
"""

import asyncio

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from agent.graph.state import InterviewState, InterviewInput, InterviewOutput
from agent.graph.nodes.persona_selector import persona_selector
from agent.graph.nodes.jd_parser import jd_parser
from agent.graph.nodes.resume_parser import resume_parser
from agent.graph.nodes.jd_resume_matcher import jd_resume_matcher
from agent.graph.nodes.question_generator import question_generator
from agent.graph.nodes.answer_evaluator import answer_evaluator
from agent.graph.nodes.follow_up_generator import follow_up_generator
from agent.graph.nodes.report_generator import report_generator
from agent.graph.edges.topic_router import topic_router
from agent.graph.edges.question_router import question_router


# ── 그래프 조립 ────────────────────────────────────────
def build_graph(checkpointer=None, interrupt_before=None):
    """
    그래프를 조립해서 컴파일된 객체를 반환.

    checkpointer=None이면 기존과 동일하게 동작한다.
    유정님 FastAPI 연동 시 checkpointer를 주입해서 대화 상태를 보존할 수 있다.

    interrupt_before:
        휴먼-인-더-루프(HITL) 모드 opt-in. ["answer_evaluator"]를 주면
        질문 생성 노드(question_generator/follow_up_generator)에서 answer_evaluator
        직전까지 실행한 뒤 일시정지한다. 이때만 question_generator → answer_evaluator
        엣지를 추가해 하나의 연속 그래프로 순환하게 만든다.
        None(기본값)이면 기존 토폴로지(첫 질문 생성 후 종료)를 그대로 유지하므로
        백엔드 등 기존 사용처에는 영향이 없다.
    """
    builder = StateGraph(
        InterviewState,
        input=InterviewInput,
        output=InterviewOutput
    )

    # 노드 등록
    builder.add_node("persona_selector", persona_selector)
    builder.add_node("jd_parser", jd_parser)
    builder.add_node("resume_parser", resume_parser)
    builder.add_node("jd_resume_matcher", jd_resume_matcher)
    builder.add_node("question_generator", question_generator)
    builder.add_node("answer_evaluator", answer_evaluator)
    builder.add_node("follow_up_generator", follow_up_generator)
    builder.add_node("report_generator", report_generator)

    # 엣지 연결
    # 초기 흐름: 페르소나 확인 → JD/이력서 파싱 → 매칭 → 첫 질문 생성
    builder.add_edge(START, "persona_selector")
    builder.add_edge("persona_selector", "jd_parser")
    builder.add_edge("jd_parser", "resume_parser")
    builder.add_edge("resume_parser", "jd_resume_matcher")
    builder.add_edge("jd_resume_matcher", "question_generator")

    # question_generator 나가는 엣지(조건부, question_router 판단):
    #   - is_finished == True → report_generator (백엔드 종료 주입 / 질문 소진)
    #   - 그 외("continue")  → 기존 흐름. interrupt 모드면 answer_evaluator(직전 정지),
    #                          아니면 END. (interrupt 없이 answer_evaluator로 가면 답변을
    #                          받기 전에 평가가 돌아가므로 비-interrupt에서는 END로 종결)
    next_after_q = "answer_evaluator" if interrupt_before else END
    builder.add_conditional_edges(
        "question_generator",
        question_router,
        {"report_generator": "report_generator", "continue": next_after_q},
    )

    # 순환 흐름: 답변 평가 → topic_router 분기 → 꼬리질문 or 다음질문 or 리포트
    # path map을 명시하는 이유: 생략하면 LangGraph가 분기 대상을 알 수 없어
    # get_graph()/mermaid 출력에 answer_evaluator → END 한 줄만 그려지고
    # 실제 순환 경로가 통째로 빠진다. (런타임 동작은 동일)
    builder.add_conditional_edges(
        "answer_evaluator",
        topic_router,
        ["report_generator", "follow_up_generator", "question_generator"],
    )
    builder.add_edge("follow_up_generator", "answer_evaluator")
    builder.add_edge("report_generator", END)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before or []
    )


# 기존 사용처(CLI 테스트 등) 호환을 위해 모듈 레벨 그래프 유지
graph = build_graph()


# ── 실행 루프 ──────────────────────────────────────────
# 유정님 FastAPI 연동 시 이 부분 변경 예정
#
# checkpointer(InMemorySaver) + thread_id 방식:
#   - 하나의 그래프를 매 턴 재사용하고, 전체 State는 checkpointer가 보존한다.
#   - answer_evaluator 직전에서 일시정지 → 사용자 답변을 messages에 주입 → 재개.
#   - invoke 반환값은 output 스키마로 필터링되므로 재사용하지 않고,
#     항상 aget_state()로 checkpointer의 온전한 State를 읽는다. (match_result 등 보존)
async def main():
    graph = build_graph(
        checkpointer=InMemorySaver(),
        interrupt_before=["answer_evaluator"],
    )
    config = {"configurable": {"thread_id": "cli-test"}}

    # 지원님 UI에서 전달받을 값 (현재는 임의값으로 테스트) — InterviewInput 스키마
    initial_input = {
        "jd_raw": "Python 백엔드 개발자 채용",
        "resume_raw": "Python 1년 경력, Django 프로젝트 경험",
        "persona": "기술 리드",
    }

    # 초기 실행: 페르소나 확인 → JD/이력서 파싱 → 매칭 → 첫 질문 생성 후
    # answer_evaluator 직전에서 정지
    await graph.ainvoke(initial_input, config)

    # 면접 루프
    while True:
        snapshot = await graph.aget_state(config)
        state = snapshot.values

        # 질문 소진(is_finished) 또는 그래프 종료(END 도달, next 없음)면 종료
        if state.get("is_finished", False) or not snapshot.next:
            break

        # 마지막 AI 메시지 = 방금 생성된 질문(또는 꼬리질문)
        ai_messages = [m for m in state.get("messages", []) if isinstance(m, AIMessage)]
        if ai_messages:
            print(f"\nAI: {ai_messages[-1].content}")

        user_input = input("나: ")
        if user_input == "quit":
            break

        # 답변을 messages에 append (input 스키마를 우회하고 add_messages 리듀서 사용).
        # answer_evaluator가 마지막 HumanMessage를 읽어 평가한다.
        await graph.aupdate_state(config, {"messages": [HumanMessage(content=user_input)]})

        # 재개: answer_evaluator → topic_router 분기 → 다음 정지 또는 END
        await graph.ainvoke(None, config)

    # 종료 후 최종 리포트 출력 (report_generator가 생성했을 경우)
    final_state = (await graph.aget_state(config)).values
    report = final_state.get("report_result")
    if report:
        print(f"\n=== 최종 리포트 ===\n{report}")

    print("\n=== 면접 종료 ===")


if __name__ == "__main__":
    asyncio.run(main())
