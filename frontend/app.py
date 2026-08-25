import base64
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
[data-testid="stAppViewContainer"] { background: var(--ld-bg) !important; }
[data-testid="stMainBlockContainer"] { background: var(--ld-bg) !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] > div,
[data-testid="stVerticalBlock"],
[data-testid="stMainBlockContainer"] { overflow: visible !important; }
[data-testid="stMainBlockContainer"] {
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
}
</style>
""", unsafe_allow_html=True)


def img_b64(path: str) -> str:
    return base64.b64encode(resource(path).read_bytes()).decode()


def go_to_start():
    if logged_in:
        st.switch_page("pages/03_면접_환경설정.py")
    else:
        st.switch_page("pages/01_로그인.py")


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
    f'<nav class="navbar ld-navbar">'
    f'<span class="navbar-brand">intr<em>o</em></span>'
    f'<div class="navbar-right">{_nav_right}</div>'
    f'</nav>',
    unsafe_allow_html=True,
)


# ── 2. 히어로 ────────────────────────────────────────────────────────
st.markdown(
    '<div class="ld-hero">'
    '<div class="ld-hero-inner">'
    '<span class="ld-eyebrow"><span class="dot"></span>AI 면접 코칭 · intro</span>'
    '<p class="ld-hero-title">질문에는,<br><em>질문이 따라옵니다</em></p>'
    '<p class="ld-hero-sub">'
    '이력서를 읽고 던지는 첫 질문이 아니라, 방금 한 대답을 듣고 더 깊이 파고드는 다음 질문.<br>'
    'intro는 정해진 대본이 아니라 진짜 대화를 합니다.'
    '</p>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)
with st.container(key="ld_cta_row"):
    _, center, _ = st.columns([2, 1, 2])
    with center:
        if st.button("무료로 시작하기", type="primary", use_container_width=True, key="ld_cta_btn"):
            go_to_start()


# ── 3. 시그니처: 대화 스레드 데모 ───────────────────────────────────────
st.markdown('<div id="thread"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ld-thread-section"><div class="ld-thread-grid">'

    '<div class="ld-thread-copy">'
    '<span class="ld-eyebrow"><span class="dot"></span>시그니처 · 실제 대화 흐름</span>'
    '<p class="ld-title-lg">답변을 듣고,<br>그 자리에서 더 물어봅니다</p>'
    '<p>일반적인 모의면접은 미리 정해둔 질문지를 순서대로 읽는 것에 가깝습니다. '
    'intro는 다릅니다 — 방금 보낸 답변을 채점하고, 근거가 부족하거나 애매한 부분이 있으면 '
    '그 자리에서 바로 파고드는 꼬리질문을 만들어냅니다. 실제 면접관이 그렇게 하듯이요.</p>'
    '<div class="ld-thread-stat"><b>최대 2개</b><span>답변당 이어지는 꼬리질문 · 기준 점수를 넘기면 오지 않아요</span></div>'
    '</div>'

    '<div class="ld-thread-panel">'
    '<div class="ld-thread-meta">'
    '<span class="ld-pill">기술 리드</span>'
    '<span class="ld-thread-timer">27:14 남음</span>'
    '</div>'

    '<div class="ld-msg ai">'
    '<div class="ld-avatar"></div>'
    '<div class="ld-bubble ai">본인이 겪었던 가장 어려운 기술적 문제와, 그걸 해결한 과정을 설명해주세요.</div>'
    '</div>'

    '<div class="ld-msg user">'
    '<div class="ld-avatar"></div>'
    '<div class="ld-bubble user">이전 프로젝트에서 API 응답 속도가 느려서 캐싱을 도입해 해결했습니다.</div>'
    '</div>'

    '<div class="ld-gaze-inline"><span class="dot"></span>'
    '<span><b>참고</b>시선이 화면 밖으로 자주 벗어났어요 · 점수에는 반영되지 않습니다</span></div>'

    '<div class="ld-followup">'
    '<span class="ld-followup-tag">꼬리질문</span>'
    '<div class="ld-msg ai" style="margin-bottom:0;">'
    '<div class="ld-avatar"></div>'
    '<div class="ld-bubble ai">캐싱을 도입했을 때 데이터 정합성은 어떻게 관리하셨나요? 구체적인 무효화 전략이 궁금해요.</div>'
    '</div>'
    '</div>'

    '<div class="ld-msg user" style="margin-bottom:0;">'
    '<div class="ld-avatar"></div>'
    '<div class="ld-bubble user">TTL을 짧게 두고, 쓰기 발생 시점에 관련 키를 즉시 무효화하는 방식으로 처리했습니다.</div>'
    '</div>'
    '</div>'

    '</div></div>',
    unsafe_allow_html=True,
)


# ── 4. 비교: 일반 모의면접 vs intro ─────────────────────────────────────
st.markdown(
    '<div class="ld-compare-section">'
    '<div class="ld-compare-head">'
    '<span class="ld-eyebrow"><span class="dot"></span>왜 다른가</span>'
    '<p class="ld-title-lg">스터디 모의면접과는, 시작부터 다릅니다</p>'
    '</div>'
    '<div class="ld-compare-grid">'

    '<div class="ld-compare-panel old">'
    '<div class="ld-compare-panel-title">일반 모의면접</div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">–</span><span>미리 정해둔 질문지를 순서대로 읽는다</span></div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">–</span><span>피드백은 다 끝난 뒤 한꺼번에 받는다</span></div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">–</span><span>스터디원 일정을 맞춰야 한 번 볼 수 있다</span></div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">–</span><span>같은 사람이 계속 봐줘서 질문이 반복된다</span></div>'
    '</div>'

    '<div class="ld-compare-panel new">'
    '<div class="ld-compare-panel-title">intro</div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">＋</span><span>답변에 따라 그 자리에서 꼬리질문이 이어진다</span></div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">＋</span><span>논리성 등 5개 항목을 답변마다 즉시 채점한다</span></div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">＋</span><span>이력서와 채용공고만 있으면 3분 안에 시작한다</span></div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">＋</span><span>매번 새로운 조합의 질문을 무제한으로 받는다</span></div>'
    '</div>'

    '</div>'
    '</div>',
    unsafe_allow_html=True,
)


# ── 5. 기능 (2x2) ────────────────────────────────────────────────────
FEATURES = [
    {
        "title": "꼬리질문 엔진",
        "desc": "답변이 기준 점수를 넘기지 못하면, 그 자리에서 부족한 부분을 파고드는 후속 질문을 만듭니다.",
    },
    {
        "title": "실시간 5축 피드백",
        "desc": "논리성 · 커뮤니케이션 · 전문지식 · 태도 · 문제해결력, 답변마다 다섯 항목을 즉시 채점합니다.",
    },
    {
        "title": "영상 참고 리포트",
        "desc": "시선 처리와 발화 속도를 기록해서 보여드리되, 최종 면접 점수에는 반영하지 않습니다.",
    },
    {
        "title": "이력서 최적화 제안",
        "desc": "면접에서 드러난 강점과 약점을 반영해 이력서 문장을 다듬은 제안을 함께 받습니다.",
    },
]
feat_html = "".join(
    f'<div class="ld-feat-card"><div class="ld-feat-icon"></div>'
    f'<p class="ld-title-card">{f["title"]}</p><p>{f["desc"]}</p></div>'
    for f in FEATURES
)
st.markdown(
    '<div class="ld-features-section">'
    '<div class="ld-section-head">'
    '<span class="ld-eyebrow"><span class="dot"></span>기능</span>'
    '<p class="ld-title-lg">겉핥기 질문으로는 알 수 없는 것들</p>'
    '</div>'
    f'<div class="ld-features-grid">{feat_html}</div>'
    '</div>',
    unsafe_allow_html=True,
)


# ── 6. 페르소나 쇼케이스 ─────────────────────────────────────────────
PERSONAS = [
    {
        "name": "기술 리드", "desc": "날카롭고 집요한 기술 검증",
        "detail": ["기술 스택에 대한 심화 질문", "문제 해결 과정을 집중적으로 검증", "꼬리질문으로 논리 전개를 확인"],
        "img": img_b64("assets/images/기술리드.png"),
    },
    {
        "name": "인사 담당자", "desc": "공감 중심 인성 면접",
        "detail": ["조직 적합성과 인성 중심 평가", "협업 경험과 태도를 질문", "편안한 분위기의 대화형 진행"],
        "img": img_b64("assets/images/인사 담당자.png"),
    },
    {
        "name": "임원 면접관", "desc": "전략적 비즈니스 역량 검증",
        "detail": ["비즈니스 임팩트와 전략적 사고 검증", "의사결정 과정을 집중적으로 질문", "리더십과 책임감을 확인"],
        "img": img_b64("assets/images/임원 면접관.png"),
    },
]
persona_html = "".join(
    f'<div class="ld-persona-card">'
    f'<img class="ld-persona-avatar" src="data:image/png;base64,{p["img"]}">'
    f'<div class="ld-persona-name">{p["name"]}</div>'
    f'<div class="ld-persona-desc">{p["desc"]}</div>'
    f'<div class="ld-persona-detail">' + "".join(f'<div>{d}</div>' for d in p["detail"]) + '</div>'
    f'</div>'
    for p in PERSONAS
)
st.markdown(
    '<div class="ld-persona-section">'
    '<div class="ld-section-head">'
    '<span class="ld-eyebrow"><span class="dot"></span>면접관 페르소나</span>'
    '<p class="ld-title-lg">세 가지 스타일 중에 골라보세요</p>'
    '</div>'
    f'<div class="ld-persona-row">{persona_html}</div>'
    '</div>',
    unsafe_allow_html=True,
)


# ── 7. 진행 단계 (세로 리스트) ───────────────────────────────────────
STEPS = [
    {"idx": "STEP 01", "title": "이력서 · 채용공고 업로드", "desc": "지원하려는 공고와 이력서를 올리면 AI가 핵심 키워드와 요구 역량을 자동으로 분석해요."},
    {"idx": "STEP 02", "title": "면접관 선택", "desc": "기술 리드 · 인사 담당자 · 임원 중 원하는 면접관 페르소나를 고릅니다."},
    {"idx": "STEP 03", "title": "실전 면접 진행", "desc": "자기소개로 긴장을 풀고, 답변에 따라 꼬리질문까지 이어지는 대화를 최대 30분간 진행해요."},
    {"idx": "STEP 04", "title": "리포트 확인", "desc": "결과 리포트와 이력서 최적화 제안을 받고, 마이페이지에서 점수 추이를 관리해요."},
]
steps_html = "".join(
    f'<div class="ld-step"><div class="ld-step-idx">{s["idx"]}</div>'
    f'<div><p class="ld-title-step">{s["title"]}</p><p>{s["desc"]}</p></div></div>'
    for s in STEPS
)
st.markdown(
    '<div class="ld-steps-section">'
    '<div class="ld-section-head">'
    '<span class="ld-eyebrow"><span class="dot"></span>진행 방식</span>'
    '<p class="ld-title-lg">4단계면 충분합니다</p>'
    '</div>'
    f'<div class="ld-step-list">{steps_html}</div>'
    '</div>',
    unsafe_allow_html=True,
)


# ── 8. FAQ ───────────────────────────────────────────────────────────
FAQS = [
    ("꼬리질문은 몇 개까지 오나요?", "답변이 좋으면 오지 않습니다. 기준 점수를 밑돌 때만, 한 질문당 최대 2개까지 이어집니다."),
    ("첫 번째 자기소개 질문도 채점되나요?", "아니요. 긴장을 풀기 위한 라포 형성 질문이라 점수와 꼬리질문 대상 모두에서 제외됩니다."),
    ("어떤 파일 형식을 지원하나요?", "이력서·채용공고 모두 PDF, DOCX, HWPX 파일을 지원해요. 구버전 HWP는 PDF로 저장한 뒤 업로드해주세요."),
    ("웹캠 없이도 이용할 수 있나요?", "네, 웹캠 없이 텍스트·음성 답변만으로도 면접을 진행할 수 있어요. 답변 내용과 논리성 분석은 동일하게 제공돼요."),
    ("면접 영상이 점수에 반영되나요?", "아니요, 영상은 시선 처리·발화 속도 등 참고용 피드백에만 쓰이고 점수에는 반영되지 않아요."),
    ("면접 시간은 얼마나 걸리나요?", "최대 30분입니다. 시간이 다 되면 진행 중인 답변까지만 마무리하고 자동으로 종료됩니다."),
]
faq_html = "".join(
    f'<details class="ld-faq-item"><summary>{q}<span class="ld-faq-mark">+</span></summary><p>{a}</p></details>'
    for q, a in FAQS
)
st.markdown(
    '<div class="ld-faq-section">'
    '<div class="ld-section-head">'
    '<span class="ld-eyebrow"><span class="dot"></span>FAQ</span>'
    '<p class="ld-title-lg">자주 묻는 질문</p>'
    '</div>'
    f'<div class="ld-faq-list">{faq_html}</div>'
    '</div>',
    unsafe_allow_html=True,
)


# ── 9. 마무리 CTA ────────────────────────────────────────────────────
st.markdown(
    '<div class="ld-final-cta-wrap"><div class="ld-final-cta">'
    '<div>'
    '<p class="ld-title-cta">다음 질문을 받아볼 준비, 되셨나요?</p>'
    '<p>이력서와 채용공고만 올리면 3분 안에 첫 질문이 시작됩니다.</p>'
    '</div>'
    '</div></div>',
    unsafe_allow_html=True,
)
with st.container(key="ld_final_cta_row"):
    _, fcenter, _ = st.columns([2, 1, 2])
    with fcenter:
        if st.button("무료로 시작하기", type="primary", use_container_width=True, key="ld_final_cta_btn"):
            go_to_start()


# ── 10. 푸터 ─────────────────────────────────────────────────────────
st.markdown(
    '<div class="ld-footer">'
    '<span>intro — AI 면접 코칭</span>'
    '<span>© 2026 intro</span>'
    '</div>',
    unsafe_allow_html=True,
)
