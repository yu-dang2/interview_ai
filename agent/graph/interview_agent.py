"""
AI 면접관 에이전트 - 그래프 조립 및 실행

사용자 답변 수신은 노드가 아닌 while 루프에서 처리.
유정님 FastAPI 연동 시 실행 루프 부분 변경 예정.
"""

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

from graph.state import InterviewState
from graph.nodes.persona_selector import persona_selector
from graph.nodes.jd_parser import jd_parser
from graph.nodes.resume_parser import resume_parser
from graph.nodes.jd_resume_matcher import jd_resume_matcher
from graph.nodes.question_generator import question_generator
from graph.nodes.answer_evaluator import answer_evaluator
from graph.nodes.follow_up_generator import follow_up_generator
from graph.nodes.report_generator import report_generator
from graph.edges.topic_router import topic_router


# ── 그래프 조립 ────────────────────────────────────────
graph = StateGraph(InterviewState)

# 노드 등록
graph.add_node("persona_selector", persona_selector)
graph.add_node("jd_parser", jd_parser)
graph.add_node("resume_parser", resume_parser)
graph.add_node("jd_resume_matcher", jd_resume_matcher)
graph.add_node("question_generator", question_generator)
graph.add_node("answer_evaluator", answer_evaluator)
graph.add_node("follow_up_generator", follow_up_generator)
graph.add_node("report_generator", report_generator)

# 엣지 연결
# 초기 흐름: 페르소나 확인 → JD/이력서 파싱 → 매칭 → 첫 질문 생성
graph.add_edge(START, "persona_selector")
graph.add_edge("persona_selector", "jd_parser")
graph.add_edge("jd_parser", "resume_parser")
graph.add_edge("resume_parser", "jd_resume_matcher")
graph.add_edge("jd_resume_matcher", "question_generator")

# 순환 흐름: 답변 평가 → topic_router 분기 → 꼬리질문 or 다음질문 or 리포트
graph.add_conditional_edges("answer_evaluator", topic_router)
graph.add_edge("follow_up_generator", "answer_evaluator")
graph.add_edge("report_generator", END)

graph = graph.compile()


# ── 실행 루프 ──────────────────────────────────────────
# 유정님 FastAPI 연동 시 이 부분 변경 예정
if __name__ == "__main__":

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
        "persona": "깐깐한 기술 팀장",
        "eval_score": 0,
        "eval_result": {},
        "eval_keywords": [],
        "weakness_areas": [],
        "follow_up_count": 0,
        "turn_count": 0,
        "is_finished": False
    }

    # 초기 실행 (페르소나 확인 → JD/이력서 파싱 → 매칭 → 첫 질문 생성)
    current_state = graph.invoke(state)

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

        current_state = sub_graph.invoke(current_state)

    print("\n=== 면접 종료 ===")
