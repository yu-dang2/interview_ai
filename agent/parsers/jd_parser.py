"""
JD 파서 — 채용 공고 입력 방식 3가지 지원
1. 텍스트 직접 입력 (parse_jd_from_text)
2. 이미지 업로드 (parse_jd_from_image)
3. URL 크롤링 (parse_jd_from_url)  ※ async

사용법:
    from agent.parsers.jd_parser import parse_jd_from_text, parse_jd_from_image, parse_jd_from_url

    # 방법 1: 텍스트
    result = parse_jd_from_text("채용 공고 텍스트...")

    # 방법 2: 이미지 (파일 경로 또는 base64)
    result = parse_jd_from_image("path/to/screenshot.png")

    # 방법 3: URL (원티드, 잡코리아 등) — async 함수라 await 필요
    result = await parse_jd_from_url("https://www.wanted.co.kr/wd/328573")
"""

import os
import json
import base64
import asyncio
from openai import OpenAI
from agent.parsers.jd_parser_prompt import JD_PARSER_SYSTEM_PROMPT, IMAGE_TO_TEXT_PROMPT


def get_client():
    """OpenAI 클라이언트 생성"""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =============================================================
# 방법 1: 텍스트 직접 입력
# =============================================================
def parse_jd_from_text(jd_text: str) -> dict:
    """
    채용 공고 텍스트를 받아서 JSON으로 파싱합니다.

    Args:
        jd_text: 채용 공고 텍스트 (주요업무 + 자격요건 + 우대사항 포함)

    Returns:
        파싱된 채용 공고 정보 (dict)
    """
    client = get_client()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": JD_PARSER_SYSTEM_PROMPT},
            {"role": "user", "content": jd_text}
        ],
        temperature=0
    )

    result_text = response.choices[0].message.content.strip()

    # ```json 마크다운 제거
    if result_text.startswith("```"):
        result_text = result_text.split("\n", 1)[1]
    if result_text.endswith("```"):
        result_text = result_text.rsplit("```", 1)[0]

    return json.loads(result_text)


# =============================================================
# 방법 2: 이미지 업로드 → GPT-4o Vision으로 텍스트 변환 → 파싱
# =============================================================
def parse_jd_from_image(image_path: str) -> dict:
    """
    채용 공고 이미지를 받아서 텍스트로 변환 후 JSON으로 파싱합니다.
    잡코리아, 사람인 등 이미지 기반 채용 공고에 사용합니다.

    Args:
        image_path: 이미지 파일 경로 (.png, .jpg 등)

    Returns:
        파싱된 채용 공고 정보 (dict)
    """
    client = get_client()

    # 이미지를 base64로 인코딩
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # 확장자로 MIME 타입 결정
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/png")

    # Step 1: 이미지 → 텍스트 변환
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    },
                    {
                        "type": "text",
                        "text": IMAGE_TO_TEXT_PROMPT
                    }
                ]
            }
        ],
        temperature=0
    )

    extracted_text = response.choices[0].message.content.strip()
    print(f"[이미지→텍스트 변환 완료] 추출된 텍스트 길이: {len(extracted_text)}자")

    # Step 2: 추출된 텍스트 → JSON 파싱
    return parse_jd_from_text(extracted_text)


# =============================================================
# 방법 3: URL → Playwright(async)로 크롤링 → 텍스트 추출 → 파싱
# =============================================================
async def parse_jd_from_url(url: str) -> dict:
    """
    채용 공고 URL을 받아서 크롤링 후 JSON으로 파싱합니다. (async)
    원티드, 잡코리아, 사람인, 프로그래머스 등을 지원합니다.

    ※ 사전 설치 필요:
        pip install playwright
        playwright install chromium

    Args:
        url: 채용 공고 URL

    Returns:
        파싱된 채용 공고 정보 (dict)
    """
    # Playwright(async)로 페이지 크롤링
    jd_text = await _crawl_jd_page(url)
    print(f"[크롤링 완료] 추출된 텍스트 길이: {len(jd_text)}자")

    # 추출된 텍스트 → JSON 파싱
    return parse_jd_from_text(jd_text)


async def _crawl_jd_page(url: str) -> str:
    """
    Playwright(async)를 사용해서 채용 공고 페이지의 텍스트를 크롤링합니다.
    JavaScript로 동적 로딩되는 콘텐츠(상세 정보 더 보기 등)도 처리합니다.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 페이지 로드
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # 사이트별 "더 보기" 버튼 클릭 처리
        await _click_more_buttons(page, url)

        # 페이지에서 채용 공고 텍스트 추출
        jd_text = await _extract_jd_text(page, url)

        await browser.close()

    return jd_text


async def _click_more_buttons(page, url: str):
    """사이트별 '상세 정보 더 보기' 버튼을 클릭합니다."""
    try:
        if "wanted.co.kr" in url:
            # 원티드: "상세 정보 더 보기" 버튼
            more_btn = page.locator("button:has-text('더 보기'), button:has-text('더보기')")
            if await more_btn.count() > 0:
                await more_btn.first.click()
                await asyncio.sleep(1)

        elif "jobkorea.co.kr" in url:
            # 잡코리아: "더보기" 또는 "전체보기" 버튼
            more_btn = page.locator(".devMoreView, .tplBtn, button:has-text('더보기')")
            if await more_btn.count() > 0:
                await more_btn.first.click()
                await asyncio.sleep(1)

        elif "saramin.co.kr" in url:
            # 사람인: "더보기" 버튼
            more_btn = page.locator(".btn_more_info, button:has-text('더보기')")
            if await more_btn.count() > 0:
                await more_btn.first.click()
                await asyncio.sleep(1)

        elif "programmers.co.kr" in url:
            # 프로그래머스: 보통 전체 표시
            await asyncio.sleep(1)

    except Exception as e:
        print(f"[경고] 더보기 버튼 클릭 실패 (무시하고 계속): {e}")


async def _extract_jd_text(page, url: str) -> str:
    """사이트별 채용 공고 본문 영역에서 텍스트를 추출합니다."""

    selectors = {
        "wanted.co.kr": "section.JobDescription_JobDescription",
        "jobkorea.co.kr": ".tbRow, .artReadDetail",
        "saramin.co.kr": ".jv_cont, .wrap_jv_cont",
        "programmers.co.kr": ".job-content",
    }

    # 사이트에 맞는 셀렉터 찾기
    for domain, selector in selectors.items():
        if domain in url:
            element = page.locator(selector)
            if await element.count() > 0:
                return await element.first.inner_text()

    # 알 수 없는 사이트면 body 전체에서 추출 (최후의 수단)
    return await page.locator("body").inner_text()


# =============================================================
# 테스트
# =============================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법:")
        print("  python jd_parser.py text    → 텍스트 입력 테스트")
        print("  python jd_parser.py image <경로>  → 이미지 파싱 테스트")
        print("  python jd_parser.py url <URL>     → URL 크롤링 테스트")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "text":
        print("채용 공고 텍스트를 입력하세요 (Ctrl+D로 종료):")
        jd_text = sys.stdin.read()
        result = parse_jd_from_text(jd_text)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif mode == "image":
        image_path = sys.argv[2]
        result = parse_jd_from_image(image_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif mode == "url":
        url = sys.argv[2]
        result = asyncio.run(parse_jd_from_url(url))   # async 함수라 asyncio.run으로 실행
        print(json.dumps(result, ensure_ascii=False, indent=2))
