import streamlit as st
from utils.paths import resource
from utils.state import restore_access_token_nonblocking

st.set_page_config(
    page_title="intro",
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
}
[data-testid="stMain"],
[data-testid="stAppViewContainer"] { background: #f8fafc !important; }

/* 콘텐츠 영역 white */
[data-testid="stMainBlockContainer"] { background: white !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] > div,
[data-testid="stVerticalBlock"],
[data-testid="stMainBlockContainer"] { overflow: visible !important; }

/* CTA 버튼 */
.st-key-cta_start_btn button {
    height: 52px !important;
    border-radius: 8px !important;
}
.st-key-cta_start_btn button p {
    font-size: 15px !important;
}
</style>
""", unsafe_allow_html=True)


# ── 아이콘 SVG 로드 ──────────────────────────────────────────────────
ICONS = {
    "file":    resource("assets/icons/Group 15.svg").read_text(encoding="utf-8"),
    "mic":     resource("assets/icons/Mic.svg").read_text(encoding="utf-8"),
    "chart":   resource("assets/icons/Group 19.svg").read_text(encoding="utf-8"),
    "refresh": resource("assets/icons/Refresh_2.svg").read_text(encoding="utf-8"),
}


# ── 데이터 ───────────────────────────────────────────────────────────
STATS = [
    {"num": "3,200+",  "label": "이력서 분석"},
    {"num": "15,000+", "label": "모의 면접"},
    {"num": "89%",     "label": "합격률 향상"},
    {"num": "4.8★",    "label": "사용자 평점"},
]

FEATURES = [
    {
        "icon": "file",    "icon_bg": "#eef3ff", "dot": "#3b6def",
        "title": "이력서 AI 분석",
        "items": ["JD 키워드 자동 매칭", "섹션별 개선 제안 생성", "점수화 및 등급 산정"],
    },
    {
        "icon": "mic",     "icon_bg": "#f0fdf4", "dot": "#16a34a",
        "title": "AI 면접 코칭",
        "items": ["LangGraph 꼬리질문 엔진", "페르소나별 면접관 선택", "웹캠 시선 처리 분석"],
    },
    {
        "icon": "chart",   "icon_bg": "#f5f3ff", "dot": "#7c3aed",
        "title": "상세 결과 분석",
        "items": ["레이더 차트 역량 시각화", "소프트 스킬 전체 평균 비교"],
    },
    {
        "icon": "refresh", "icon_bg": "#fffbeb", "dot": "#d97706",
        "title": "반복 개선 사이클",
        "items": ["히스토리 점수 추이 관리", "이력서 버전 관리", "면접 히스토리 아카이브"],
    },
]


# ── 1. 네비게이션 바 ─────────────────────────────────────────────────
_nav_right = "" if logged_in else (
    '<a class="btn-ghost"  href="/%ED%9A%8C%EC%9B%90%EA%B0%80%EC%9E%85" target="_self">회원가입</a>'
    '<a class="btn-filled" href="/%EB%A1%9C%EA%B7%B8%EC%9D%B8"           target="_self">로그인</a>'
)
st.markdown(
    f'<nav class="navbar">'
    f'<span class="navbar-brand">intro</span>'
    f'<div class="navbar-right">{_nav_right}</div>'
    f'</nav>',
    unsafe_allow_html=True,
)


# ── 2. 히어로 ────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-blob hero-blob-1"></div>
    <div class="hero-blob hero-blob-2"></div>
    <div class="hero-inner">
        <div class="hero-badge">AI 기반 면접 코치 서비스 — Beta</div>
        <div class="hero-title">이력서 → 면접 → 합격</div>
        <p class="hero-subtitle">AI가 당신의 취업을 완성합니다</p>
        <p class="hero-desc">
            이력서 AI 분석부터 맞춤형 AI 면접 코칭, 상세 결과 리포트까지<br>
            취업 준비의 모든 과정을 하나의 서비스로 경험하세요.
        </p>
    </div>
</div>
""", unsafe_allow_html=True)


# ── 3. CTA 버튼 ──────────────────────────────────────────────────────
_, center, _ = st.columns([2, 1, 2])
with center:
    if st.button("면접 시작하기", type="primary", use_container_width=True, key="cta_start_btn"):
        if logged_in:
            st.switch_page("pages/03_면접_환경설정.py")
        else:
            st.switch_page("pages/01_로그인.py")


# ── 4. 통계 ──────────────────────────────────────────────────────────
stat_items = "".join(
    f'<div class="stat-item">'
    f'  <div class="stat-num">{s["num"]}</div>'
    f'  <div class="stat-label">{s["label"]}</div>'
    f'</div>'
    for s in STATS
)
st.markdown(f'<div class="stats-row">{stat_items}</div>', unsafe_allow_html=True)


# ── 5. 기능 카드 ─────────────────────────────────────────────────────
def make_feat_card(f: dict) -> str:
    items_html = "".join(
        f'<div class="feat-item">'
        f'  <div class="feat-dot" style="background:{f["dot"]};"></div>'
        f'  {item}'
        f'</div>'
        for item in f["items"]
    )
    return (
        f'<div class="feat-card">'
        f'  <div class="feat-icon-box" style="background:{f["icon_bg"]};">'
        f'    {ICONS[f["icon"]]}'
        f'  </div>'
        f'  <div class="feat-title">{f["title"]}</div>'
        f'  {items_html}'
        f'</div>'
    )

cards_html = "".join(make_feat_card(f) for f in FEATURES)

st.markdown(
    f'<div class="features-section">'
    f'  <p class="features-title">하나의 서비스로 완성하는 취업 준비</p>'
    f'  <div class="features-grid">{cards_html}</div>'
    f'</div>',
    unsafe_allow_html=True,
)
