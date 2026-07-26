"""
question_router (Conditional Edge)

question_generator 실행 후 어디로 갈지 판단.
노드가 아니므로 LLM 호출 없이 State 값만으로 분기 결정.

분기 조건:
    1. is_finished == True  → report_generator
       (백엔드가 종료를 주입했거나, question_generator가 질문 소진 시 설정)
    2. 그 외                → "continue"
       (build_graph에서 토폴로지별 대상으로 매핑:
        interrupt 모드 → answer_evaluator, 아니면 END)

is_finished는 백엔드가 State에 주입하거나 question_generator가 질문 소진 시 설정한다.
report_generator가 종료 시 is_finished=True를 설정하는 정상 종료 경로와 공존한다.
"""

from agent.graph.state import InterviewState


def question_router(state: InterviewState):
    if state.get("is_finished", False):
        return "report_generator"
    return "continue"
