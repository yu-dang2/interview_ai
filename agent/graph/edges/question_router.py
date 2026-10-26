from agent.graph.state import InterviewState


def question_router(state: InterviewState):
    if state.get("is_finished", False):
        return "report_generator"
    return "continue"
