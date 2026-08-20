import os
import json
import asyncio
import logging

from openai import AsyncOpenAI, OpenAIError

logger = logging.getLogger(__name__)

# 자기소개(라포 형성) 질문의 type 값. question_generator 프롬프트가 첫 질문에 부여한다.
# 이 질문은 지원자의 긴장을 풀어주는 것이 목적이라 채점·꼬리질문 대상이 아니다.
INTRO_TYPE = "자기소개"


def is_intro_question(question: dict) -> bool:
    """라포 형성용 자기소개 질문이면 True. (채점·꼬리질문·리포트 집계에서 제외)

    type 은 LLM 이 채우는 값이라 누락되거나 공백이 섞일 수 있어 방어적으로 비교한다.
    인덱스 기반 폴백(첫 질문이면 자기소개로 간주)은 일부러 두지 않는다.
    폴백이 있으면 프롬프트가 type 을 빠뜨려도 조용히 넘어가 회귀를 놓친다.
    """
    return (question.get("type") or "").strip() == INTRO_TYPE


def get_client():
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _clean_json_text(text: str) -> str:
    """LLM 응답에서 마크다운 코드펜스(```json ... ```)와 앞뒤 공백 제거"""
    text = (text or "").strip()
    if text.startswith("```"):
        # 첫 줄(``` 또는 ```json)을 통째로 제거
        text = text.split("\n", 1)[1] if "\n" in text else ""
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


async def call_llm(system_prompt: str, user_content: str, max_retries: int = 3) -> dict:
    """
    LLM 호출 후 JSON 파싱하여 반환.

    API 호출 실패(네트워크/rate limit/타임아웃)와 JSON 파싱 실패를 재시도한다.
    재시도 간격은 지수 백오프(1초 → 2초 → 4초).
    max_retries회 모두 실패하면 RuntimeError를 발생시킨다. (조용히 None을 반환하지 않음)
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            client = get_client()
            response = await client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
            )
            text = _clean_json_text(response.choices[0].message.content)
            return json.loads(text)

        except (OpenAIError, json.JSONDecodeError) as e:
            last_error = e
            if attempt == max_retries:
                break

            wait_seconds = 2 ** (attempt - 1)    # 1초 → 2초 → 4초
            logger.warning(
                "call_llm 실패 (%d/%d회): %s: %s — %d초 후 재시도",
                attempt, max_retries, type(e).__name__, e, wait_seconds
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
