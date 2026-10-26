import os
import json
import asyncio
import logging

from openai import AsyncOpenAI, OpenAIError

logger = logging.getLogger(__name__)

# 라포 형성 질문의 type 값. question_generator 프롬프트가 첫 질문에 부여한다.
# 이 질문은 지원자의 긴장을 풀어주는 것이 목적이라 채점·꼬리질문 대상이 아니다.
RAPPORT_TYPE = "라포"


def is_rapport_question(question: dict) -> bool:
    """라포 형성 질문이면 True. (채점·꼬리질문·리포트 집계에서 제외)

    type 은 LLM 이 채우는 값이라 누락되거나 공백이 섞일 수 있어 방어적으로 비교한다.
    인덱스 기반 폴백(첫 질문이면 라포로 간주)은 일부러 두지 않는다.
    폴백이 있으면 프롬프트가 type 을 빠뜨려도 조용히 넘어가 회귀를 놓친다.
    """
    return (question.get("type") or "").strip() == RAPPORT_TYPE


def get_client():
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── reasoning 강도 (노드별) ────────────────────────────────
# 미지정이면 create() 에 인자 자체를 넘기지 않는다. 즉 아무것도 설정하지 않은 환경에서는
# 이 기능을 넣기 전과 100% 동일하게 동작한다(회귀 위험 0).
#
#   REASONING_EFFORT              전 노드 기본값
#   REASONING_EFFORT_<STAGE>      특정 노드만. STAGE 는 call_llm(stage=...) 에 넘긴 이름.
#                                 예: REASONING_EFFORT_QUESTION_GENERATOR=medium
#
# 노드별로 나눠둔 이유: 로딩 경로(파싱·매칭·질문생성)와 면접 중 경로(채점·꼬리질문·리포트)의
# 품질 요구가 다르다. 로딩만 낮추고 채점·리포트는 그대로 두는 조합이 가능해야 한다.
REASONING_EFFORTS = ("minimal", "low", "medium", "high")

# 노드별 모델.
#   LLM_MODEL / LLM_MODEL_<STAGE>   (reasoning 과 같은 규칙)
DEFAULT_MODEL = "gpt-5-mini"

# 노드별 확정 기본값 (2026-08-24 팀 결정 — 면접 로딩 속도 개선).
# 값을 정한 근거:
#   resume_parser  이력서 5종(깔끔·표/불릿·장문·형식흐트러짐·수치다수) x 3회 실측에서
#                  gpt-4o-mini 가 gpt-5-mini 대비 항목 누락 0, 장문에서는 오히려 더 잘 뽑았다.
#                  최상위 키 구성도 15개 조합 전부 동일. 21.5s -> 3.7s(표/불릿 기준).
#   jd_resume_matcher  reasoning low 로 36.6s -> 24.8s. 페르소나 편향(인성>=4, 기술<=2)
#                  회귀를 별도로 확인했다.
#
# 여기에 없는 노드는 일부러 비워둔다. 그래야 요청에 인자가 실리지 않아 현행과 완전히 같다.
#   question_generator  gpt-5-mini 기본이 이미 medium 이라 낮출 이유가 없다. low 로 내리면
#                       "한 질문에 개념 3개 이상"이 30문항 중 5건 -> 10건으로 늘었다(음성 면접에 치명적).
#   answer_evaluator / follow_up_generator / report_generator / resume_optimizer
#                       면접 중 품질에 직결되어 건드리지 않는다.
#
# 환경변수가 있으면 이 값보다 환경변수가 우선한다(아래 model_for / reasoning_effort 참고).
STAGE_DEFAULTS = {
    "resume_parser": {"model": "gpt-4o-mini"},
    "jd_resume_matcher": {"reasoning_effort": "low"},
}

# reasoning_effort 를 받는 모델 계열. gpt-4o 계열은 추론 모델이 아니라 이 인자를 거부한다.
REASONING_MODEL_PREFIXES = ("gpt-5", "o1", "o3", "o4")

_effort_warned = set()   # 같은 경고를 매 호출마다 찍지 않기 위한 플래그


def model_for(stage: str | None = None) -> str:
    """이 호출에 쓸 모델.

    우선순위: LLM_MODEL_<STAGE> > LLM_MODEL > STAGE_DEFAULTS > DEFAULT_MODEL.
    """
    keys = [f"LLM_MODEL_{stage.upper()}"] if stage else []
    keys.append("LLM_MODEL")
    for key in keys:
        value = (os.getenv(key) or "").strip()
        if value and value.lower() != "default":
            return value
    return STAGE_DEFAULTS.get(stage, {}).get("model", DEFAULT_MODEL)


