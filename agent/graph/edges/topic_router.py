from agent.graph.state import InterviewState
from agent.graph.utils import is_rapport_question

MAX_TURNS = 10
THRESHOLD = 70
MAX_FOLLOW_UPS = 2


def topic_router(state: InterviewState):
    if state.get("is_finished", False):
        return "report_generator"

    if state.get("turn_count", 0) >= MAX_TURNS:
        return "report_generator"

    question_list = state.get("question_list", [])
    current_index = state.get("current_question_index", 0)
    if (current_index < len(question_list)
            and is_rapport_question(question_list[current_index])):
        return "question_generator"

    if (state.get("eval_score", 0) < THRESHOLD
            and state.get("follow_up_count", 0) < MAX_FOLLOW_UPS):
        return "follow_up_generator"

    return "question_generator"
