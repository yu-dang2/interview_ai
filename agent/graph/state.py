"""
State 스키마 정의

모든 노드가 공유하는 데이터 저장소.
노드끼리 직접 데이터를 주고받을 수 없고 반드시 State를 통해서만 공유됨.
"""

from typing import Annotated, TypedDict, NotRequired
from langgraph.graph import MessagesState
from operator import add


class InterviewState(MessagesState):

    # 지원님 UI에서 invoke() 시 전달
    jd_raw: str
    resume_raw: str
    persona: str            # "기술 리드" / "인사 담당자" / "임원 면접관"

    # 예진님 파서 결과
    jd_parsed: dict         # {"job_title", "required_skills", "preferred_skills", "soft_skills", ...}
    resume_parsed: dict     # {"name", "skills", "experience", "projects", "soft_skills", ...}
    match_result: dict      # {"matching_skills", "missing_skills", "interview_topics", ...}
    match_score: int        # JD-이력서 적합도 0~100 정수 (jd_resume_matcher 산출, 백엔드 노출)
    question_list: list     # [{"question", "intent", "good_answer_criteria", ...}]

    # 현재 진행 상태
    current_question_index: int
    eval_score: int         # 0~100점. topic_router가 THRESHOLD 기준으로 분기 판단
    eval_result: dict       # {"score", "feedback", "follow_up_needed", "follow_up_focus", ...}

    # 누적값 (면접 전체에서 쌓임)
    eval_keywords: Annotated[list, add]
    weakness_areas: Annotated[list, add]

    # 흐름 제어 (이현주 관리)
    follow_up_count: int    # 꼬리질문 횟수. 3회 초과 시 다음 주제로 강제 이동
    turn_count: int         # 전체 턴 수. MAX_TURNS 초과 시 종료
    is_finished: bool

    # 답변 입력 방식 (STT/TTS는 그래프 밖 백엔드 API에서 처리 — 그래프는 텍스트만 주고받음)
    input_type: str          # "text" | "voice". 백엔드가 답변 전송 시 주입, 미지정 시 "text".
                             # "voice"면 answer_evaluator가 음성 말버릇을 감점하지 않도록 안내를 덧붙임.

    # 최종 결과 (report_generator가 생성)
    report_result: dict     # {"total_score", "grade", "category_scores", "summary", "keywords", "question_feedbacks"}


class InterviewInput(TypedDict):
    jd_raw: str
    resume_raw: str
    persona: str
    # 백엔드가 면접 종료(예: 종료 버튼)를 invoke 입력으로 주입할 수 있도록 선택 필드로 노출.
    # update_state 경로로도 주입 가능하며, 미지정 시 기본 False로 동작한다.
    is_finished: NotRequired[bool]
    # 답변 입력 방식. 백엔드가 답변 전송 시 invoke 입력 또는 update_state로 주입.
    # is_finished와 동일한 패턴이며, 미지정 시 answer_evaluator가 "text"로 동작한다.
    input_type: NotRequired[str]


class InterviewOutput(TypedDict):
    messages: list
    is_finished: bool
    report_result: dict
    match_score: int