def supports_reasoning(model: str) -> bool:
    return any(model.startswith(p) for p in REASONING_MODEL_PREFIXES)


def reasoning_effort(stage: str | None = None) -> str | None:
    """이 호출에 쓸 reasoning 강도. None 이면 인자를 넘기지 않는다(API 기본값).

    우선순위: REASONING_EFFORT_<STAGE> > REASONING_EFFORT > STAGE_DEFAULTS > None.
    """
    keys = [f"REASONING_EFFORT_{stage.upper()}"] if stage else []
    keys.append("REASONING_EFFORT")

    for key in keys:
        value = (os.getenv(key) or "").strip().lower()
        if not value or value == "default":
            continue
        if value in REASONING_EFFORTS:
            return value
        # 오타를 조용히 무시하면 "설정했는데 왜 안 빨라지지"로 되돌아온다.
        logger.warning(
            "%s 값이 올바르지 않아 무시합니다: %r (허용: %s)",
            key, value, ", ".join(REASONING_EFFORTS),
        )
    return STAGE_DEFAULTS.get(stage, {}).get("reasoning_effort")


def _clean_json_text(text: str) -> str:
    """LLM 응답에서 마크다운 코드펜스(```json ... ```)와 앞뒤 공백 제거"""
    text = (text or "").strip()
    if text.startswith("```"):
        # 첫 줄(``` 또는 ```json)을 통째로 제거
        text = text.split("\n", 1)[1] if "\n" in text else ""
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


async def call_llm(
    system_prompt: str,
    user_content: str,
    max_retries: int = 3,
    stage: str | None = None,
) -> dict:
    """
    LLM 호출 후 JSON 파싱하여 반환.

    API 호출 실패(네트워크/rate limit/타임아웃)와 JSON 파싱 실패를 재시도한다.
    재시도 간격은 지수 백오프(1초 → 2초 → 4초).
    max_retries회 모두 실패하면 RuntimeError를 발생시킨다. (조용히 None을 반환하지 않음)

    stage 는 이 호출이 어느 노드에서 왔는지를 나타내는 이름이다. 모델과 reasoning 강도를
    노드별로 다르게 주기 위한 것이다(STAGE_DEFAULTS 참고). 지정된 값이 없는 노드는
    모델은 DEFAULT_MODEL 을 쓰고 reasoning_effort 는 요청에 아예 싣지 않는다.
    """
    last_error = None

    # 요청마다 다시 읽지 않도록 루프 밖에서 한 번만 결정한다.
    model = model_for(stage)
    effort = reasoning_effort(stage)
    request = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }
    if effort and supports_reasoning(model):
        request["reasoning_effort"] = effort
    elif effort:
        # gpt-4o 계열에 reasoning_effort 를 보내면 400 이 난다. 조용히 빼면 "왜 안 빨라지지"가
        # 되므로 조합당 한 번 알린다.
        if (stage, model) not in _effort_warned:
            _effort_warned.add((stage, model))
            logger.warning(
                "%s 는 reasoning_effort 를 지원하지 않아 무시합니다 (stage=%s, effort=%s)",
                model, stage or "-", effort,
            )

    for attempt in range(1, max_retries + 1):
        try:
            client = get_client()
            response = await client.chat.completions.create(**request)
            text = _clean_json_text(response.choices[0].message.content)
            return json.loads(text)

        except (OpenAIError, json.JSONDecodeError) as e:
            last_error = e
            if attempt == max_retries:
                break

            wait_seconds = 2 ** (attempt - 1)    # 1초 → 2초 → 4초
            logger.warning(
                "call_llm 실패 (%d/%d회, stage=%s): %s: %s — %d초 후 재시도",
                attempt, max_retries, stage or "-", type(e).__name__, e, wait_seconds
            )
            await asyncio.sleep(wait_seconds)

    logger.error(
        "call_llm %d회 모두 실패: %s: %s",
        max_retries, type(last_error).__name__, last_error
    )
    raise RuntimeError(
        f"LLM 호출이 {max_retries}회 모두 실패했습니다: "
        f"{type(last_error).__name__}: {last_error}"
    ) from last_error
