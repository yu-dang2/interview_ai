"""
JD 파서 v2 — 에러 핸들링 + 사용자 안내 메시지 포함
- 파싱 실패 시 다른 방법으로 안내
- 일부만 파싱된 경우 부족한 부분을 텍스트로 보내달라고 안내
- OpenAI(유료) 또는 Google Gemini(무료) 선택 가능

무료 테스트:
1. https://aistudio.google.com/apikey 에서 API 키 발급
2. $env:GEMINI_API_KEY = "your-key"  (Windows PowerShell)
3. python jd_parser_free.py text
"""

import os
import json
import base64
import requests

from agent.parsers.jd_parser_prompt import JD_PARSER_SYSTEM_PROMPT, IMAGE_TO_TEXT_PROMPT


# =============================================================
# 파싱 결과 검증 및 사용자 안내 메시지
# =============================================================
class JDParseResult:
    """JD 파싱 결과를 담는 클래스. 성공/부분성공/실패 상태와 안내 메시지를 포함합니다."""

    def __init__(self, data: dict = None, status: str = "success", message: str = "", suggestions: list = None):
        self.data = data or {}
        self.status = status        # "success", "partial", "failed"
        self.message = message      # 사용자에게 보여줄 안내 메시지
        self.suggestions = suggestions or []  # 추가 행동 제안

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
    """파싱 결과를 검증하고, 부족한 부분이 있으면 안내 메시지를 생성합니다."""
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

    # 완전 실패
    if len(missing_fields) >= 3:
        return JDParseResult(
            data=data, status="failed",
            message="채용 공고를 파싱하지 못했습니다.",
            suggestions=_get_fallback_suggestions(input_method)
        )

    # 부분 성공
    if empty_fields:
        field_names_kr = {
            "job_title": "직무명", "company": "회사명",
            "required_skills": "자격요건(필수 기술)", "preferred_skills": "우대사항",
            "main_tasks": "주요 업무", "experience_years": "경력 요건",
            "interview_keywords": "면접 키워드"
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
            suggestions=suggestions
        )

    # 완전 성공
    return JDParseResult(data=data, status="success", message="채용 공고가 성공적으로 파싱되었습니다.")


def _get_fallback_suggestions(input_method: str) -> list:
    """입력 방식에 따른 대체 방법 안내 메시지"""
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


# =============================================================
# LLM 호출
# =============================================================
def call_llm(system_prompt: str, user_content, provider: str = "gemini") -> str:
    if provider == "gemini":
        return _call_gemini(system_prompt, user_content)
    elif provider == "openai":
        return _call_openai(system_prompt, user_content)
    else:
        raise ValueError(f"지원하지 않는 provider: {provider}")


def _call_gemini(system_prompt: str, user_content) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY가 설정되지 않았습니다.\n"
            "1. https://aistudio.google.com/apikey 에서 무료 API 키 발급\n"
            "2. Windows: $env:GEMINI_API_KEY = 'your-key'\n"
            "3. Mac/Linux: export GEMINI_API_KEY=your-key"
        )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    if isinstance(user_content, str):
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_content}]}],
            "generationConfig": {"temperature": 0}
        }
    elif isinstance(user_content, list):
        parts = []
        for item in user_content:
            if item.get("type") == "text":
                parts.append({"text": item["text"]})
            elif item.get("type") == "image_base64":
                parts.append({"inline_data": {"mime_type": item["mime_type"], "data": item["data"]}})
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0}
        }

    response = requests.post(url, json=payload, timeout=60)

    if response.status_code == 429:
        raise Exception("API 요청 한도 초과 (429 에러). 1~2분 기다린 후 다시 시도해주세요.")

    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def _call_openai(system_prompt: str, user_content) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if isinstance(user_content, str):
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
    elif isinstance(user_content, list):
        content_parts = []
        for item in user_content:
            if item.get("type") == "text":
                content_parts.append({"type": "text", "text": item["text"]})
            elif item.get("type") == "image_base64":
                content_parts.append({"type": "image_url", "image_url": {"url": f"data:{item['mime_type']};base64,{item['data']}"}})
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": content_parts}]

    response = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0)
    return response.choices[0].message.content.strip()


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


