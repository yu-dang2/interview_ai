"""
report_generator 노드
작성: 이현주

TODO: 예진님 리포트 프롬프트 받으면 통합 예정.
현재는 면접 요약만 제공.
"""

from langchain_core.messages import AIMessage
from graph.state import InterviewState


def report_generator(state: InterviewState):
    # TODO: 예진님 리포트 프롬프트 통합 예정
    report = (
        f"=== 면접 결과 리포트 ===\n"
        f"총 면접 턴 수: {state.get('turn_count', 0)}\n"
        f"확인된 강점: {', '.join(state.get('eval_keywords', []))}\n"
        f"확인된 약점: {', '.join(state.get('weakness_areas', []))}\n"
        f"\n[예진님 리포트 프롬프트 통합 후 상세 결과 제공 예정]"
    )
    return {
        "messages": [AIMessage(content=report)],
        "is_finished": True
    }
