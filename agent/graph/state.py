from typing import Annotated, TypedDict, NotRequired
from langgraph.graph import MessagesState
from operator import add


class InterviewState(MessagesState):

    jd_raw: str
    resume_raw: str
    persona: str            # "기술 리드" / "인사 담당자" / "임원 면접관"

    jd_parsed: dict         # {"job_title", "required_skills", "preferred_skills", "soft_skills", ...}
    resume_parsed: dict     # {"name", "skills", "experience", "projects", "soft_skills", ...}
    match_result: dict      # {"matching_skills", "missing_skills", "interview_topics", ...}
    match_score: int        # 0~100
    question_list: list     # [{"question", "type", "intent", "good_answer_criteria", ...}]
                            # type: "라포"(첫 질문) / "기술" / "인성"

    retrieved_knowledge: list

    current_question_index: int
    eval_score: int         # 마지막 답변 값만 남는다. 전체 점수는 eval_results.
    eval_result: dict       # 마지막 답변만. 라포 질문은 {}.
                            # {"eval_score", "feedback", "strengths", "weaknesses", "eval_keywords",
                            #  "follow_up_needed", "follow_up_focus", 세부 점수 5종}
                            # 종합 점수 키는 "score"가 아니라 "eval_score"다.

    eval_keywords: Annotated[list, add]
    weakness_areas: Annotated[list, add]

    # 답변별 점수. 꼬리질문이 섞여 있어 question_list 와 1:1이 아니다(라포는 제외).
    eval_results: Annotated[list, add]

    follow_up_count: int    # 현재 주제의 꼬리질문 수. 새 주질문마다 0으로 리셋
    turn_count: int
    is_finished: bool

    input_type: str          # "text"(기본) | "voice"

    report_result: dict     # {"total_score", "grade", "is_early_terminated", "category_scores",
                            #  "category_comments", "summary", "keywords", "question_feedbacks"}

    resume_optimization: dict   # {"matched_keywords": [...], "missing_keywords": [...],
                                #  "suggestions": [{"id","section","original","improved","reason"}]}


class InterviewInput(TypedDict):
    jd_raw: str
    resume_raw: str
    persona: str
    is_finished: NotRequired[bool]   # 백엔드의 면접 종료 주입용 (기본 False)
    input_type: NotRequired[str]     # "text"(기본) | "voice"


class InterviewOutput(TypedDict):
    messages: list
    is_finished: bool
    report_result: dict
    match_score: int
    resume_optimization: dict
