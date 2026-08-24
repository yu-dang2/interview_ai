"""
jd_resume_matcher 노드
작성: 이현주

예진님 JD_RESUME_MATCHER_SYSTEM_PROMPT 사용하여
JD와 이력서 비교 → 강점/약점/면접 주제 산출.

페르소나를 함께 받아 interview_topics 구성을 조정한다. 이 노드가 만드는 주제 목록이
question_generator 의 유일한 재료라서, 여기서 기술로 쏠리면 인사·임원 면접인데도
기술 질문이 나온다. (아래 PERSONA_TOPIC_INSTRUCTION 주석 참고)
"""

import json
from agent.parsers.jd_resume_matcher_prompt import JD_RESUME_MATCHER_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.utils import call_llm

# 프롬프트 파일은 수정 불가 → 노드에서 match_score 산출 지시를 이어붙임.
MATCH_SCORE_INSTRUCTION = """

[추가 지시 - 적합도 점수]
위 JSON 최상위에 match_score(JD-이력서 적합도, 0~100 정수) 키를 추가로 포함하세요.
- 필수 기술(required_skills) 충족도를 가장 크게 반영하세요.
- 우대 기술, 경력 연차, 프로젝트 관련성은 보조 지표로 반영하세요.
- 반드시 0~100 사이의 정수 하나로 출력하세요.
- match_score는 JD와 이력서만 비교한 순수 적합도입니다. 입력의 persona나 아래 면접관
  페르소나 지시는 interview_topics 구성에만 적용하고, match_score 산출에는 절대 반영하지
  마세요. 같은 JD·이력서라면 어떤 페르소나로 면접하든 같은 점수가 나와야 합니다.
"""

# 페르소나별 interview_topics 구성 지시. 역시 프롬프트 파일을 못 고치므로 노드에서 이어붙인다.
#
# 왜 필요한가:
#   이 노드는 원래 페르소나를 몰랐다. 그래서 interview_topics 가 기술 6 : 인성 1 로 쏠렸고,
#   question_generator 는 그 기술 주제 더미를 받아놓고 "인사·임원이면 기술 질문 하지 마라"는
#   지시만 받는 모순에 놓였다. 실측에서 인사 2/5, 임원 3/5 가 기술 질문으로 나왔고,
#   인성 질문은 6회 생성 내내 같은 소재(멘토링) 하나뿐이었다. 쓸 재료가 그것뿐이었기 때문이다.
#   질문 단계에서 막는 대신 재료 단계에서 인성 주제를 확보한다.
#
# 왜 개수를 숫자로 못박는가:
#   question_generator 프롬프트는 이미 "절대 하지 마세요", "★ 매우 중요"까지 썼는데도
#   기술 질문이 나왔다. 정성적 표현은 약하다. 최소 개수로 지정해야 검증도 가능하다.
#
# 기술 리드는 일부러 비워둔다. 현재 잘 동작하고(기술 4/5) 바꿀 이유가 없어 회귀만 부른다.
PERSONA_TOPIC_INSTRUCTION = {
    "인사 담당자": """

[추가 지시 - 면접관 페르소나: 인사 담당자]
이번 면접은 인사 담당자가 진행합니다. interview_topics를 아래 기준으로 구성하세요.
- interview_topics 중 최소 4개는 type을 "인성"으로 하고, 주제 자체를 협업·갈등 해결·
  멘토링·학습과 성장·지원 동기·팀에서의 역할로 잡으세요.
- type이 "기술"인 주제는 최대 2개까지만 넣으세요.
- 인성 주제의 소재는 resume의 성과 수치가 아니라 그 과정에서의 사람·협업·배움에서 찾으세요.
  이력서에 협업 경험이 적게 적혀 있어도, 지원 동기·성장 목표·어려움을 극복한 경험처럼
  기술과 무관한 주제로 채우세요.
- ★ 라벨만 바꾸지 마세요. type을 "인성"으로 적어놓고 topic이나 sample_question이
  성능 최적화·쿼리 튜닝·캐시 설계·아키텍처·장애 원인 분석처럼 기술 설명을 요구하면 잘못된
  것입니다. 판별 기준은 하나입니다: 그 질문에 답하려면 기술 지식을 설명해야 한다면
  인성 주제가 아닙니다.
""",
    "임원 면접관": """

[추가 지시 - 면접관 페르소나: 임원 면접관]
이번 면접은 임원(CTO/본부장)이 진행하는 최종 면접입니다. interview_topics를 아래 기준으로
구성하세요.
- interview_topics 중 최소 4개는 type을 "인성"으로 하고, 주제를 비즈니스 임팩트·
  우선순위 판단·리더십과 팔로워십·장기 커리어 비전·회사 기여로 잡으세요.
- type이 "기술"인 주제는 최대 2개까지만 넣고, 그 경우에도 구현 방식이 아니라 그 기술이
  만든 성과와 그렇게 판단한 근거를 묻는 주제로 잡으세요.
- ★ 라벨만 바꾸지 마세요. type을 "인성"으로 적어놓고 topic이나 sample_question이
  캐시 무효화 전략·인덱스 설계·시스템 아키텍처처럼 기술 구현 설명을 요구하면 잘못된
  것입니다. 판별 기준은 하나입니다: 그 질문에 답하려면 기술 지식을 설명해야 한다면
  인성 주제가 아닙니다.
""",
}

# match_score 파싱 실패/범위 밖일 때의 안전한 기본값 (미산출을 낮게 표기해 눈에 띄게)
DEFAULT_MATCH_SCORE = 0


def _clamp_match_score(value) -> int:
    """LLM이 준 match_score를 0~100 정수로 방어적으로 변환 (실패 시 기본값)."""
    try:
        score = int(value)
    except (TypeError, ValueError):
        return DEFAULT_MATCH_SCORE
    return max(0, min(100, score))


async def jd_resume_matcher(state: InterviewState):
    # persona_selector 가 START 직후에 돌면서 PERSONA_MAP 의 3종 중 하나로 정규화해 둔다.
    # (미지의 값은 거기서 "기술 리드"로 폴백하므로 여기서 다시 검사하지 않는다)
    persona = state.get("persona", "")

    user_content = json.dumps({
        "jd": state["jd_parsed"],
        "resume": state["resume_parsed"],
        "persona": persona,
    }, ensure_ascii=False)

    system_prompt = JD_RESUME_MATCHER_SYSTEM_PROMPT + MATCH_SCORE_INSTRUCTION
    # 기술 리드는 매핑에 없으므로 아무것도 붙지 않는다(현행 동작 유지).
    system_prompt += PERSONA_TOPIC_INSTRUCTION.get(persona, "")

    match_result = await call_llm(system_prompt, user_content, stage="jd_resume_matcher")
    raw = match_result.get("match_score") if isinstance(match_result, dict) else None
    match_score = _clamp_match_score(raw)
    # 기존 match_result 반환은 그대로 유지, match_score만 추가
    return {"match_result": match_result, "match_score": match_score}
