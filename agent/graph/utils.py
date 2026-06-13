import os
import json
from openai import OpenAI


def get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_llm(system_prompt: str, user_content: str) -> dict:
    """LLM 호출 후 JSON 파싱하여 반환"""
    client = get_client()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0
    )
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())
