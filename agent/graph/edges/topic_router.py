"""
topic_router (Conditional Edge)

answer_evaluator 실행 후 어디로 갈지 판단.
노드가 아니므로 LLM 호출 없이 State 값만으로 분기 결정.

분기 조건:
    1. is_finished == True           → report_generator (중도 종료 / 질문 소진)
    2. turn_count >= MAX_TURNS       → report_generator (턴 수 초과)
    3. 현재 질문 type == "자기소개"   → question_generator (라포 질문은 꼬리질문 없이 통과)
    4. eval_score < THRESHOLD
       + follow_up_count < MAX_FOLLOW_UPS → follow_up_generator (꼬리질문)
    5. 그 외                         → question_generator (다음 질문)

1번은 백엔드가 중도 종료를 주입한 경우다. 예전에는 END로 직행해 리포트 없이
끝났으나, "abandoned 세션도 리포트 저장 대상" 합의에 따라 report_generator를
거치도록 변경했다. 중도 종료 여부는 report_generator가 turn_count로 재판정한다.

# 0~100점 기준
"""

from agent.graph.state import InterviewState
from agent.graph.utils import is_intro_question

MAX_TURNS = 10    # 예진님과 합의 후 수정
THRESHOLD = 70    # 예진님 평가 점수 기준 (70점 미만 = 꼬리질문)

# 한 주제에서 이어갈 수 있는 꼬리질문 수. 누적이 아니라 주제당 상한이다
# (question_generator가 새 질문마다 follow_up_count를 0으로 리셋한다).
# 3 → 2 로 줄였다. 답변이 계속 기준 미만이면 한 주제에서 주질문 1 + 꼬리 3 = 4문항이
# 연달아 나와 면접이 늘어졌다. 2면 한 주제 최대 3문항이 된다.
MAX_FOLLOW_UPS = 2


def topic_router(state: InterviewState):
    if state.get("is_finished", False):
        return "report_generator"

    if state.get("turn_count", 0) >= MAX_TURNS:
        return "report_generator"

    # 자기소개(라포 형성) 질문에는 꼬리질문을 붙이지 않는다.
    # 긴장 풀라고 던진 질문을 파고들면 라포 형성이라는 목적 자체가 무너진다.
    # (실측에서 "현재 직책과 총 경력 몇 년인지 말씀해 주시겠어요?" 같은 추궁이 붙었다)
    #
    # answer_evaluator가 이미 중립 점수를 줘서 아래 조건에 걸리지 않지만,
    # THRESHOLD나 중립 점수가 바뀌어도 버티도록 여기서 한 번 더 명시한다.
    # 범위 체크는 필수 — 질문 소진 시 question_generator가 인덱스를
    # len(question_list)까지 올린다.
    question_list = state.get("question_list", [])
    current_index = state.get("current_question_index", 0)
    if (current_index < len(question_list)
            and is_intro_question(question_list[current_index])):
        return "question_generator"

    if (state.get("eval_score", 0) < THRESHOLD
            and state.get("follow_up_count", 0) < MAX_FOLLOW_UPS):
        return "follow_up_generator"

    return "question_generator"