# =============================================================
# 방법 1: 텍스트 직접 입력
# =============================================================
def parse_jd_from_text(jd_text: str, provider: str = "gemini") -> JDParseResult:
    try:
        if not jd_text or len(jd_text.strip()) < 20:
            return JDParseResult(
                status="failed", message="입력된 텍스트가 너무 짧습니다.",
                suggestions=["채용 공고의 주요업무, 자격요건, 우대사항이 포함된 전체 텍스트를 입력해주세요."]
            )
        result_text = call_llm(JD_PARSER_SYSTEM_PROMPT, jd_text, provider)
        data = _extract_json(result_text)
        return _validate_parsed_jd(data, "text")
    except json.JSONDecodeError:
        return JDParseResult(status="failed", message="파싱 결과를 JSON으로 변환하지 못했습니다.", suggestions=_get_fallback_suggestions("text"))
    except Exception as e:
        return JDParseResult(status="failed", message=f"파싱 중 오류: {str(e)}", suggestions=_get_fallback_suggestions("text"))


# =============================================================
# 방법 2: 이미지 업로드
# =============================================================
def parse_jd_from_image(image_path: str, provider: str = "gemini") -> JDParseResult:
    try:
        if not os.path.exists(image_path):
            return JDParseResult(status="failed", message=f"이미지 파일을 찾을 수 없습니다: {image_path}", suggestions=["파일 경로를 확인해주세요."])

        file_size = os.path.getsize(image_path) / (1024 * 1024)
        if file_size > 20:
            return JDParseResult(status="failed", message=f"이미지가 너무 큽니다 ({file_size:.1f}MB). 20MB 이하로 줄여주세요.")

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/png")

        # Step 1: 이미지 → 텍스트
        user_content = [
            {"type": "image_base64", "mime_type": mime_type, "data": image_data},
            {"type": "text", "text": IMAGE_TO_TEXT_PROMPT}
        ]
        extracted_text = call_llm("", user_content, provider)

        if not extracted_text or len(extracted_text.strip()) < 20:
            return JDParseResult(status="failed", message="이미지에서 텍스트를 추출하지 못했습니다.", suggestions=_get_fallback_suggestions("image"))

        print(f"[이미지→텍스트 완료] {len(extracted_text)}자 추출")

        # Step 2: 텍스트 → JSON
        result_text = call_llm(JD_PARSER_SYSTEM_PROMPT, extracted_text, provider)
        data = _extract_json(result_text)
        result = _validate_parsed_jd(data, "image")
        result.data["_extracted_text"] = extracted_text
        return result

    except json.JSONDecodeError:
        return JDParseResult(status="failed", message="이미지에서 추출한 텍스트를 파싱하지 못했습니다.", suggestions=_get_fallback_suggestions("image"))
    except Exception as e:
        return JDParseResult(status="failed", message=f"이미지 파싱 중 오류: {str(e)}", suggestions=_get_fallback_suggestions("image"))


# =============================================================
# 방법 3: URL 크롤링
# =============================================================
def parse_jd_from_url(url: str, provider: str = "gemini") -> JDParseResult:
    try:
        jd_text = _crawl_jd_page(url)

        if not jd_text or len(jd_text.strip()) < 20:
            return JDParseResult(status="failed", message="해당 URL에서 채용 공고 내용을 가져오지 못했습니다.", suggestions=_get_fallback_suggestions("url"))

        print(f"[크롤링 완료] {len(jd_text)}자 추출")

        result_text = call_llm(JD_PARSER_SYSTEM_PROMPT, jd_text, provider)
        data = _extract_json(result_text)
        result = _validate_parsed_jd(data, "url")
        result.data["_crawled_text"] = jd_text[:500] + "..."
        return result

    except ImportError:
        return JDParseResult(
            status="failed", message="URL 크롤링에 필요한 패키지가 설치되지 않았습니다.",
            suggestions=[
                "다음 명령어로 설치해주세요:",
                "  pip install playwright",
                "  playwright install chromium",
                "",
                "또는 다른 방법을 사용해주세요:",
                "1. 채용 공고를 스크린샷으로 찍어서 이미지로 업로드",
                "2. 채용 공고 텍스트를 복사해서 직접 붙여넣기",
            ]
        )
    except json.JSONDecodeError:
        return JDParseResult(status="failed", message="크롤링한 텍스트를 파싱하지 못했습니다.", suggestions=_get_fallback_suggestions("url"))
    except Exception as e:
        error_msg = str(e)
        if "Timeout" in error_msg or "timeout" in error_msg:
            msg = "페이지 로딩 시간이 초과되었습니다."
        elif "ERR_NAME_NOT_RESOLVED" in error_msg:
            msg = "해당 URL에 접속할 수 없습니다. URL을 확인해주세요."
        else:
            msg = f"크롤링 중 오류: {error_msg}"
        return JDParseResult(status="failed", message=msg, suggestions=_get_fallback_suggestions("url"))


