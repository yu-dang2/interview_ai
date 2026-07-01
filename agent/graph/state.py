"""
State 스키마 정의

모든 노드가 공유하는 데이터 저장소.
노드끼리 직접 데이터를 주고받을 수 없고 반드시 State를 통해서만 공유됨.
"""

from typing import Annotated
from langgraph.graph import MessagesState
from operator import add


class InterviewState(MessagesState):

    # 지원님 UI에서 invoke() 시 전달
    jd_raw: str
    resume_raw: str
    persona: str            # "깐깐한 기술 팀장" / "공감형 인사 담당자" / "실무형 시니어 개발자"

    # 예진님 파서 결과
    jd_parsed: dict         # {"job_title", "required_skills", "preferred_skills", "soft_skills", ...}
    resume_parsed: dict     # {"name", "skills", "experience", "projects", "soft_skills", ...}
    match_result: dict      # {"matching_skills", "missing_skills", "interview_topics", ...}
    question_list: list     # [{"question", "intent", "good_answer_criteria", ...}]

    # 현재 진행 상태
    current_question_index: int
    eval_score: int         # 1~10점. topic_router가 THRESHOLD 기준으로 분기 판단
    eval_result: dict       # {"score", "feedback", "follow_up_needed", "follow_up_focus", ...}

    # 누적값 (면접 전체에서 쌓임)
    eval_keywords: Annotated[list, add]
    weakness_areas: Annotated[list, add]

    # 흐름 제어 (이현주 관리)
    follow_up_count: int    # 꼬리질문 횟수. 3회 초과 시 다음 주제로 강제 이동
    turn_count: int         # 전체 턴 수. MAX_TURNS 초과 시 종료
    is_finished: bool
