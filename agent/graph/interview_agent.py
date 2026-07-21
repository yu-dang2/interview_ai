"""
AI 면접관 에이전트 - 그래프 조립 및 실행

사용자 답변 수신은 노드가 아닌 while 루프에서 처리.
유정님 FastAPI 연동 시 실행 루프 부분 변경 예정.
"""

import asyncio

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

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


# ── 그래프 조립 ────────────────────────────────────────
def build_graph(checkpointer=None):
    """
    그래프를 조립해서 컴파일된 객체를 반환.

    checkpointer=None이면 기존과 동일하게 동작한다.
    유정님 FastAPI 연동 시 checkpointer를 주입해서 대화 상태를 보존할 수 있다.
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

    # 순환 흐름: 답변 평가 → topic_router 분기 → 꼬리질문 or 다음질문 or 리포트
    builder.add_conditional_edges("answer_evaluator", topic_router)
    builder.add_edge("follow_up_generator", "answer_evaluator")
    builder.add_edge("report_generator", END)

    return builder.compile(checkpointer=checkpointer)


# 기존 사용처(CLI 테스트 등) 호환을 위해 모듈 레벨 그래프 유지
graph = build_graph()


# ── 실행 루프 ──────────────────────────────────────────
# 유정님 FastAPI 연동 시 이 부분 변경 예정
async def main():

    # 지원님 UI에서 전달받을 값 (현재는 임의값으로 테스트)
    state = {
        "messages": [],
        "jd_raw": "Python 백엔드 개발자 채용",
        "resume_raw": "Python 1년 경력, Django 프로젝트 경험",
        "jd_parsed": {},
        "resume_parsed": {},
        "match_result": {},
        "question_list": [],
        "current_question_index": 0,
        "persona": "기술 리드",
        "eval_score": 0,
        "eval_result": {},
        "eval_keywords": [],
        "weakness_areas": [],
        "follow_up_count": 0,
        "turn_count": 0,
        "is_finished": False
    }

    # 초기 실행 (페르소나 확인 → JD/이력서 파싱 → 매칭 → 첫 질문 생성)
    current_state = await graph.ainvoke(state)

    # 면접 루프
    while not current_state.get("is_finished", False):
        print(f"\nAI: {current_state['messages'][-1].content}")

        user_input = input("나: ")
        if user_input == "quit":
            break

        current_state["messages"] = current_state["messages"] + [HumanMessage(content=user_input)]

        # 답변 받은 후 answer_evaluator부터 재실행
        sub_graph = StateGraph(InterviewState)
        sub_graph.add_node("answer_evaluator", answer_evaluator)
        sub_graph.add_node("follow_up_generator", follow_up_generator)
        sub_graph.add_node("question_generator", question_generator)
        sub_graph.add_node("report_generator", report_generator)
        sub_graph.add_edge(START, "answer_evaluator")
        sub_graph.add_conditional_edges("answer_evaluator", topic_router)
        sub_graph.add_edge("follow_up_generator", "answer_evaluator")
        sub_graph.add_edge("question_generator", END)
        sub_graph.add_edge("report_generator", END)
        sub_graph = sub_graph.compile()

        current_state = await sub_graph.ainvoke(current_state)

    print("\n=== 면접 종료 ===")


if __name__ == "__main__":
    asyncio.run(main())
