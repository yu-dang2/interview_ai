"""
topic_router (Conditional Edge)

answer_evaluator 실행 후 어디로 갈지 판단.
노드가 아니므로 LLM 호출 없이 State 값만으로 분기 결정.

분기 조건:
    1. is_finished == True           → END (질문 소진)
    2. turn_count >= MAX_TURNS       → report_generator (턴 수 초과)
    3. eval_score < THRESHOLD
       + follow_up_count < 3        → follow_up_generator (꼬리질문)
    4. 그 외                         → question_generator (다음 질문)
"""

from langgraph.graph import END
from graph.state import InterviewState

MAX_TURNS = 5    # 예진님과 합의 후 수정
THRESHOLD = 7    # 예진님 평가 점수 기준 (7점 미만 = 꼬리질문)


def topic_router(state: InterviewState):
    if state.get("is_finished", False):
        return END

    if state.get("turn_count", 0) >= MAX_TURNS:
        return "report_generator"

    if state.get("eval_score", 0) < THRESHOLD and state.get("follow_up_count", 0) < 3:
        return "follow_up_generator"

    return "question_generator"
