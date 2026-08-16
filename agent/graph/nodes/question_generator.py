"""
question_generator 노드
작성: 이현주

예진님 QUESTION_GENERATOR_SYSTEM_PROMPT + 페르소나 조합하여 질문 목록 생성.
- 첫 실행: 질문 목록 생성 후 첫 번째 질문 반환
- 이후 실행: 다음 질문으로 인덱스 이동
- 질문 소진 시 is_finished = True로 설정하여 종료 트리거
"""

import json
from langchain_core.messages import AIMessage
from agent.parsers.question_generator_prompt import QUESTION_GENERATOR_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.nodes.persona_selector import PERSONA_MAP
from agent.parsers.persona_prompts import PERSONA_TECH_LEAD
from agent.graph.utils import call_llm

# 프롬프트 파일은 수정 불가 → 노드에서 지시문을 이어붙인다.
# (jd_resume_matcher 의 MATCH_SCORE_INSTRUCTION 과 같은 패턴)
#
# 이 지시문이 RAG 도입의 성패를 가른다. 기존 프롬프트 규칙 4번이 "이력서 내용을 구체적으로
# 언급하라"인데, 직무 지식을 그대로 질문화하면 "캐싱 경험 있으신가요?" 같은 누구에게나
# 하는 뻔한 질문으로 퇴행한다. JD·이력서가 주재료임을 명시적으로 못박아야 한다.
RETRIEVAL_INSTRUCTION = """

[추가 지시 - 직무 지식 참고]
아래 reference_knowledge는 이 직무에서 일반적으로 평가하는 관점입니다.
채용공고(JD)와 지원자 이력서가 우선이며, 이 지식은 질문을 더 전문적으로 만들기 위한
보조 참고자료입니다.
- 이 관점을 그대로 질문으로 만들지 마세요. 반드시 지원자 이력서의 구체적 경험과 결합해
  재작성하세요.
- 관련성이 낮은 항목은 무시하세요.
- 참고자료에 있다는 이유만으로 이력서에 근거가 없는 주제를 질문하지 마세요.
"""

# 프롬프트에 실어 보낼 카드 필드. aliases·related_keywords·scope_summary 는 검색용이라 빼고,
# _distance 같은 검색 메타와 _주의 같은 편집자용 주석도 뺀다(LLM 에게는 노이즈).
# 화이트리스트라서 카드에 새 필드가 생겨도 여기 추가하지 않으면 프롬프트로 나가지 않는다.
_PROMPT_FIELDS = (
    "job_family",
    # 신 스키마: LLM 이 스스로 만들어내지 못하는 구체 정보
    "trend_2026",
    "real_questions",
    "deep_dive_patterns",
    "common_pitfalls",
    # 구 스키마 호환
    "core_competencies",
    "evaluation_points",
    "industry_trends",
    "interview_perspective",
)


def _to_reference(cards: list) -> list:
    """검색 결과 카드를 프롬프트용으로 추린다."""
    reference = []
    for card in cards or []:
        if not isinstance(card, dict):
            continue
        picked = {f: card[f] for f in _PROMPT_FIELDS if card.get(f)}
        if picked:
            reference.append(picked)
    return reference


async def question_generator(state: InterviewState):
    current_index = state.get("current_question_index", 0)
    question_list = state.get("question_list", [])

    # 첫 실행: 예진님 프롬프트로 질문 목록 생성
    if not question_list:
        persona_prompt = PERSONA_MAP.get(state.get("persona"), PERSONA_TECH_LEAD)
        system_prompt = persona_prompt + QUESTION_GENERATOR_SYSTEM_PROMPT

        payload = {
            "match_result": state["match_result"],
            "resume": state["resume_parsed"]
        }

        # 검색 결과가 있을 때만 지시문과 참고자료를 붙인다. 빈 배열을 주면서 "참고하라"고
        # 하면 모델이 없는 자료를 찾으려 든다. (인덱스 미구축·검색 실패 시 기존과 동일 동작)
        reference = _to_reference(state.get("retrieved_knowledge", []))
        if reference:
            system_prompt += RETRIEVAL_INSTRUCTION
            payload["reference_knowledge"] = reference

        user_content = json.dumps(payload, ensure_ascii=False)
        result = await call_llm(system_prompt, user_content)
        question_list = result.get("questions", [])
        current_index = 0
    else:
        # 이후 실행: 다음 질문으로 이동
        current_index += 1

    # 질문 소진 시 종료
    if current_index >= len(question_list):
        return {
            "question_list": question_list,
            "current_question_index": current_index,
            "is_finished": True
        }

    current_q = question_list[current_index]
    return {
        "messages": [AIMessage(content=current_q["question"])],
        "question_list": question_list,
        "current_question_index": current_index,
        "turn_count": state.get("turn_count", 0) + 1,
        "follow_up_count": 0    # 새 주제 시작 시 꼬리질문 횟수 초기화
    }
