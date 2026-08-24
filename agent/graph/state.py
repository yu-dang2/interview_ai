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
    question_list: list     # [{"question", "type", "intent", "good_answer_criteria", ...}]
                            # type: "라포"(첫 질문, 라포 형성) / "기술" / "인성".
                            # 그래프는 type 으로 분기한다(agent.graph.utils.is_rapport_question).
                            # 라포 질문은 채점 대상이 아니라서 answer_evaluator 가 LLM 호출
                            # 없이 중립 점수를 주고, topic_router 가 꼬리질문을 붙이지 않으며,
                            # report_generator 가 총점·항목점수·개별 피드백에서 제외한다.

    # 직무 지식 카드 검색 결과 (question_retriever 산출, question_generator 참고자료)
    # JD가 질문의 주재료이고 이건 관점을 보태는 보조 자료다. 검색 실패·미설치 시 [].
    retrieved_knowledge: list

    # 현재 진행 상태
    current_question_index: int
    eval_score: int         # 0~100점. topic_router가 THRESHOLD 기준으로 분기 판단.
                            # LastValue 라 마지막 답변 것만 남는다. 리포트가 쓸 전체 점수는
                            # 아래 eval_results 누적 채널에 있다.
                            # 단 라포 질문은 채점하지 않고 고정 중립 점수가 들어간다
                            # (answer_evaluator.RAPPORT_NEUTRAL_SCORE) — 답변 품질과 무관하다.
    eval_result: dict       # answer_evaluator 프롬프트 출력 그대로. 라포 질문은 {}.
                            # 이것도 LastValue 다(위 eval_score 와 같은 이유).
                            # {"eval_score", "feedback", "strengths", "weaknesses", "eval_keywords",
                            #  "follow_up_needed", "follow_up_focus",
                            #  세부 점수 5종(logic/communication/expertise/attitude/problem_solving_score)}
                            # 종합 점수 키는 "score"가 아니라 "eval_score"다.

    # 누적값 (면접 전체에서 쌓임)
    eval_keywords: Annotated[list, add]
    weakness_areas: Annotated[list, add]

    # 답변별 채점 결과. report_generator 가 총점·항목점수를 산출할 입력이다.
    # eval_score/eval_result 는 LastValue 라 마지막 답변 것만 남는데, 리포트 프롬프트는
    # "각 답변의 평가 결과를 종합·평균하라"고 지시한다. 그 입력을 여기서 만든다.
    # 없으면 LLM 이 답변 원문만 보고 재채점해 실시간 평가와 총점이 어긋난다.
    #
    # 원소는 answer_evaluator.to_score_entry() 가 만든다. eval_result 전문이 아니라
    # 점수 필드만 추린다 — feedback·follow_up_focus 까지 넣으면 프롬프트가 비대해지고
    # 리포트에 엉뚱하게 반영된다. 강점·약점·키워드는 이미 별도 누적 채널로 나간다.
    #
    # 꼬리질문 답변도 answer_evaluator 를 거치므로 자연히 포함된다.
    # 라포 질문은 answer_evaluator 가 빈 리스트를 반환해 담기지 않는다.
    # question_list 와 1:1 로 짝지으면 안 된다 — 꼬리질문은 question_list 에 없다.
    eval_results: Annotated[list, add]

    # 흐름 제어 (이현주 관리)
    follow_up_count: int    # 꼬리질문 횟수. topic_router.MAX_FOLLOW_UPS 도달 시 다음 주제로 이동
    turn_count: int         # 전체 턴 수. MAX_TURNS 초과 시 종료
    is_finished: bool

    # 답변 입력 방식 (STT/TTS는 그래프 밖 백엔드 API에서 처리 — 그래프는 텍스트만 주고받음)
    input_type: str          # "text" | "voice". 백엔드가 답변 전송 시 주입, 미지정 시 "text".
                             # "voice"면 answer_evaluator가 음성 말버릇을 감점하지 않도록 안내를 덧붙임.

    # 최종 결과 (report_generator가 생성)
    report_result: dict     # {"total_score", "grade", "is_early_terminated", "category_scores",
                            #  "category_comments", "summary", "keywords", "question_feedbacks"}
                            # is_early_terminated: 중도 종료 여부. report_generator가
                            # current_question_index < len(question_list) 로 판정해 넣는다.

    # 이력서 자동 최적화 (resume_optimizer가 종료 직전 생성, 화면·DB 기준 키로 정규화)
    # matched_keywords: JD 키워드 중 이력서에 이미 있는 것 (화면 "보유 키워드")
    # missing_keywords: JD 키워드 중 이력서에 없는 것 (화면 "추가 추천 키워드")
    # suggestions:      항목별 문구 개선 제안
    resume_optimization: dict   # {"matched_keywords": [...], "missing_keywords": [...],
                                #  "suggestions": [{"id","section","original","improved","reason"}]}


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
    resume_optimization: dict
