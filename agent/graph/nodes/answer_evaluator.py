"""
answer_evaluator 노드

예진님 ANSWER_EVALUATOR_SYSTEM_PROMPT + 페르소나 조합하여 답변 평가.
good_answer_criteria도 함께 전달하여 정확한 평가 유도.
eval_result의 eval_score를 State의 eval_score로 올리며, 이 값이 topic_router 분기 판단의 핵심이다.

예외: type이 "자기소개"인 라포 형성 질문은 채점하지 않고 중립 점수로 통과시킨다.
(LLM 호출도 하지 않는다 — 아래 INTRO_NEUTRAL_SCORE 주석 참고)
"""

import json
from langchain_core.messages import HumanMessage
from agent.parsers.answer_evaluator_prompt import (
    ANSWER_EVALUATOR_SYSTEM_PROMPT,
    VOICE_INPUT_NOTICE,
)
from agent.graph.state import InterviewState
from agent.graph.nodes.persona_selector import PERSONA_MAP
from agent.parsers.persona_prompts import PERSONA_TECH_LEAD
from agent.graph.utils import call_llm, is_intro_question

# 자기소개 질문에 매길 중립 점수.
# topic_router.THRESHOLD(70)보다 확실히 높게 둬서 꼬리질문 분기로 새지 않게 한다.
# 다만 이 값에만 기대지 않는다 — THRESHOLD가 올라가도 버티도록 topic_router에도
# 같은 판정을 명시적으로 넣어뒀다(의도적 이중 안전장치).
INTRO_NEUTRAL_SCORE = 80


async def answer_evaluator(state: InterviewState):
    question_list = state.get("question_list", [])
    current_index = state.get("current_question_index", 0)
    current_q = question_list[current_index] if question_list else {}

    # 자기소개(라포 형성) 질문은 채점하지 않는다.
    # 긴장을 풀어주려고 던지는 질문에 good_answer_criteria를 들이대면,
    # "네 안녕하세요 잘 부탁드립니다" 같은 답에 전문성·문제해결력까지 채점되어
    # 35점이 나오고 곧바로 꼬리질문이 붙는다(실측). 라포 형성이라는 목적이 무너진다.
    #
    # 누적 리듀서(eval_keywords·weakness_areas)에는 빈 리스트를 반환해
    # 자기소개에서 뽑힌 키워드·약점이 리포트 입력에 섞이지 않게 한다.
    if is_intro_question(current_q):
        return {
            "eval_score": INTRO_NEUTRAL_SCORE,
            "eval_result": {},
            "eval_keywords": [],
            "weakness_areas": []
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

    eval_result = await call_llm(system_prompt, user_content)
    return {
        "eval_score": eval_result.get("eval_score", 0),
        "eval_result": eval_result,
        "eval_keywords": eval_result.get("eval_keywords", []),
        "weakness_areas": eval_result.get("weaknesses", [])
    }
