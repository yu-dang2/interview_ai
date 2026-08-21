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

[data-testid="stMainBlockContainer"] {
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
}

/* CTA 버튼 (히어로) */
.st-key-cta_start_btn button {
    height: 52px !important;
    border-radius: 8px !important;
    background: #3b6def !important;
    border: none !important;
    color: white !important;
}
.st-key-cta_start_btn button:hover {
    background: #2563eb !important;
}
.st-key-cta_start_btn button p {
    font-size: 15px !important;
    font-weight: 700 !important;
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
_auth_links = "" if logged_in else (
    '<a class="btn-ghost"  href="/%ED%9A%8C%EC%9B%90%EA%B0%80%EC%9E%85" target="_self">회원가입</a>'
    '<a class="btn-filled" href="/%EB%A1%9C%EA%B7%B8%EC%9D%B8"           target="_self">로그인</a>'
)
_nav_right = (
    '<a class="navbar-link" href="/%EC%82%AC%EC%9A%A9%EB%B2%95" target="_self">사용법</a>'
    f'{_auth_links}'
)
st.markdown(
    f'<nav class="navbar">'
    f'<span class="navbar-brand">intro</span>'
    f'<div class="navbar-right">{_nav_right}</div>'
    f'</nav>',
    unsafe_allow_html=True,
)


# ── 2. 히어로 ────────────────────────────────────────────────────────
st.markdown(
'<div class="hero">'
'<div class="hero-inner">'
'<p class="hero-badge">AI 기반 면접 코치 서비스 — Beta</p>'
'<h1 class="hero-title">이력서 → 면접 → 합격</h1>'
'<p class="hero-subtitle">AI가 당신의 취업을 완성합니다</p>'
'<p class="hero-desc">'
'이력서 AI 분석부터 맞춤형 AI 면접 코칭, 상세 결과 리포트까지<br>'
'취업 준비의 모든 과정을 하나의 서비스로 경험하세요.'
'</p>'
'</div>'
'</div>',
unsafe_allow_html=True)


# ── 3. CTA 버튼 (히어로의 밝은 배경을 이어받는 컨테이너) ─────────────────────
with st.container(key="cta_row"):
    _, center, _ = st.columns([2, 1, 2])
    with center:
        if st.button("면접 시작하기", type="primary", use_container_width=True, key="cta_start_btn"):
            if logged_in:
                st.switch_page("pages/03_면접_환경설정.py")
            else:
                st.switch_page("pages/01_로그인.py")


# ── 4. 기능 카드 ─────────────────────────────────────────────────────
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


# ── 5. 진행 과정 (3단계) ────────────────────────────────────────────────
STEPS = [
    {"num": "01", "title": "문서 업로드", "desc": "이력서와 채용공고(JD)를 업로드하면 AI가 자동으로 분석해요."},
    {"num": "02", "title": "AI 모의 면접", "desc": "면접관 스타일을 고르고, 꼬리질문까지 이어지는 실전형 면접을 진행해요."},
    {"num": "03", "title": "결과 리포트 확인", "desc": "역량 점수와 개선 피드백을 바탕으로 다음 면접을 준비해요."},
]
steps_html = "".join(
    f'<div class="process-step">'
    f'  <div class="process-num">{s["num"]}</div>'
    f'  <div class="process-title">{s["title"]}</div>'
    f'  <div class="process-desc">{s["desc"]}</div>'
    f'</div>'
    for s in STEPS
)
st.markdown(
    f'<div class="process-section">'
    f'  <p class="process-label">HOW IT WORKS</p>'
    f'  <p class="process-title-main">이렇게 3단계로 진행돼요</p>'
    f'  <div class="process-grid">{steps_html}</div>'
    f'</div>',
    unsafe_allow_html=True,
)


# ── 6. FAQ ───────────────────────────────────────────────────────────
FAQS = [
    ("어떤 파일 형식을 지원하나요?", "이력서·채용공고 모두 PDF, DOCX, HWPX 파일을 지원해요. 구버전 HWP는 PDF로 저장한 뒤 업로드해주세요."),
    ("웹캠 없이도 이용할 수 있나요?", "네, 웹캠 없이 음성·텍스트 답변만으로도 면접을 진행할 수 있어요. 답변 내용과 논리성 분석은 동일하게 제공돼요."),
    ("면접 영상이 점수에 반영되나요?", "아니요, 영상은 시선 처리·발화 속도 등 참고용 피드백에만 사용되고 점수에는 반영되지 않아요."),
]
faq_html = "".join(
    f'<details class="faq-item">'
    f'  <summary>{q}<span class="faq-chevron">⌄</span></summary>'
    f'  <p>{a}</p>'
    f'</details>'
    for q, a in FAQS
)
st.markdown(
    f'<div class="faq-section">'
    f'  <p class="faq-title">자주 묻는 질문</p>'
    f'  <div class="faq-list">{faq_html}</div>'
    f'</div>',
    unsafe_allow_html=True,
)


# ── 7. 마무리 CTA ────────────────────────────────────────────────────
st.markdown(
    '<div class="final-cta">'
    '  <p class="final-cta-title">지금 바로 면접 준비를 시작해보세요</p>'
    '  <p class="final-cta-desc">이력서 업로드부터 결과 리포트까지, 몇 분이면 충분해요.</p>'
    '</div>',
    unsafe_allow_html=True,
)
with st.container(key="final_cta_row"):
    _, fcenter, _ = st.columns([2, 1, 2])
    with fcenter:
        if st.button("무료로 시작하기", type="primary", use_container_width=True, key="final_cta_btn"):
            if logged_in:
                st.switch_page("pages/03_면접_환경설정.py")
            else:
                st.switch_page("pages/01_로그인.py")
