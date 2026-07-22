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

    # 최종 결과 (report_generator가 생성)
    report_result: dict     # {"total_score", "grade", "category_scores", "summary", "keywords", "question_feedbacks"}

    # STT/TTS 인터페이스 (백엔드 오디오 API 연동용, 아직 그래프에 미연결)
    audio_input: str         # STT 입력: 오디오 base64/URL (프론트/백엔드 제공)
    transcribed_text: str    # STT 출력: 전사 텍스트 (stt_node가 채움)
    audio_output: str        # TTS 출력: 합성 오디오 base64/URL (tts_node가 채움)


class InterviewInput(TypedDict):
    jd_raw: str
    resume_raw: str
    persona: str
    # 백엔드가 면접 종료(예: 종료 버튼)를 invoke 입력으로 주입할 수 있도록 선택 필드로 노출.
    # update_state 경로로도 주입 가능하며, 미지정 시 기본 False로 동작한다.
    is_finished: NotRequired[bool]


class InterviewOutput(TypedDict):
    messages: list
    is_finished: bool
    report_result: dict
    match_score: int
