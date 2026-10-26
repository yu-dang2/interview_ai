import json
from agent.parsers.jd_resume_matcher_prompt import JD_RESUME_MATCHER_SYSTEM_PROMPT
from agent.graph.state import InterviewState
from agent.graph.utils import call_llm

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

DEFAULT_MATCH_SCORE = 0


def _clamp_match_score(value) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return DEFAULT_MATCH_SCORE
    return max(0, min(100, score))


async def jd_resume_matcher(state: InterviewState):
    persona = state.get("persona", "")

    user_content = json.dumps({
        "jd": state["jd_parsed"],
        "resume": state["resume_parsed"],
        "persona": persona,
    }, ensure_ascii=False)

    system_prompt = JD_RESUME_MATCHER_SYSTEM_PROMPT + MATCH_SCORE_INSTRUCTION
    system_prompt += PERSONA_TOPIC_INSTRUCTION.get(persona, "")

    match_result = await call_llm(system_prompt, user_content, stage="jd_resume_matcher")
    raw = match_result.get("match_score") if isinstance(match_result, dict) else None
    match_score = _clamp_match_score(raw)
    return {"match_result": match_result, "match_score": match_score}
