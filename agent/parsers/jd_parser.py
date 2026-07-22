"""
JD 파서 — 채용 공고 입력 방식 3가지 + 에러 핸들링/안내 메시지
1. 텍스트 직접 입력 (parse_jd_from_text)
2. 이미지 업로드 (parse_jd_from_image)
3. URL 크롤링 (parse_jd_from_url)  ※ async

- 파싱 실패/부분 성공 시 상태와 안내 메시지를 함께 반환 (JDParseResult)
- 반환 타입: JDParseResult (result.data 로 파싱 결과 dict 접근)
- LLM: OpenAI gpt-5-mini

사용법:
    from agent.parsers.jd_parser import parse_jd_from_text, parse_jd_from_image, parse_jd_from_url

    result = await parse_jd_from_text("채용 공고 텍스트...")  # async
    print(result.status)   # "success" / "partial" / "failed"
    print(result.data)     # 파싱된 dict

    # URL은 async 함수라 await 필요
    result = await parse_jd_from_url("https://www.wanted.co.kr/wd/328573")
"""

import os
import json
import base64
import asyncio
from openai import AsyncOpenAI
from agent.parsers.jd_parser_prompt import JD_PARSER_SYSTEM_PROMPT, IMAGE_TO_TEXT_PROMPT


def get_client():
    """OpenAI 클라이언트 생성"""
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =============================================================
# 파싱 결과 컨테이너 (성공/부분성공/실패 + 안내 메시지)
# =============================================================
class JDParseResult:
    """JD 파싱 결과. 상태·안내 메시지·추가 제안을 함께 담는다."""

    def __init__(self, data: dict = None, status: str = "success", message: str = "", suggestions: list = None):
        self.data = data or {}
        self.status = status                    # "success" / "partial" / "failed"
        self.message = message                  # 사용자에게 보여줄 안내
        self.suggestions = suggestions or []    # 추가 행동 제안

    def to_dict(self):
        result = {"status": self.status, "data": self.data}
        if self.message:
            result["message"] = self.message
        if self.suggestions:
            result["suggestions"] = self.suggestions
        return result

    def __repr__(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def _validate_parsed_jd(data: dict, input_method: str) -> JDParseResult:
    """파싱 결과를 검증하고, 부족한 부분이 있으면 안내 메시지를 생성한다."""
    required_fields = ["job_title", "company", "required_skills", "main_tasks"]
    missing_fields = []
    empty_fields = []

    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
        elif isinstance(data[field], list) and len(data[field]) == 0:
            empty_fields.append(field)
        elif isinstance(data[field], str) and (data[field] == "" or data[field] == "명시되지 않음"):
            empty_fields.append(field)

    # 완전 실패 (필수 필드 3개 이상 누락)
    if len(missing_fields) >= 3:
        return JDParseResult(
            data=data, status="failed",
            message="채용 공고를 파싱하지 못했습니다.",
            suggestions=_get_fallback_suggestions(input_method),
        )

    # 부분 성공 (일부 항목만 비어 있음)
    if empty_fields:
        field_names_kr = {
            "job_title": "직무명", "company": "회사명",
            "required_skills": "자격요건(필수 기술)", "preferred_skills": "우대사항",
            "main_tasks": "주요 업무", "experience_years": "경력 요건",
            "interview_keywords": "면접 키워드",
        }
        empty_kr = [field_names_kr.get(f, f) for f in empty_fields]
        suggestions = [
            f"다음 항목을 텍스트로 직접 입력해주시면 더 정확한 면접 질문을 생성할 수 있습니다: {', '.join(empty_kr)}"
        ]
        if input_method == "image":
            suggestions.append("이미지에서 해당 부분이 잘렸을 수 있습니다. 전체 채용 공고가 보이도록 다시 캡처해주세요.")
        elif input_method == "url":
            suggestions.append("'상세 정보 더 보기' 등 숨겨진 내용이 있을 수 있습니다. 해당 부분을 텍스트로 복사해서 보내주세요.")

        return JDParseResult(
            data=data, status="partial",
            message=f"채용 공고를 파싱했지만, 일부 항목({', '.join(empty_kr)})을 찾지 못했습니다.",
            suggestions=suggestions,
        )

    # 완전 성공
    return JDParseResult(data=data, status="success", message="채용 공고가 성공적으로 파싱되었습니다.")


def _get_fallback_suggestions(input_method: str) -> list:
    """입력 방식에 따른 대체 방법 안내."""
    if input_method == "url":
        return [
            "해당 사이트의 채용 공고를 자동으로 가져오지 못했습니다.",
            "다음 방법 중 하나를 시도해주세요:",
            "1. 채용 공고 페이지를 스크린샷으로 찍어서 이미지로 업로드",
            "2. 채용 공고의 주요업무/자격요건/우대사항을 복사해서 텍스트로 붙여넣기",
        ]
    elif input_method == "image":
        return [
            "이미지에서 채용 공고 내용을 읽지 못했습니다.",
            "다음 방법 중 하나를 시도해주세요:",
            "1. 이미지를 더 선명하게 다시 캡처 (글자가 잘 보이도록)",
            "2. 채용 공고 텍스트를 직접 입력",
        ]
    else:
        return [
            "입력하신 텍스트에서 채용 공고 정보를 추출하지 못했습니다.",
            "다음 항목이 포함되어 있는지 확인해주세요:",
            "• 주요업무 (어떤 일을 하는지)",
            "• 자격요건 (필수 기술, 경력 요건)",
            "• 우대사항 (있는 경우)",
        ]


def _extract_json(text: str) -> dict:
    """LLM 응답에서 ```json 마크다운을 제거하고 JSON으로 파싱한다."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


async def _call_openai(system_prompt: str, user_content) -> str:
    """
    OpenAI 호출. user_content가 문자열이면 텍스트, list면 이미지 포함 요청.
    (Vision 이미지 파트: {"type": "image_base64", "mime_type": ..., "data": ...})
    """
    client = get_client()

    if isinstance(user_content, str):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    else:  # list — 이미지 + 텍스트 파트
        parts = []
        for item in user_content:
            if item.get("type") == "text":
                parts.append({"type": "text", "text": item["text"]})
            elif item.get("type") == "image_base64":
                parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{item['mime_type']};base64,{item['data']}"},
                })
        messages = [{"role": "user", "content": parts}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

    response = await client.chat.completions.create(
        model="gpt-5-mini",   # gpt-4o → gpt-5-mini
        messages=messages,
        # ※ temperature 미지정: gpt-5 계열은 temperature=0 미지원(기본값 1만 허용)
    )
    return response.choices[0].message.content.strip()


# =============================================================
# 방법 1: 텍스트 직접 입력
# =============================================================
async def parse_jd_from_text(jd_text: str) -> JDParseResult:
    """채용 공고 텍스트를 받아서 JSON으로 파싱한다."""
    try:
        if not jd_text or len(jd_text.strip()) < 20:
            return JDParseResult(
                status="failed", message="입력된 텍스트가 너무 짧습니다.",
                suggestions=["채용 공고의 주요업무, 자격요건, 우대사항이 포함된 전체 텍스트를 입력해주세요."],
            )
        result_text = await _call_openai(JD_PARSER_SYSTEM_PROMPT, jd_text)
        data = _extract_json(result_text)
        return _validate_parsed_jd(data, "text")

    except json.JSONDecodeError:
        return JDParseResult(status="failed", message="파싱 결과를 JSON으로 변환하지 못했습니다.",
                             suggestions=_get_fallback_suggestions("text"))
    except Exception as e:
        return JDParseResult(status="failed", message=f"파싱 중 오류: {str(e)}",
                             suggestions=_get_fallback_suggestions("text"))


# =============================================================
# 방법 2: 이미지 업로드 → Vision으로 텍스트 변환 → 파싱
# =============================================================
async def parse_jd_from_image(image_path: str) -> JDParseResult:
    """채용 공고 이미지를 텍스트로 변환 후 JSON으로 파싱한다."""
    try:
        if not os.path.exists(image_path):
            return JDParseResult(status="failed", message=f"이미지 파일을 찾을 수 없습니다: {image_path}",
                                 suggestions=["파일 경로를 확인해주세요."])

        file_size = os.path.getsize(image_path) / (1024 * 1024)
        if file_size > 20:
            return JDParseResult(status="failed",
                                 message=f"이미지가 너무 큽니다 ({file_size:.1f}MB). 20MB 이하로 줄여주세요.")

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/png")

        # Step 1: 이미지 → 텍스트
        user_content = [
            {"type": "image_base64", "mime_type": mime_type, "data": image_data},
            {"type": "text", "text": IMAGE_TO_TEXT_PROMPT},
        ]
        extracted_text = await _call_openai("", user_content)

        if not extracted_text or len(extracted_text.strip()) < 20:
            return JDParseResult(status="failed", message="이미지에서 텍스트를 추출하지 못했습니다.",
                                 suggestions=_get_fallback_suggestions("image"))

        print(f"[이미지→텍스트 완료] {len(extracted_text)}자 추출")

        # Step 2: 텍스트 → JSON
        data = _extract_json(await _call_openai(JD_PARSER_SYSTEM_PROMPT, extracted_text))
        return _validate_parsed_jd(data, "image")

    except json.JSONDecodeError:
        return JDParseResult(status="failed", message="이미지에서 추출한 텍스트를 파싱하지 못했습니다.",
                             suggestions=_get_fallback_suggestions("image"))
    except Exception as e:
        return JDParseResult(status="failed", message=f"이미지 파싱 중 오류: {str(e)}",
                             suggestions=_get_fallback_suggestions("image"))


# =============================================================
# 방법 3: URL → Playwright(async)로 크롤링 → 파싱
# =============================================================
async def parse_jd_from_url(url: str) -> JDParseResult:
    """
    채용 공고 URL을 크롤링 후 JSON으로 파싱한다. (async)

    ※ 사전 설치: pip install playwright && playwright install chromium
    """
    try:
        jd_text = await _crawl_jd_page(url)

        if not jd_text or len(jd_text.strip()) < 20:
            return JDParseResult(status="failed", message="해당 URL에서 채용 공고 내용을 가져오지 못했습니다.",
                                 suggestions=_get_fallback_suggestions("url"))

        print(f"[크롤링 완료] {len(jd_text)}자 추출")

        data = _extract_json(await _call_openai(JD_PARSER_SYSTEM_PROMPT, jd_text))
        return _validate_parsed_jd(data, "url")

    except ImportError:
        return JDParseResult(
            status="failed", message="URL 크롤링에 필요한 패키지(playwright)가 설치되지 않았습니다.",
            suggestions=[
                "다음 명령어로 설치해주세요:",
                "  pip install playwright",
                "  playwright install chromium",
                "",
                "또는 다른 방법을 사용해주세요:",
                "1. 채용 공고를 스크린샷으로 찍어서 이미지로 업로드",
                "2. 채용 공고 텍스트를 복사해서 직접 붙여넣기",
            ],
        )
    except json.JSONDecodeError:
        return JDParseResult(status="failed", message="크롤링한 텍스트를 파싱하지 못했습니다.",
                             suggestions=_get_fallback_suggestions("url"))
    except Exception as e:
        error_msg = str(e)
        if "Timeout" in error_msg or "timeout" in error_msg:
            msg = "페이지 로딩 시간이 초과되었습니다."
        elif "ERR_NAME_NOT_RESOLVED" in error_msg:
            msg = "해당 URL에 접속할 수 없습니다. URL을 확인해주세요."
        else:
            msg = f"크롤링 중 오류: {error_msg}"
        return JDParseResult(status="failed", message=msg, suggestions=_get_fallback_suggestions("url"))


async def _crawl_jd_page(url: str) -> str:
    """Playwright(async)로 채용 공고 페이지 텍스트를 크롤링한다."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(url, wait_until="networkidle", timeout=30000)

        await _click_more_buttons(page, url)
        jd_text = await _extract_jd_text(page, url)

        await browser.close()

    return jd_text


async def _click_more_buttons(page, url: str):
    """사이트별 '상세 정보 더 보기' 버튼을 클릭한다."""
    try:
        if "wanted.co.kr" in url:
            more_btn = page.locator("button:has-text('더 보기'), button:has-text('더보기')")
            if await more_btn.count() > 0:
                await more_btn.first.click()
                await asyncio.sleep(1)

        elif "jobkorea.co.kr" in url:
            more_btn = page.locator(".devMoreView, .tplBtn, button:has-text('더보기')")
            if await more_btn.count() > 0:
                await more_btn.first.click()
                await asyncio.sleep(1)

        elif "saramin.co.kr" in url:
            more_btn = page.locator(".btn_more_info, button:has-text('더보기')")
            if await more_btn.count() > 0:
                await more_btn.first.click()
                await asyncio.sleep(1)

        elif "programmers.co.kr" in url:
            await asyncio.sleep(1)

    except Exception as e:
        print(f"[경고] 더보기 버튼 클릭 실패 (무시하고 계속): {e}")


async def _extract_jd_text(page, url: str) -> str:
    """사이트별 채용 공고 본문에서 텍스트를 추출한다."""
    selectors = {
        "wanted.co.kr": "section.JobDescription_JobDescription",
        "jobkorea.co.kr": ".tbRow, .artReadDetail",
        "saramin.co.kr": ".jv_cont, .wrap_jv_cont",
        "programmers.co.kr": ".job-content",
    }

    for domain, selector in selectors.items():
        if domain in url:
            element = page.locator(selector)
            if await element.count() > 0:
                return await element.first.inner_text()

    return await page.locator("body").inner_text()


# =============================================================
# CLI 테스트
# =============================================================
def _print_result(result: JDParseResult):
    print()
    print("=" * 50)
    if result.status == "success":
        print("<파싱 성공>")
    elif result.status == "partial":
        print("<부분 파싱 (일부 항목 누락)>")
    else:
        print("<파싱 실패>")
    print("=" * 50)

    if result.message:
        print(f"\n[안내] {result.message}")

    if result.suggestions:
        print()
        for s in result.suggestions:
            print(f"  {s}")

    if result.data:
        print(f"\n[파싱 결과]")
        print(json.dumps(result.data, ensure_ascii=False, indent=2))
    print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법:")
        print("  python jd_parser.py text          → 텍스트 입력 테스트")
        print("  python jd_parser.py image <경로>  → 이미지 파싱 테스트")
        print("  python jd_parser.py url <URL>     → URL 크롤링 테스트")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "text":
        print("채용 공고 텍스트를 입력하세요 (Windows: Ctrl+Z→Enter / Mac: Ctrl+D):")
        jd_text = sys.stdin.read()
        _print_result(asyncio.run(parse_jd_from_text(jd_text)))

    elif mode == "image":
        _print_result(asyncio.run(parse_jd_from_image(sys.argv[2])))

    elif mode == "url":
        result = asyncio.run(parse_jd_from_url(sys.argv[2]))   # async 함수
        _print_result(result)
