import base64
import streamlit as st
import streamlit.components.v1 as components
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

/* 페르소나 스위처 (대화 스레드 데모 위) */
.st-key-ld_persona_switch {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 40px 12px;
}
.st-key-ld_persona_switch [data-testid="stHorizontalBlock"] {
    max-width: 420px;
    margin: 0 auto;
    gap: 8px !important;
}
.st-key-ld_persona_switch [data-testid="stBaseButton-primary"],
.st-key-ld_persona_switch [data-testid="stBaseButton-secondary"] {
    font-size: 12.5px !important;
    font-weight: 600 !important;
    padding: 0.55em 0.4em !important;
    border-radius: 999px !important;
    white-space: nowrap !important;
}
.st-key-ld_persona_switch [data-testid="stBaseButton-primary"] p,
.st-key-ld_persona_switch [data-testid="stBaseButton-secondary"] p {
    font-size: 12.5px !important;
    font-weight: 600 !important;
}
.st-key-ld_persona_switch [data-testid="stBaseButton-secondary"] {
    background: white !important;
    border-color: var(--border) !important;
    color: var(--gray-500) !important;
}
.ld-switch-label {
    text-align: center; font-size: 12.5px !important; color: var(--ld-muted);
    margin: 0 0 22px !important; word-break: keep-all;
}