def _crawl_jd_page(url: str) -> str:
    from playwright.sync_api import sync_playwright
    import time

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)

        try:
            if "wanted.co.kr" in url:
                btn = page.locator("button:has-text('더 보기'), button:has-text('더보기')")
                if btn.count() > 0:
                    btn.first.click()
                    time.sleep(1)
            elif "jobkorea.co.kr" in url:
                btn = page.locator(".devMoreView, button:has-text('더보기')")
                if btn.count() > 0:
                    btn.first.click()
                    time.sleep(1)
            elif "saramin.co.kr" in url:
                btn = page.locator(".btn_more_info, button:has-text('더보기')")
                if btn.count() > 0:
                    btn.first.click()
                    time.sleep(1)
        except Exception as e:
            print(f"[경고] 더보기 클릭 실패: {e}")

        selectors = {
            "wanted.co.kr": "section.JobDescription_JobDescription",
            "jobkorea.co.kr": ".tbRow, .artReadDetail",
            "saramin.co.kr": ".jv_cont, .wrap_jv_cont",
            "programmers.co.kr": ".job-content",
        }
        for domain, sel in selectors.items():
            if domain in url:
                el = page.locator(sel)
                if el.count() > 0:
                    text = el.first.inner_text()
                    browser.close()
                    return text

        text = page.locator("body").inner_text()
        browser.close()
        return text


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
        print(f"\n📋 {result.message}")

    if result.suggestions:
        print()
        for s in result.suggestions:
            print(f"  {s}")

    if result.data:
        display_data = {k: v for k, v in result.data.items() if not k.startswith("_")}
        if display_data:
            print(f"\n📄 파싱 결과:")
            print(json.dumps(display_data, ensure_ascii=False, indent=2))
    print()


if __name__ == "__main__":
    import sys

    provider = "gemini"

    print()
    print("=" * 50)
    print("  JD 파서 v2 — 에러 핸들링 포함")
    print(f"  LLM: {provider} (무료)")
    print("=" * 50)

    if len(sys.argv) < 2:
        print()
        print("사용법:")
        print("  python jd_parser_free.py text              → 텍스트 입력")
        print("  python jd_parser_free.py image <경로>      → 이미지 파싱")
        print("  python jd_parser_free.py url <URL>         → URL 크롤링")
        print()
        print("사전 준비:")
        print("  1. https://aistudio.google.com/apikey 에서 API 키 발급 (무료)")
        print("  2. Windows: $env:GEMINI_API_KEY = 'your-key'")
        print("  3. pip install requests")
        print("  4. (URL만) pip install playwright && playwright install chromium")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "text":
        print("\n채용 공고 텍스트를 붙여넣으세요.")
        print("입력 완료 후: Windows → Ctrl+Z → Enter / Mac → Ctrl+D\n")
        jd_text = sys.stdin.read()
        result = parse_jd_from_text(jd_text, provider)
        _print_result(result)

    elif mode == "image":
        if len(sys.argv) < 3:
            print("\n사용법: python jd_parser_free.py image screenshot.png")
            sys.exit(1)
        result = parse_jd_from_image(sys.argv[2], provider)
        _print_result(result)

    elif mode == "url":
        if len(sys.argv) < 3:
            print("\n사용법: python jd_parser_free.py url https://www.wanted.co.kr/wd/...")
            sys.exit(1)
        result = parse_jd_from_url(sys.argv[2], provider)
        _print_result(result)

    else:
        print(f"\n알 수 없는 모드: {mode}")
        print("text, image, url 중 하나를 입력해주세요.")
