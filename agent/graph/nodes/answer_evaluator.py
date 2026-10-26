"""
answer_evaluator 노드

예진님 ANSWER_EVALUATOR_SYSTEM_PROMPT + 페르소나 조합하여 답변 평가.
good_answer_criteria도 함께 전달하여 정확한 평가 유도.
eval_result의 eval_score를 State의 eval_score로 올리며, 이 값이 topic_router 분기 판단의 핵심이다.

예외: type이 "라포"인 첫 질문(라포 형성)은 채점하지 않고 중립 점수로 통과시킨다.
(LLM 호출도 하지 않는다 — 아래 RAPPORT_NEUTRAL_SCORE 주석 참고)
"""

import json
from langchain_core.messages import AIMessage, HumanMessage
from agent.parsers.answer_evaluator_prompt import (
    ANSWER_EVALUATOR_SYSTEM_PROMPT,
    VOICE_INPUT_NOTICE,
)
from agent.graph.state import InterviewState
from agent.graph.nodes.persona_selector import PERSONA_MAP
from agent.parsers.persona_prompts import PERSONA_TECH_LEAD
from agent.graph.utils import call_llm, is_rapport_question

# 라포 질문에 매길 중립 점수.
# topic_router.THRESHOLD(70)보다 확실히 높게 둬서 꼬리질문 분기로 새지 않게 한다.
# 다만 이 값에만 기대지 않는다 — THRESHOLD가 올라가도 버티도록 topic_router에도
# 같은 판정을 명시적으로 넣어뒀다(의도적 이중 안전장치).
RAPPORT_NEUTRAL_SCORE = 80

# eval_results 에 담을 세부 점수 키. 리포트의 category_scores 5개 항목과 같다.
# 화이트리스트라서 평가 프롬프트에 필드가 늘어도 여기 추가하지 않으면 리포트로 나가지 않는다.
CATEGORY_SCORE_FIELDS = (
    "logic_score",
    "communication_score",
    "expertise_score",
    "attitude_score",
    "problem_solving_score",
)


def _last_question(messages: list) -> str:
    """방금 답변한 질문. 마지막 AIMessage 가 그것이다.

    question_list 에서 꺼내지 않는 이유: 꼬리질문은 question_list 에 없고
    current_question_index 도 움직이지 않아, 꼬리질문 답변에 주질문 텍스트가 붙는다.
    """
    for msg in reversed(messages or []):
        if isinstance(msg, AIMessage):
            return msg.content
    return ""


def to_score_entry(eval_result: dict, order: int, question: str, is_follow_up: bool) -> dict:
    """채점 결과를 eval_results 원소로 추린다. (State 주석 참고)"""
    entry = {
        "order": order,
        "question": question,
        "is_follow_up": is_follow_up,
        "eval_score": eval_result.get("eval_score", 0),
    }
    for field in CATEGORY_SCORE_FIELDS:
        if eval_result.get(field) is not None:
            entry[field] = eval_result[field]
    return entry


async def answer_evaluator(state: InterviewState):
    question_list = state.get("question_list", [])
    current_index = state.get("current_question_index", 0)
    current_q = question_list[current_index] if question_list else {}

    # 라포 형성 질문은 채점하지 않는다.
    # 긴장을 풀어주려고 던지는 질문에 good_answer_criteria를 들이대면,
    # "네 안녕하세요 잘 부탁드립니다" 같은 답에 전문성·문제해결력까지 채점되어
    # 35점이 나오고 곧바로 꼬리질문이 붙는다(실측). 라포 형성이라는 목적이 무너진다.
    #
    # 누적 리듀서(eval_keywords·weakness_areas)에는 빈 리스트를 반환해
    # 라포 질문에서 뽑힌 키워드·약점이 리포트 입력에 섞이지 않게 한다.
    if is_rapport_question(current_q):
        return {
            "eval_score": RAPPORT_NEUTRAL_SCORE,
            "eval_result": {},
            "eval_keywords": [],
            "weakness_areas": [],
            "eval_results": []
        }

    # 마지막 사용자 답변 가져오기
    user_answer = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            user_answer = msg.content
            break

    persona_prompt = PERSONA_MAP.get(state.get("persona"), PERSONA_TECH_LEAD)
    system_prompt = persona_prompt + ANSWER_EVALUATOR_SYSTEM_PROMPT
    # 음성 답변(STT 변환)일 때만 말버릇 비감점 안내를 덧붙인다.
    # 미지정/"text"면 기존과 완전히 동일. (프롬프트 파일은 예진님 영역이라 노드에서 append)
    if state.get("input_type", "text") == "voice":
        system_prompt += VOICE_INPUT_NOTICE
    user_content = json.dumps({
        "question": current_q.get("question", ""),
        "good_answer_criteria": current_q.get("good_answer_criteria", ""),
        "answer": user_answer
    }, ensure_ascii=False)

    eval_result = await call_llm(system_prompt, user_content, stage="answer_evaluator")

    # 리포트가 쓸 점수를 누적 채널에 쌓는다. eval_score/eval_result 는 LastValue 라
    # 여기서 담아두지 않으면 report_generator 시점에 마지막 답변 것만 남는다.
    #
    # follow_up_count 는 follow_up_generator 가 꼬리질문을 낼 때 +1 되고
    # question_generator 가 새 주질문마다 0 으로 리셋한다. 그래서 이 시점의 값이
    # 0 이 아니면 방금 답한 것이 꼬리질문이다.
    entry = to_score_entry(
        eval_result,
        order=len(state.get("eval_results", [])) + 1,
        question=_last_question(state.get("messages", [])),
        is_follow_up=state.get("follow_up_count", 0) > 0,
    )

    return {
        "eval_score": eval_result.get("eval_score", 0),
        "eval_result": eval_result,
        "eval_keywords": eval_result.get("eval_keywords", []),
        "weakness_areas": eval_result.get("weaknesses", []),
        "eval_results": [entry]
    }
