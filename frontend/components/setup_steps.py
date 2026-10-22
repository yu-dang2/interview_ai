"""면접 환경설정(1단계) · 문서 업로드(2단계) · 웹캠 허용(3단계) 화면이 같이 쓰는 단계 표시와 카드 스타일.

두 화면의 간격·글자 크기가 어긋나지 않게 여기 한 곳에서만 정한다.
제목은 h 태그 대신 div 를 쓴다 (Streamlit 이 h 태그에 기본 스타일과 앵커 링크를 붙인다).
카드 안에 Streamlit 위젯(입력칸·업로드·체크박스)이 들어가야 해서, 카드는
st.container(key="..._card") 로 만들고 그 key 클래스에 카드 모양을 입힌다.
"""

SETUP_CSS = """<style>
[data-testid="stMainBlockContainer"] { padding: 36px 40px 80px !important; max-width: 1060px !important;
    word-break: keep-all !important; overflow-wrap: break-word !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stHorizontalBlock"] { gap: 16px; }

.su-steps { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 26px; font-size: 14px; font-weight: 700; }
.su-steps .s { display: flex; align-items: center; gap: 8px; color: #9ca3af; }
.su-steps .s .n { width: 26px; height: 26px; border-radius: 8px; display: flex; align-items: center;
    justify-content: center; font-size: 12px; font-weight: 800; background: #eef0f4; color: #9ca3af; }
.su-steps .s.on { color: #111827; }
.su-steps .s.on .n { background: #3b6def; color: #fff; }
.su-steps .s.done { color: #4b5563; }
.su-steps .s.done .n { background: #eef3ff; color: #3b6def; font-size: 14px; }
.su-steps .bar { flex: 0 0 48px; height: 2px; background: #e5e7eb; border-radius: 2px; }
.su-steps .bar.done { background: #c7d4fb; }

.su-head { margin-bottom: 0; }
/* Streamlit 마크다운은 아래 여백이 -16px 이라, 제목 블록과 카드 안 마크다운은 0 으로 되돌리고 간격은 각 요소의 margin 으로 준다. */
[data-testid="stMarkdownContainer"]:has(.su-head),
[class*="st-key-"][class*="_card"] [data-testid="stMarkdownContainer"] {
    margin-bottom: 0 !important; }
[data-testid="stElementContainer"]:has(.su-head) { margin-bottom: 22px !important; }
.su-head .t { font-size: 26px; font-weight: 800; letter-spacing: -.02em; color: #111827; margin: 0 0 6px; }
.su-head .sub { font-size: 14px; color: #6b7280; }

[class*="st-key-"][class*="_card"] { background: #fff !important; border: 1px solid #e9ecf2 !important;
    border-radius: 18px !important; padding: 26px 28px !important; margin-bottom: 16px !important;
    box-sizing: border-box !important; }
.su-sh { display: flex; gap: 10px; align-items: center; font-size: 19px; font-weight: 700; color: #111827; margin: 0 0 4px; }
.su-sh .n { font-size: 12px; color: #3b6def; background: #eef3ff; border-radius: 7px; padding: 3px 8px; font-weight: 800; }
.su-sd { margin: 0 0 18px; color: #6b7280; font-size: 13.5px; }

.st-key-next_area { margin-top: 6px !important; }
.st-key-next_area [data-testid="stColumn"]:last-child { display: flex !important; justify-content: flex-end !important; }
.st-key-next_area [data-testid="stColumn"]:last-child [data-testid="stVerticalBlock"] { align-items: flex-end !important; }
.st-key-next_area [data-testid="stColumn"]:last-child [data-testid="stElementContainer"] { width: auto !important; }
.st-key-next_area [data-testid="stBaseButton-primary"] { font-size: 15px !important; padding: 12px 26px !important;
    border-radius: 12px !important; white-space: nowrap !important; width: auto !important; min-height: 0 !important; }
.su-foot-hint { font-size: 13px; color: #6b7280; }

@media (max-width: 640px) {
    [data-testid="stMainBlockContainer"] { padding: 24px 16px 60px !important; }
    [class*="st-key-"][class*="_card"] { padding: 20px 18px !important; }
}
</style>"""


_STEP_LABELS = ["기본 정보", "문서 업로드", "면접 방식"]


def steps_html(current: int) -> str:
    """current: 1(기본 정보) · 2(문서 업로드) · 3(면접 방식 = 웹캠 허용)."""
    parts = []
    for i, label in enumerate(_STEP_LABELS, start=1):
        if i < current:
            parts.append(f'<span class="s done"><span class="n"><i class="ph-bold ph-check"></i></span>{label}</span>')
        else:
            parts.append(f'<span class="s{" on" if i == current else ""}"><span class="n">{i:02d}</span>{label}</span>')
        if i < len(_STEP_LABELS):
            parts.append(f'<span class="bar{" done" if i < current else ""}"></span>')
    return f'<div class="su-steps">{"".join(parts)}</div>'
