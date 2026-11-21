"""결과 리포트 · 피드백 보고서 · 이력서 최적화 상단의 파란 '리포트 표지' 카드.

세 페이지가 같은 간격과 글자 크기를 쓰도록 여기 한 곳에서만 스타일을 정한다.
제목은 h 태그 대신 div 를 쓴다 (Streamlit 이 h 태그에 기본 스타일과 앵커 링크를 붙인다).
"""
import html

COVER_CSS = """<style>
.cv-book { background: #2f5bd8; border-radius: 6px 18px 18px 6px; color: #fff; padding: 30px 30px 28px;
    box-shadow: inset 10px 0 0 #2549b6; display: flex; flex-direction: column; min-height: 280px; height: 100%;
    box-sizing: border-box; }
.cv-label { font-size: 12px; font-weight: 700; letter-spacing: .1em; color: #c9d6ff; }
.cv-meta { margin-top: 16px; font-size: 14px; line-height: 1.6; color: #dbe4ff; }
.cv-title { margin: 6px 0 24px; font-size: 34px; font-weight: 800; line-height: 1.25; letter-spacing: -.03em; color: #fff; }
.cv-bottom { margin-top: auto; padding-top: 16px; border-top: 1px solid rgba(255,255,255,.2); }

/* 아래쪽: 점수형 (왼쪽 설명 · 오른쪽 점수와 등급) */
.cv-score { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; }
.cv-score .cap { font-size: 13px; line-height: 1.6; color: #c9d6ff; }
.cv-score .val { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
.cv-score .num { font-size: 52px; font-weight: 800; line-height: 1; letter-spacing: -.04em; color: #fff; }
.cv-score .pill { font-size: 12px; font-weight: 800; background: #fff; padding: 4px 11px; border-radius: 999px; }

/* 아래쪽: 숫자 여러 개형 */
.cv-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.cv-stats .cap { font-size: 12px; color: #c9d6ff; }
.cv-stats .num { margin-top: 4px; font-size: 28px; font-weight: 800; line-height: 1.1; color: #fff; }
</style>"""


def cover_html(label: str, meta: str, title_lines: list[str], bottom: str) -> str:
    """label·meta·title 은 escape 해서 넣고, bottom 은 아래 두 함수가 만든 HTML 을 그대로 넣는다."""
    title = "<br>".join(html.escape(t) for t in title_lines)
    return (
        f'<div class="cv-book"><div class="cv-label">{html.escape(label)}</div>'
        f'<div class="cv-meta">{html.escape(meta)}</div>'
        f'<div class="cv-title">{title}</div>'
        f'<div class="cv-bottom">{bottom}</div></div>'
    )


def score_bottom(caption_lines: list[str], score, badge: str, badge_color: str) -> str:
    cap = "<br>".join(html.escape(c) for c in caption_lines)
    return (
        f'<div class="cv-score"><div class="cap">{cap}</div>'
        f'<div class="val"><span class="num">{html.escape(str(score))}</span>'
        f'<span class="pill" style="color:{badge_color}">{html.escape(str(badge))}</span></div></div>'
    )


def stats_bottom(items: list[tuple[str, object]]) -> str:
    cells = "".join(
        f'<div><div class="cap">{html.escape(label)}</div><div class="num">{html.escape(str(value))}</div></div>'
        for label, value in items
    )
    return f'<div class="cv-stats">{cells}</div>'
