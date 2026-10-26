from typing import Annotated, TypedDict, NotRequired
from langgraph.graph import MessagesState
from operator import add


class InterviewState(MessagesState):

    jd_raw: str
    resume_raw: str
    persona: str

    jd_parsed: dict
    resume_parsed: dict
    match_result: dict
    match_score: int
    question_list: list

    retrieved_knowledge: list

    current_question_index: int
    eval_score: int         # 마지막 답변 값만 남는다. 전체 점수는 eval_results.
    eval_result: dict       # 마지막 답변만. 라포 질문은 {}. 종합 점수 키는 "score"가 아니라 "eval_score"다.

    eval_keywords: Annotated[list, add]
    weakness_areas: Annotated[list, add]

    # 답변별 점수. 꼬리질문이 섞여 있어 question_list 와 1:1이 아니다(라포는 제외).
    eval_results: Annotated[list, add]

    follow_up_count: int
    turn_count: int
    is_finished: bool

    input_type: str

    report_result: dict

    resume_optimization: dict


class InterviewInput(TypedDict):
    jd_raw: str
    resume_raw: str
    persona: str
    is_finished: NotRequired[bool]
    input_type: NotRequired[str]     # "text"(기본) | "voice"


class InterviewOutput(TypedDict):
    messages: list
    is_finished: bool
    report_result: dict
    match_score: int
    resume_optimization: dict
