import asyncio

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from agent.graph.state import InterviewState, InterviewInput, InterviewOutput
from agent.graph.nodes.persona_selector import persona_selector
from agent.graph.nodes.jd_parser import jd_parser
from agent.graph.nodes.resume_parser import resume_parser
from agent.graph.nodes.jd_resume_matcher import jd_resume_matcher
from agent.graph.nodes.question_retriever import question_retriever
from agent.graph.nodes.question_generator import question_generator
from agent.graph.nodes.answer_evaluator import answer_evaluator
from agent.graph.nodes.follow_up_generator import follow_up_generator
from agent.graph.nodes.report_generator import report_generator
from agent.graph.nodes.resume_optimizer import resume_optimizer
from agent.graph.edges.topic_router import topic_router
from agent.graph.edges.question_router import question_router


def build_graph(checkpointer=None, interrupt_before=None):
    """
    interrupt_before: ["answer_evaluator"]를 주면 답변 평가 직전마다 멈추는 순환 그래프가 된다.
        None이면 첫 질문 생성 후 종료한다.
    """
    builder = StateGraph(
        InterviewState,
        input=InterviewInput,
        output=InterviewOutput
    )

    builder.add_node("persona_selector", persona_selector)
    builder.add_node("jd_parser", jd_parser)
    builder.add_node("resume_parser", resume_parser)
    builder.add_node("jd_resume_matcher", jd_resume_matcher)
    builder.add_node("question_retriever", question_retriever)
    builder.add_node("question_generator", question_generator)
    builder.add_node("answer_evaluator", answer_evaluator)
    builder.add_node("follow_up_generator", follow_up_generator)
    builder.add_node("report_generator", report_generator)
    builder.add_node("resume_optimizer", resume_optimizer)

    builder.add_edge(START, "persona_selector")

    # 두 파서는 병렬로 돌고 matcher 에서 합류한다. 두 노드가 같은 State 키에 쓰면 안 된다.
    builder.add_edge("persona_selector", "jd_parser")
    builder.add_edge("persona_selector", "resume_parser")
    builder.add_edge("jd_parser", "jd_resume_matcher")
    builder.add_edge("resume_parser", "jd_resume_matcher")

    builder.add_edge("jd_parser", "question_retriever")

    builder.add_edge("jd_resume_matcher", "question_generator")
    builder.add_edge("question_retriever", "question_generator")

    # interrupt 없이 answer_evaluator 로 가면 답변 전에 평가가 돌기 때문에 END 로 보낸다.
    next_after_q = "answer_evaluator" if interrupt_before else END
    builder.add_conditional_edges(
        "question_generator",
        question_router,
        {"report_generator": "report_generator", "continue": next_after_q},
    )

    # path map 을 빼면 get_graph() 그림에서 순환 경로가 빠진다(실행은 같음).
    builder.add_conditional_edges(
        "answer_evaluator",
        topic_router,
        ["report_generator", "follow_up_generator", "question_generator"],
    )
    builder.add_edge("follow_up_generator", "answer_evaluator")
    builder.add_edge("report_generator", "resume_optimizer")
    builder.add_edge("resume_optimizer", END)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before or []
    )


graph = build_graph()


# invoke 반환값은 output 스키마로 걸러지므로 State 는 aget_state()로 읽는다.
async def main():
    graph = build_graph(
        checkpointer=InMemorySaver(),
        interrupt_before=["answer_evaluator"],
    )
    config = {"configurable": {"thread_id": "cli-test"}}

    initial_input = {
        "jd_raw": "Python 백엔드 개발자 채용",
        "resume_raw": "Python 1년 경력, Django 프로젝트 경험",
        "persona": "기술 리드",
    }

    await graph.ainvoke(initial_input, config)

    while True:
        snapshot = await graph.aget_state(config)
        state = snapshot.values

        if state.get("is_finished", False) or not snapshot.next:
            break

        ai_messages = [m for m in state.get("messages", []) if isinstance(m, AIMessage)]
        if ai_messages:
            print(f"\nAI: {ai_messages[-1].content}")

        user_input = input("나: ")
        if user_input == "quit":
            break

        await graph.aupdate_state(config, {"messages": [HumanMessage(content=user_input)]})

        await graph.ainvoke(None, config)

    final_state = (await graph.aget_state(config)).values
    report = final_state.get("report_result")
    if report:
        print(f"\n=== 최종 리포트 ===\n{report}")

    print("\n=== 면접 종료 ===")


if __name__ == "__main__":
    asyncio.run(main())