/* 스크롤 리빌 (아래로 스크롤하면 섹션이 떠오르듯 나타남) */
.ld-reveal {
    opacity: 0;
    transform: translateY(18px);
    transition: opacity 0.6s ease, transform 0.6s ease;
}
.ld-reveal.is-visible { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) {
    .ld-reveal { opacity: 1; transform: none; transition: none; }
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


# ── 0. 스크롤 진행 바 ────────────────────────────────────────────────
st.markdown('<div class="ld-scrollbar" id="ld-scrollbar"></div>', unsafe_allow_html=True)


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
PERSONA_IMG = {
    "기술 리드": img_b64("assets/images/기술리드.png"),
    "인사 담당자": img_b64("assets/images/인사 담당자.png"),
    "임원 면접관": img_b64("assets/images/임원 면접관.png"),
}
hero_stage_html = (
    '<div class="ld-hero-stage" aria-hidden="true">'
    '<div class="ld-iv-card back b2">'
    f'<img src="data:image/png;base64,{PERSONA_IMG["임원 면접관"]}" alt=""><b>임원 면접관</b></div>'
    '<div class="ld-iv-card back b1">'
    f'<img src="data:image/png;base64,{PERSONA_IMG["기술 리드"]}" alt=""><b>기술 리드</b></div>'
    '<div class="ld-iv-card front">'
    '<div class="ld-iv-head">'
    f'<img src="data:image/png;base64,{PERSONA_IMG["인사 담당자"]}" alt="">'
    '<div class="ld-iv-who"><b>인사 담당자</b><span>공감 중심 인성 면접</span></div>'
    '<span class="ld-iv-live"><i></i>질문 중</span>'
    '</div>'
    '<div class="ld-iv-q">팀 내에서 의견 충돌이 있었던 경험과, 그걸 어떻게 풀어갔는지 말씀해주세요.</div>'
    '<div class="ld-iv-a">일정 우선순위로 의견이 갈려서, 근거를 정리해 다시 논의했습니다.</div>'
    '<div class="ld-iv-fu">'
    '<span class="ld-iv-fu-tag"><span class="ld-typing"><span></span><span></span><span></span></span>꼬리질문</span>'
    '<p>그 과정에서 상대방 의견은 어디까지 받아들이셨나요?</p>'
    '</div>'
    '</div>'
    '</div>'
)
def _kinetic(text: str, start_delay: float, step: float = 0.045) -> str:
    out = ""
    i = 0
    for word in text.split(" "):
        d = start_delay + i * step
        out += f'<span class="ld-kinetic-word" style="animation-delay:{d:.3f}s">{word}</span> '
        i += 1
    return out.strip()

st.markdown(
    '<div class="ld-hero">'
    '<div class="ld-hero-grid"></div>'
    '<div class="ld-hero-wrap">'
    '<div class="ld-hero-inner">'
    '<p class="ld-hero-quote"><em>Meet your interview before the real interview.</em></p>'
    '<p class="ld-hero-title">'
    f'{_kinetic("실제 면접 전에,", 0.05)}<br>'
    f'<em>{_kinetic("먼저 만나보는 AI 면접관", 0.32)}</em>'
    '</p>'
    '<p class="ld-hero-sub">'
    '이력서를 읽고 던지는 첫 질문이 아니라, 방금 한 대답을 듣고 더 깊이 파고드는 다음 질문. '
    'intro는 정해진 대본이 아니라 진짜 대화를 합니다.'
    '</p>'
    '</div>'
    f'{hero_stage_html}'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

with st.container(key="ld_cta_row"):
    cta_col, _ = st.columns([1, 4.4])
    with cta_col:
        if st.button("무료로 시작하기", type="primary", use_container_width=True, key="ld_cta_btn"):
            go_to_start()


# ── 3. 시그니처: 답변 피커(즉석 체험) + 페르소나별 전체 대화 데모 ──────────────
FEATURE_PICKER_Q = "캐싱 도입 시 데이터 정합성은 어떻게 관리하셨나요?"
FEATURE_PICKER_OPTIONS = [
    ("TTL을 짧게 설정해서 자동으로 만료되게 했습니다.", "TTL을 얼마나 짧게 설정하셨고, 그 값은 어떻게 정하셨나요?"),
    ("쓰기 시점에 관련 캐시를 즉시 무효화하는 방식을 썼습니다.", "무효화가 실패했을 때의 폴백 전략은 어떻게 설계하셨나요?"),
    ("딱히 전략은 없었고, 필요할 때마다 수동으로 지웠습니다.", "수동으로 지우는 과정에서 누락된 적은 없었나요? 그건 어떻게 확인하세요?"),
]
_feat_opt_html = "".join(
    f'<div class="ld-opt" data-i="{i}" data-a="{a}" data-fu="{fu}">'
    '<div class="ld-opt-radio"></div>'
    f'<p>&ldquo;{a}&rdquo;</p>'
    '</div>'
    for i, (a, fu) in enumerate(FEATURE_PICKER_OPTIONS)
)

THREAD_DEMOS = {
    "기술 리드": {
        "timer": "27:14 남음",
        "q1": "본인이 겪었던 가장 어려운 기술적 문제와, 그걸 해결한 과정을 설명해주세요.",
        "a1": "이전 프로젝트에서 API 응답 속도가 느려서 캐싱을 도입해 해결했습니다.",
        "speech": ("빠름", "말이 다소 빨라요. 조금 천천히 또박또박 말해보세요."),
        "q2": "캐싱을 도입했을 때 데이터 정합성은 어떻게 관리하셨나요? 구체적인 무효화 전략이 궁금해요.",
        "a2": "TTL을 짧게 두고, 쓰기 발생 시점에 관련 키를 즉시 무효화하는 방식으로 처리했습니다.",
        "score": 87,
    },
    "인사 담당자": {
        "timer": "24:50 남음",
        "q1": "팀 내에서 의견 충돌이 있었던 경험과, 그걸 어떻게 풀어갔는지 말씀해주세요.",
        "a1": "일정 우선순위를 두고 동료와 의견이 갈렸는데, 각자 근거를 정리해서 다시 논의하는 자리를 가졌습니다.",
        "speech": ("느림", "말이 다소 느려요. 조금 더 또렷하고 빠르게 말해보세요."),
        "q2": "그 과정에서 상대방 의견을 어디까지 수용하셨나요? 본인 생각과 다른 부분은 어떻게 받아들이셨어요?",
        "a2": "제 쪽 일정 추정이 낙관적이었다는 걸 인정하고, 상대방 제안대로 버퍼를 늘려서 진행했습니다.",
        "score": 91,
    },
    "임원 면접관": {
        "timer": "21:02 남음",
        "q1": "지금까지 내린 결정 중 비즈니스에 가장 큰 영향을 준 선택은 무엇이었나요?",
        "a1": "신규 기능 출시를 2주 미루고, 기존 사용자 이탈 원인부터 분석하자고 제안했습니다.",
        "speech": ("적정", "발화 속도가 적정해요. 듣기 편한 속도입니다."),
        "q2": "그 결정으로 포기한 것과 얻은 것을 숫자로 설명해주실 수 있나요?",
        "a2": "출시는 2주 늦었지만, 이탈 원인을 고쳐서 재방문율이 18% 올랐습니다.",
        "score": 84,
    },
}
PERSONAS = {
    "기술 리드": {
        "desc": "날카롭고 집요한 기술 검증",
        "detail": ["기술 스택에 대한 심화 질문", "문제 해결 과정을 집중적으로 검증", "꼬리질문으로 논리 전개를 확인"],
    },
    "인사 담당자": {
        "desc": "공감 중심 인성 면접",
        "detail": ["조직 적합성과 인성 중심 평가", "협업 경험과 태도를 질문", "편안한 분위기의 대화형 진행"],
    },
    "임원 면접관": {
        "desc": "전략적 비즈니스 역량 검증",
        "detail": ["비즈니스 임팩트와 전략적 사고 검증", "의사결정 과정을 집중적으로 질문", "리더십과 책임감을 확인"],
    },
}

if "ld_demo_persona" not in st.session_state:
    st.session_state["ld_demo_persona"] = "기술 리드"
_active_persona = st.session_state["ld_demo_persona"]
_demo = THREAD_DEMOS[_active_persona]
_persona_info = PERSONAS[_active_persona]

st.markdown('<div id="thread"></div>', unsafe_allow_html=True)

st.markdown(
    '<div class="ld-story-section">'
    '<div class="ld-story-head ld-reveal">'
    '<p class="ld-title-lg">답변을 듣고,<br>그 자리에서 더 물어봅니다</p>'
    '<p>방금 보낸 답변을 채점하고, 근거가 부족한 부분을 그 자리에서 파고듭니다. '
    '아래에서 답변을 직접 골라보세요.</p>'
    '</div>'
    '<div class="ld-feature-split ld-reveal" id="ld-feature-area">'

    '<div class="ld-feature-left">'
    '<div class="ld-picker" id="ld-picker">'
    f'{_feat_opt_html}'
    '</div>'
    '</div>'

    '<div class="ld-feature-right" id="ld-tilt-area">'
    '<div class="ld-mini-panel" id="ld-mini-panel">'
    '<div class="ld-mini-panel-chrome">'
    '<div class="dots"><span></span><span></span><span></span></div>'
    '<div class="live"><span class="d"></span>intro 면접 세션</div>'
    '</div>'
    '<div class="ld-mini-panel-body">'
    '<div class="pb-label">AI 면접관의 질문</div>'
    f'<div class="pb-q-text">{FEATURE_PICKER_Q}</div>'
    '<div class="pb-label">선택한 답변</div>'
    f'<div class="pb-a-text" id="ld-pb-a">{FEATURE_PICKER_OPTIONS[0][0]}</div>'
    '<div class="pb-arrow">↓</div>'
    '<div class="pb-fu-tag"><span class="typing"><span></span><span></span><span></span></span>꼬리질문</div>'
    f'<div class="pb-fu-text" id="ld-pb-fu">{FEATURE_PICKER_OPTIONS[0][1]}</div>'
    '</div>'
    '</div>'
    '</div>'

    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="ld-section-head ld-switch-head">'
    '<p class="ld-title-lg">세 가지 스타일 중에 골라보세요</p>'
    '<p class="ld-switch-label">면접관을 바꾸면 같은 흐름이라도 질문이 달라집니다</p>'
    '</div>',
    unsafe_allow_html=True,
)
with st.container(key="ld_persona_switch"):
    _cols = st.columns(3)
    for _col, _persona in zip(_cols, THREAD_DEMOS.keys()):
        with _col:
            _is_active = _persona == _active_persona
            if st.button(
                _persona, key=f"ld_switch_{_persona}", use_container_width=True,
                type="primary" if _is_active else "secondary",
            ):
                st.session_state["ld_demo_persona"] = _persona
                st.rerun()

st.markdown(
    '<div class="ld-thread-section"><div class="ld-thread-grid ld-thread-grid-solo">'

    '<div class="ld-thread-panel">'
    '<div class="ld-thread-meta">'
    '<div class="ld-thread-who">'
    f'<img src="data:image/png;base64,{PERSONA_IMG[_active_persona]}" alt="{_active_persona} 면접관">'
    f'<div><b>{_active_persona}</b><span>{_persona_info["desc"]}</span></div>'
    '</div>'
    f'<span class="ld-thread-timer">{_demo["timer"]}</span>'
    '</div>'
    '<div class="ld-thread-traits">'
    + "".join(f'<span>{d}</span>' for d in _persona_info["detail"]) +
    '</div>'

    '<div class="ld-story-step" data-order="0">'
    '<div class="ld-msg ai">'
    '<div class="ld-avatar"></div>'
    f'<div class="ld-bubble ai">{_demo["q1"]}</div>'
    '</div></div>'

    '<div class="ld-story-step" data-order="1">'
    '<div class="ld-msg user">'
    '<div class="ld-avatar"></div>'
    f'<div class="ld-bubble user">{_demo["a1"]}</div>'
    '</div></div>'

    '<div class="ld-story-step" data-order="2">'
    '<div class="ld-gaze-inline">'
    f'<span><b>발화 속도 · {_demo["speech"][0]}</b>{_demo["speech"][1]}</span></div>'
    '</div>'

    '<div class="ld-story-step" data-order="3">'
    '<div class="ld-followup">'
    '<span class="ld-followup-tag"><span class="ld-typing"><span></span><span></span><span></span></span>&nbsp; 꼬리질문 생성 중</span>'
    '<div class="ld-msg ai" style="margin-bottom:0;">'
    '<div class="ld-avatar"></div>'
    f'<div class="ld-bubble ai">{_demo["q2"]}</div>'
    '</div>'
    '</div></div>'

    '<div class="ld-story-step" data-order="4">'
    '<div class="ld-msg user" style="margin-bottom:0;">'
    '<div class="ld-avatar"></div>'
    f'<div class="ld-bubble user">{_demo["a2"]}</div>'
    '</div></div>'

    '<div class="ld-story-step" data-order="5">'
    '<div style="text-align:center;padding-top:6px;">'
    '<span class="ld-score-badge"><span class="ld-count-num" data-target="' + str(_demo["score"]) + '">0</span>'
    '<span class="unit">점 · 종합 평가</span></span>'
    '</div></div>'

    '</div>'

    '</div></div>',
    unsafe_allow_html=True,
)


# ── 4. 비교: 일반 모의면접 vs intro ─────────────────────────────────────
st.markdown(
    '<div class="ld-compare-section ld-reveal">'
    '<div class="ld-compare-head">'
    '<p class="ld-title-lg">스터디 모의면접과는, 시작부터 다릅니다</p>'
    '</div>'
    '<div class="ld-compare-grid ld-stagger">'

    '<div class="ld-compare-panel old ld-tilt">'
    '<div class="ld-compare-panel-title">일반 모의면접</div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">–</span><span>미리 정해둔 질문지를 순서대로 읽는다</span></div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">–</span><span>피드백은 다 끝난 뒤 한꺼번에 받는다</span></div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">–</span><span>스터디원 일정을 맞춰야 한 번 볼 수 있다</span></div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">–</span><span>같은 사람이 계속 봐줘서 질문이 반복된다</span></div>'
    '</div>'

    '<div class="ld-compare-panel new ld-tilt">'
    '<div class="ld-compare-panel-title">intro</div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">＋</span><span>답변에 따라 그 자리에서 꼬리질문이 이어진다</span></div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">＋</span><span>논리성 등 5개 항목을 답변마다 즉시 채점한다</span></div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">＋</span><span>이력서와 채용공고만 있으면 3분 안에 시작한다</span></div>'
    '<div class="ld-compare-row"><span class="ld-compare-mark">＋</span><span>매번 새로운 조합의 질문을 받는다</span></div>'
    '</div>'

    '</div>'
    '</div>',
    unsafe_allow_html=True,
)


# ── 5. 기능 (큰 카드 1 + 줄 목록 2) ──────────────────────────────────────────
FEATURES = [
    {
        "title": "실시간 5축 피드백",
        "desc": "논리성 · 커뮤니케이션 · 전문지식 · 태도 · 문제해결력, 답변마다 다섯 항목을 즉시 채점합니다.",
        "icon": "ph-bold ph-gauge",
    },
    {
        "title": "영상 참고 리포트",
        "desc": "시선 처리와 발화 속도를 참고용으로 기록해 보여드려요.",
        "icon": "ph-bold ph-video-camera",
    },
    {
        "title": "이력서 최적화 제안",
        "desc": "면접에서 드러난 강점과 약점을 반영해 이력서 문장을 다듬은 제안을 함께 받습니다.",
        "icon": "ph-bold ph-note-pencil",
    },
]

FEATURE_AXES = [("논리성", 88), ("커뮤니케이션", 74), ("전문 지식", 91), ("태도", 83), ("문제 해결력", 69)]
_main_feat = FEATURES[0]
_axes_html = "".join(
    f'<div class="ld-axis"><span>{name}</span>'
    f'<div class="ld-axis-bar"><i style="width:{score}%"></i></div>'
    f'<b>{score}</b></div>'
    for name, score in FEATURE_AXES
)

_FEATURE_PREVIEWS = {
    "영상 참고 리포트": (
        '<div class="ld-mini-preview ld-video-preview">'
        '<div class="ld-mini-metric"><span>시선 처리</span>'
        '<p><b class="ld-level">보통</b>대체로 좋지만 시선이 가끔 흔들려요.</p></div>'
        '<div class="ld-mini-metric"><span>발화 속도</span>'
        '<p><b class="ld-level">적정</b>발화 속도가 적정해요. 듣기 편한 속도입니다.</p></div>'
        '</div>'
    ),
    "이력서 최적화 제안": (
        '<div class="ld-mini-preview ld-resume-preview">'
        '<div class="ld-resume-line before"><span>기존</span><p>API 성능을 개선했습니다.</p></div>'
        '<div class="ld-resume-line after"><span>개선 제안</span>'
        '<p>캐싱을 도입해 API 응답 속도를 개선한 경험을 구체적으로 서술했습니다.</p></div>'
        '</div>'
    ),
}
_side_html = "".join(
    f'<div class="ld-feat-row">'
    f'<div class="ld-feat-row-head"><i class="ld-feat-icon {f["icon"]}"></i>'
    f'<p class="ld-title-card">{f["title"]}</p></div>'
    f'<p>{f["desc"]}</p>'
    f'{_FEATURE_PREVIEWS.get(f["title"], "")}'
    f'</div>'
    for f in FEATURES[1:]
)
st.markdown(
    '<div class="ld-features-section ld-reveal">'
    '<div class="ld-section-head">'
    '<p class="ld-title-lg">겉핥기 질문으로는 알 수 없는 것들</p>'
    '</div>'
    '<div class="ld-bento ld-stagger">'
    '<div class="ld-bento-main">'
    f'<i class="ld-feat-icon {_main_feat["icon"]}"></i>'
    f'<p class="ld-title-card">{_main_feat["title"]}</p><p>{_main_feat["desc"]}</p>'
    '<div class="ld-axis-card">'
    '<div class="ld-axis-head"><span>방금 한 답변</span><span class="ld-axis-total">81<small>점</small></span></div>'
    f'{_axes_html}'
    '</div>'
    '</div>'
    f'<div class="ld-bento-side">{_side_html}</div>'
    '</div>'
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
    '<div class="ld-steps-section ld-reveal">'
    '<div class="ld-section-head">'
    '<p class="ld-title-lg">4단계면 충분합니다</p>'
    '</div>'
    f'<div class="ld-step-list" id="ld-step-list"><div class="ld-step-fill" id="ld-step-fill"></div>{steps_html}</div>'
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
    '<div class="ld-faq-section ld-reveal">'
    '<div class="ld-section-head">'
    '<p class="ld-title-lg">자주 묻는 질문</p>'
    '</div>'
    f'<div class="ld-faq-list">{faq_html}</div>'
    '</div>',
    unsafe_allow_html=True,
)


# ── 9. 마무리 CTA ────────────────────────────────────────────────────
st.markdown(
    '<div class="ld-final-cta-wrap ld-reveal"><div class="ld-final-cta">'
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
    '<span>intro · AI 면접 코칭</span>'
    '<span>© 2026 intro</span>'
    '</div>',
    unsafe_allow_html=True,
)


# ── 11. 스크롤 리빌 (섹션이 화면에 들어오면 떠오르듯 표시) ────────────────

components.html(
    """
    <script>
    (function () {
        var win = window.parent;
        var doc = win.document;

        // ── 리빌(reveal) + 스태거 + 스토리 패널 ──────────────────────────
        function check() {
            var vh = win.innerHeight || doc.documentElement.clientHeight;

            doc.querySelectorAll('.ld-reveal:not(.is-visible), .ld-stagger:not(.is-visible)')
                .forEach(function (el) {
                    var rect = el.getBoundingClientRect();
                    if (rect.top < vh * 0.92) el.classList.add('is-visible');
                });

            var panel = doc.querySelector('.ld-thread-panel:not(.is-visible)');
            if (panel) {
                var r = panel.getBoundingClientRect();
                if (r.top < vh * 0.85) {
                    panel.classList.add('is-visible');
                    win.setTimeout(function () { runCountUps(panel); }, 1550);
                }
            }
        }

        // ── 점수 카운트업 ────────────────────────────────────────────────
        function runCountUps(scope) {
            (scope || doc).querySelectorAll('.ld-count-num:not([data-done])').forEach(function (el) {
                el.setAttribute('data-done', '1');
                var target = parseInt(el.getAttribute('data-target'), 10) || 0;
                var start = null;
                var dur = 900;
                function step(ts) {
                    if (!start) start = ts;
                    var p = Math.min(1, (ts - start) / dur);
                    var eased = 1 - Math.pow(1 - p, 3);
                    el.textContent = Math.round(eased * target);
                    if (p < 1) win.requestAnimationFrame(step);
                }
                win.requestAnimationFrame(step);
            });
        }

        // ── 스크롤 진행 바 ───────────────────────────────────────────────
        function updateScrollbar(scroller) {
            var bar = doc.getElementById('ld-scrollbar');
            if (!bar) return;
            var max = scroller.scrollHeight - scroller.clientHeight;
            var pct = max > 0 ? Math.min(100, Math.max(0, (scroller.scrollTop / max) * 100)) : 0;
            bar.style.width = pct + '%';
        }

        // ── Steps 연결선 채우기 ──────────────────────────────────────────
        function updateStepFill() {
            var list = doc.getElementById('ld-step-list');
            var fill = doc.getElementById('ld-step-fill');
            if (!list || !fill) return;
            var vh = win.innerHeight || doc.documentElement.clientHeight;
            var rect = list.getBoundingClientRect();
            var total = rect.height;
            var visible = (vh * 0.75) - rect.top;
            var pct = total > 0 ? Math.min(100, Math.max(0, (visible / total) * 100)) : 0;
            fill.style.height = pct + '%';
        }

        // ── 카드 틸트 (마우스 추적) ──────────────────────────────────────
        function attachTilt() {
            doc.querySelectorAll('.ld-tilt:not([data-tilt-bound])').forEach(function (el) {
                el.setAttribute('data-tilt-bound', '1');
                el.addEventListener('mousemove', function (e) {
                    var r = el.getBoundingClientRect();
                    var px = (e.clientX - r.left) / r.width - 0.5;
                    var py = (e.clientY - r.top) / r.height - 0.5;
                    el.style.transform =
                        'perspective(700px) rotateX(' + (-py * 7) + 'deg) rotateY(' + (px * 7) + 'deg) translateY(-4px)';
                });
                el.addEventListener('mouseleave', function () {
                    el.style.transform = '';
                });
            });
        }

        // ── 히어로 답변 피커: 슬라이딩 글라이더 + 라이브 타이핑 + 커서 스포트라이트
        //    + 패널 3D 틸트 + 매그네틱 CTA ──────────────────────────────────
        function attachHeroPicker() {
            var picker = doc.getElementById('ld-picker');
            var aEl = doc.getElementById('ld-pb-a');
            var fuEl = doc.getElementById('ld-pb-fu');
            if (!picker || !aEl || !fuEl) return;

            var opts = Array.prototype.slice.call(picker.querySelectorAll('.ld-opt'));
            if (!opts.length) return;

            function typeInto(el, text, speed, token) {
                el.textContent = '';
                var i = 0;
                function step() {
                    if (token !== win.__ldHeroTypingToken) return;
                    i++;
                    el.textContent = text.slice(0, i);
                    var caret = doc.createElement('span');
                    caret.className = 'caret';
                    el.appendChild(caret);
                    if (i < text.length) {
                        win.setTimeout(step, speed);
                    } else {
                        el.textContent = text;
                    }
                }
                step();
            }

            function animateSelect(opt) {
                var liveOpts = Array.prototype.slice.call(
                    (doc.getElementById('ld-picker') || picker).querySelectorAll('.ld-opt')
                );
                var liveA = doc.getElementById('ld-pb-a') || aEl;
                var liveFu = doc.getElementById('ld-pb-fu') || fuEl;
                liveOpts.forEach(function (o) { o.classList.toggle('active', o === opt); });
                win.__ldHeroTypingToken = (win.__ldHeroTypingToken || 0) + 1;
                var token = win.__ldHeroTypingToken;
                var a = opt.getAttribute('data-a');
                var fu = opt.getAttribute('data-fu');
                liveA.style.opacity = 0;
                win.setTimeout(function () {
                    if (token !== win.__ldHeroTypingToken) return;
                    liveA.textContent = a;
                    liveA.style.opacity = 1;
                    typeInto(liveFu, fu, 18, token);
                }, 150);
            }
            function syncInstant(opt) {
                opts.forEach(function (o) { o.classList.toggle('active', o === opt); });
                aEl.textContent = opt.getAttribute('data-a');
                aEl.style.opacity = 1;
                fuEl.textContent = opt.getAttribute('data-fu');
            }

            if (win.__ldHeroClickHandler) doc.body.removeEventListener('click', win.__ldHeroClickHandler);
            win.__ldHeroClickHandler = function (e) {
                var opt = e.target.closest ? e.target.closest('.ld-opt') : null;
                if (!opt) return;
                animateSelect(opt);
            };
            doc.body.addEventListener('click', win.__ldHeroClickHandler);

            syncInstant(picker.querySelector('.ld-opt.active') || opts[0]);

            // 커서 스포트라이트 (히어로 전체 영역)
            var heroArea = doc.getElementById('ld-feature-area');
            if (heroArea) {
                if (win.__ldHeroSpotlightHandler) heroArea.removeEventListener('mousemove', win.__ldHeroSpotlightHandler);
                win.__ldHeroSpotlightHandler = function (e) {
                    var r = heroArea.getBoundingClientRect();
                    heroArea.style.setProperty('--mx', (e.clientX - r.left) + 'px');
                    heroArea.style.setProperty('--my', (e.clientY - r.top) + 'px');
                };
                heroArea.addEventListener('mousemove', win.__ldHeroSpotlightHandler);
            }

            // 미니 패널 3D 틸트
            var tiltArea = doc.getElementById('ld-tilt-area');
            var miniPanel = doc.getElementById('ld-mini-panel');
            if (tiltArea && miniPanel) {
                if (win.__ldHeroTiltMove) tiltArea.removeEventListener('mousemove', win.__ldHeroTiltMove);
                if (win.__ldHeroTiltLeave) tiltArea.removeEventListener('mouseleave', win.__ldHeroTiltLeave);
                win.__ldHeroTiltMove = function (e) {
                    var r = tiltArea.getBoundingClientRect();
                    var px = (e.clientX - r.left) / r.width - 0.5;
                    var py = (e.clientY - r.top) / r.height - 0.5;
                    miniPanel.style.transform = 'rotateX(' + (-py * 6) + 'deg) rotateY(' + (px * 6) + 'deg)';
                };
                win.__ldHeroTiltLeave = function () { miniPanel.style.transform = ''; };
                tiltArea.addEventListener('mousemove', win.__ldHeroTiltMove);
                tiltArea.addEventListener('mouseleave', win.__ldHeroTiltLeave);
            }

            // 매그네틱 CTA 버튼
            var ctaRow = doc.querySelector('.st-key-ld_cta_row [data-testid="stHorizontalBlock"]');
            var ctaBtn = doc.querySelector('.st-key-ld_cta_row .stButton > button');
            if (ctaRow && ctaBtn) {
                if (win.__ldHeroMagnetMove) ctaRow.removeEventListener('mousemove', win.__ldHeroMagnetMove);
                if (win.__ldHeroMagnetLeave) ctaRow.removeEventListener('mouseleave', win.__ldHeroMagnetLeave);
                win.__ldHeroMagnetMove = function (e) {
                    var r = ctaBtn.getBoundingClientRect();
                    var relX = e.clientX - (r.left + r.width / 2);
                    var relY = e.clientY - (r.top + r.height / 2);
                    if (Math.abs(relX) < r.width && Math.abs(relY) < r.height * 2) {
                        ctaBtn.style.transform = 'translate(' + (relX * 0.2) + 'px, ' + (relY * 0.2) + 'px)';
                    }
                };
                win.__ldHeroMagnetLeave = function () { ctaBtn.style.transform = ''; };
                ctaRow.addEventListener('mousemove', win.__ldHeroMagnetMove);
                ctaRow.addEventListener('mouseleave', win.__ldHeroMagnetLeave);
            }
        }

        function onScrollFrame() {
            var scroller = doc.querySelector('[data-testid="stMain"]');
            if (scroller) {
                updateScrollbar(scroller);
                var nav = doc.querySelector('.ld-navbar');
                if (nav) nav.classList.toggle('is-scrolled', scroller.scrollTop > 8);
            }
            check();
            updateStepFill();
        }

        function attach() {
            var scroller = doc.querySelector('[data-testid="stMain"]') || win;
            var ticking = false;
            function onScroll() {
                if (ticking) return;
                ticking = true;
                win.requestAnimationFrame(function () { onScrollFrame(); ticking = false; });
            }
            scroller.addEventListener('scroll', onScroll, { passive: true });
            win.addEventListener('resize', onScroll, { passive: true });
            onScrollFrame();
            attachTilt();
            attachHeroPicker();
        }

        attach();
        setTimeout(function () { onScrollFrame(); attachTilt(); attachHeroPicker(); }, 300);
        setTimeout(function () { onScrollFrame(); attachTilt(); attachHeroPicker(); }, 1000);
        var interval = win.setInterval(function () { onScrollFrame(); attachTilt(); attachHeroPicker(); }, 400);
        setTimeout(function () { win.clearInterval(interval); }, 15000);
    })();
    </script>
    """,
    height=0,
)
