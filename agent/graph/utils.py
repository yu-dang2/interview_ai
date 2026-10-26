import os
import json
import asyncio
import logging

from openai import AsyncOpenAI, OpenAIError

logger = logging.getLogger(__name__)

RAPPORT_TYPE = "라포"


def is_rapport_question(question: dict) -> bool:
    return (question.get("type") or "").strip() == RAPPORT_TYPE


def get_client():
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# 노드별 모델·reasoning 강도: LLM_MODEL_<STAGE> / REASONING_EFFORT_<STAGE> 환경변수 > STAGE_DEFAULTS.
# 전역 LLM_MODEL 을 설정하면 STAGE_DEFAULTS 의 모델 지정이 모두 무시된다.
REASONING_EFFORTS = ("minimal", "low", "medium", "high")

DEFAULT_MODEL = "gpt-5-mini"

STAGE_DEFAULTS = {
    "resume_parser": {"model": "gpt-4o-mini"},
    "jd_resume_matcher": {"reasoning_effort": "low"},
    "answer_evaluator": {"reasoning_effort": "low"},
    "follow_up_generator": {"model": "gpt-4o-mini"},
}

# gpt-4o 계열은 reasoning_effort 를 거부한다.
REASONING_MODEL_PREFIXES = ("gpt-5", "o1", "o3", "o4")

_effort_warned = set()


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
        logger.warning(
            "%s 값이 올바르지 않아 무시합니다: %r (허용: %s)",
            key, value, ", ".join(REASONING_EFFORTS),
        )
    return STAGE_DEFAULTS.get(stage, {}).get("reasoning_effort")


def _clean_json_text(text: str) -> str:
    """LLM 응답에서 마크다운 코드펜스(```json ... ```)와 앞뒤 공백 제거"""
    text = (text or "").strip()
    if text.startswith("```"):
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

    API 오류와 JSON 파싱 실패는 지수 백오프(1초 → 2초 → 4초)로 재시도하고,
    max_retries회 모두 실패하면 RuntimeError를 발생시킨다.
    stage 는 호출한 노드 이름으로, 노드별 모델·reasoning 강도를 고르는 데 쓴다.
    """
    last_error = None

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

            wait_seconds = 2 ** (attempt - 1)
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
