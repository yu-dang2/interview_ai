import streamlit as st
from utils.brand import FAVICON, logo_img
from utils.paths import resource
from utils.state import restore_access_token_nonblocking

st.set_page_config(
    page_title="사용법 | intro",
    page_icon=FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

logged_in = bool(restore_access_token_nonblocking())

# ── 스타일 ───────────────────────────────────────────────────────────
css = resource("styles/global.css").read_text(encoding="utf-8")
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stExpandSidebarButton"] { display: none !important; }

.main .block-container,
[data-testid="stMainBlockContainer"] {
    padding: 0 !important;
    max-width: 100% !important;
    width: 100% !important;
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
}
[data-testid="stMain"],
[data-testid="stAppViewContainer"] { background: #f8fafc !important; }
[data-testid="stMainBlockContainer"] { background: white !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }

.usage-hero {
    background: white;
    padding: 120px 40px 56px;
    text-align: center;
}

.usage-hero-badge { font-size: 12px !important; font-weight: 700; letter-spacing: 2px; color: var(--blue); margin-bottom: 12px; }
.usage-hero-title { font-size: 34px !important; font-weight: 800; color: var(--gray-900); margin: 0 0 12px; }
.usage-hero-desc  { font-size: 15px !important; color: var(--gray-500); }

.usage-steps { background: var(--bg); padding: 56px 40px 72px; }
.usage-step {
    max-width: 760px;
    margin: 0 auto 20px;
    background: white;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 28px 32px;
    display: flex;
    gap: 24px;
    align-items: flex-start;
}
.usage-step-num {
    font-size: 22px;
    font-weight: 900;
    color: white;
    background: var(--blue);
    width: 44px; height: 44px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.usage-step-title { font-size: 17px !important; font-weight: 700; color: var(--gray-900); margin: 0 0 6px; }
.usage-step-desc  { font-size: 13px !important; color: var(--gray-500); line-height: 1.8; margin: 0 0 10px; }
.usage-step-tags  { display: flex; gap: 8px; flex-wrap: wrap; }
.usage-tag {
    font-size: 11px; font-weight: 600; color: var(--blue);
    background: var(--blue-soft); padding: 4px 10px; border-radius: 20px;
}

.st-key-usage_cta_row { padding: 64px 40px 80px; text-align: center; background: white; }
.st-key-usage_cta_row button { height: 52px !important; border-radius: 8px !important; }
.st-key-usage_cta_row button p { font-size: 15px !important; }
</style>
""", unsafe_allow_html=True)

# ── 네비게이션 ──────────────────────────────────────────────────────
_auth_links = "" if logged_in else (
    '<a class="btn-ghost"  href="/%ED%9A%8C%EC%9B%90%EA%B0%80%EC%9E%85" target="_self">회원가입</a>'
    '<a class="btn-filled" href="/%EB%A1%9C%EA%B7%B8%EC%9D%B8"           target="_self">로그인</a>'
)
st.markdown(
    f'<nav class="navbar">'
    f'<a class="navbar-brand" href="/" target="_self" aria-label="intro 홈">{logo_img(25)}</a>'
    f'<div class="navbar-right">{_auth_links}</div>'
    f'</nav>',
    unsafe_allow_html=True,
)

# ── 히어로 ──────────────────────────────────────────────────────────
st.markdown("""
<div class="usage-hero">
    <p class="usage-hero-badge">HOW TO USE</p>
    <p class="usage-hero-title">3단계면 준비 끝, 이렇게 시작하세요</p>
    <p class="usage-hero-desc">면접관 선택부터 결과 리포트 확인까지, intro 사용법을 한눈에 안내해드려요.</p>
</div>
""", unsafe_allow_html=True)

# ── 단계별 안내 ─────────────────────────────────────────────────────
STEPS = [
    {
        "num": "1", "title": "면접관 선택 · 이력서와 채용공고 업로드",
        "desc": "기술 리드 · 인사 담당자 · 임원 면접관 중 원하는 스타일을 고르고, PDF, DOCX, HWPX 형식의 이력서와 채용공고(JD)를 업로드하면 AI가 핵심 키워드와 요구 역량을 자동으로 분석해요.",
        "tags": ["페르소나 3종", "PDF / DOCX / HWPX"],
    },
    {
        "num": "2", "title": "실전 같은 AI 모의 면접",
        "desc": "웹캠 사용 여부를 고른 뒤, 답변에 따라 꼬리질문이 이어지는 AI 면접을 진행해요. 웹캠 없이도 음성·텍스트로 진행할 수 있어요.",
        "tags": ["꼬리질문", "웹캠 선택 가능"],
    },
    {
        "num": "3", "title": "결과 리포트로 복기하기",
        "desc": "역량 레이더 차트와 질문별 피드백 보고서를 확인하고, 이력서 최적화 제안까지 받아 다음 면접을 준비해요.",
        "tags": ["역량 리포트", "이력서 최적화"],
    },
]
# f-string {} 안에 백슬래시(\')를 쓰면 Python 3.11 이하에서 SyntaxError — 태그 HTML은 따로 만든다.
def _tags_html(tags):
    return "".join(f'<span class="usage-tag">{t}</span>' for t in tags)


steps_html = "".join(
    f'<div class="usage-step">'
    f'  <div class="usage-step-num">{s["num"]}</div>'
    f'  <div>'
    f'    <p class="usage-step-title">{s["title"]}</p>'
    f'    <p class="usage-step-desc">{s["desc"]}</p>'
    f'    <div class="usage-step-tags">{_tags_html(s["tags"])}</div>'
    f'  </div>'
    f'</div>'
    for s in STEPS
)
st.markdown(f'<div class="usage-steps">{steps_html}</div>', unsafe_allow_html=True)

# ── CTA ─────────────────────────────────────────────────────────────
with st.container(key="usage_cta_row"):
    st.markdown('<p style="font-size:14px;color:#6b7280;margin-bottom:20px;text-align:center;">이제 직접 체험해볼 차례예요</p>',
                unsafe_allow_html=True)
    _, center, _ = st.columns([2, 1, 2])
    with center:
        if st.button("면접 시작하기", type="primary", use_container_width=True, key="usage_cta_btn"):
            if logged_in:
                st.switch_page("pages/03_면접_환경설정.py")
            else:
                st.switch_page("pages/01_로그인.py")
