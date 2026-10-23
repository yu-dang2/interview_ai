import streamlit as st
from utils.brand import FAVICON
import streamlit.components.v1 as components
import base64
from utils.paths import resource
from components.sidebar import render_sidebar
from components.setup_steps import SETUP_CSS, steps_html
from utils.state import init_session, get, set as state_set
from utils.ui import show_error

st.set_page_config(
    page_title="면접 환경설정 | intro",
    page_icon=FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()

if get("session_id"):
    st.session_state["_session_id_clear_pending"] = True
    state_set("session_id", None)
    state_set("first_question", None)
    state_set("result", None)
    state_set("interview_done", False)
    if "iv_messages" in st.session_state:
        del st.session_state["iv_messages"]

render_sidebar(active="면접 시작")


def img_b64(path: str) -> str:
    return base64.b64encode(resource(path).read_bytes()).decode()


PERSONAS = [
    {
        "key": "기술 리드", "desc": "날카롭고 집요한 기술 검증",
        "detail": ["기술 스택에 대한 심화 질문", "문제 해결 과정을 집중적으로 검증", "꼬리질문으로 논리 전개를 확인"],
        "img": img_b64("assets/images/기술리드.png"),
    },
    {
        "key": "인사 담당자", "desc": "공감 중심 인성 면접",
        "detail": ["조직 적합성과 인성 중심 평가", "협업 경험과 태도를 질문", "편안한 분위기의 대화형 진행"],
        "img": img_b64("assets/images/인사 담당자.png"),
    },
    {
        "key": "임원 면접관", "desc": "전략적 비즈니스 역량 검증",
        "detail": ["비즈니스 임팩트와 전략적 사고 검증", "의사결정 과정을 집중적으로 질문", "리더십과 책임감을 확인"],
        "img": img_b64("assets/images/임원 면접관.png"),
    },
]

selected = get("interviewer_style") or "기술 리드"

# ── CSS ─────────────────────────────────────────────────────────────────
# 단계 표시·카드·번호 제목은 문서 업로드 화면과 같은 규칙을 쓴다. 제목은 h 태그 대신 div.
st.markdown(SETUP_CSS, unsafe_allow_html=True)
st.markdown("""
<style>
.st-key-setup_name_card [data-testid="stTextInput"] { max-width: 420px; }
.st-key-setup_name_card [data-testid="stTextInput"] input { font-size: 15px !important; }
.st-key-setup_name_card [data-baseweb="input"] { height: 48px !important; border-radius: 12px !important;
    background: #fafbfd !important; border-color: #e5e7eb !important; }

.ps-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.ps-card { position: relative; border: 1px solid #e9ecf2; border-radius: 16px; padding: 22px 20px; background: #fff;
    cursor: pointer; transition: transform .15s, box-shadow .15s; min-width: 0; }
.ps-card:hover { box-shadow: 0 4px 16px rgba(59,109,239,.15); transform: translateY(-1px); }
.ps-card.on { border: 1.5px solid #3b6def; background: #f5f8ff; }
.ps-card .ck { position: absolute; top: 14px; right: 14px; width: 24px; height: 24px; border-radius: 50%;
    background: #3b6def; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 13px; }
.ps-card img { width: 72px; height: 72px; border-radius: 16px; object-fit: cover; background: #eef3ff; display: block; }
.ps-card .nm { margin-top: 14px; font-size: 17px; font-weight: 800; color: #111827; }
.ps-card.on .nm { color: #2f5bd8; }
.ps-card .ds { margin-top: 3px; font-size: 13px; color: #6b7280; }
.ps-card .dt { margin-top: 14px; padding-top: 14px; border-top: 1px solid #eef0f4; display: flex;
    flex-direction: column; gap: 7px; }
.ps-card .dt div { font-size: 12.5px; color: #4b5563; display: flex; gap: 7px; align-items: flex-start; }
.ps-card .dt i { color: #3b6def; font-size: 13px; margin-top: 2px; }

@media (max-width: 900px) {
    .ps-grid { grid-template-columns: 1fr; }
}
</style>
""", unsafe_allow_html=True)

# ── 단계 표시 · 타이틀 ────────────────────────────────────────────────────
st.markdown(
    steps_html(1)
    + '<div class="su-head"><div class="t">면접 환경 설정</div>'
    '<div class="sub">성함을 입력하고 함께할 면접관 스타일을 골라 주세요</div></div>',
    unsafe_allow_html=True,
)

# ── 01 성함 ──────────────────────────────────────────────────────────────
if st.session_state.get("setup_name"):
    state_set("user_name", st.session_state["setup_name"])

with st.container(key="setup_name_card"):
    st.markdown(
        '<div class="su-sh"><span class="n">01</span>성함</div>'
        '<div class="su-sd">면접을 시작하기 전에 성함을 입력해 주세요</div>',
        unsafe_allow_html=True,
    )
    name = st.text_input("성함", placeholder="홍길동", label_visibility="collapsed",
                         value=get("user_name") or "", key="setup_name")
if name:
    state_set("user_name", name)

# ── 02 면접관 스타일 ─────────────────────────────────────────────────────
cards_html = '<div class="ps-grid">'
for p in PERSONAS:
    is_active = selected == p["key"]
    detail_html = "".join(f'<div><i class="ph-bold ph-check"></i><span>{d}</span></div>' for d in p["detail"])
    check = '<span class="ck"><i class="ph-bold ph-check"></i></span>' if is_active else ""
    cards_html += (
        f'<div class="ps-card{" on" if is_active else ""}" data-persona-card="{p["key"]}">{check}'
        f'<img src="data:image/png;base64,{p["img"]}" alt="">'
        f'<div class="nm">{p["key"]}</div><div class="ds">{p["desc"]}</div>'
        f'<div class="dt">{detail_html}</div></div>'
    )
cards_html += '</div>'

with st.container(key="setup_persona_card"):
    st.markdown(
        '<div class="su-sh"><span class="n">02</span>면접관 스타일</div>'
        '<div class="su-sd">스타일에 따라 질문 방향과 꼬리질문이 달라져요</div>'
        + cards_html,
        unsafe_allow_html=True,
    )

# 카드를 누르면 아래 숨긴 버튼을 대신 눌러 선택을 저장한다.
st.markdown(
    "<style>.st-key-persona_hidden_row { display:none !important; }</style>",
    unsafe_allow_html=True,
)
with st.container(key="persona_hidden_row"):
    btn_cols = st.columns(3)
    for i, p in enumerate(PERSONAS):
        with btn_cols[i]:
            if st.button(p["key"], key=f"ps_{p['key']}", use_container_width=True):
                state_set("interviewer_style", p["key"])
                st.rerun()

components.html("""
<script>
(function () {
    function attach() {
        var doc = window.parent.document;
        var cards = doc.querySelectorAll('[data-persona-card]');
        if (!cards.length) { setTimeout(attach, 300); return; }

        cards.forEach(function (card) {
            var key = card.getAttribute('data-persona-card');
            card.onclick = function () {
                var btns = doc.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    if (btns[i].innerText.trim() === key) {
                        btns[i].click();
                        return;
                    }
                }
            };
        });
    }

    attach();

    setTimeout(function () {
        new MutationObserver(function () { attach(); })
            .observe(window.parent.document.body, { childList: true, subtree: true });
    }, 800);
}());
</script>
""", height=0)

# ── 다음 단계 버튼 ──────────────────────────────────────────────────────
with st.container(key="next_area"):
    _hint_col, _btn_col = st.columns([3, 1], vertical_alignment="center")
    with _hint_col:
        st.markdown('<div class="su-foot-hint">다음 단계에서 이력서와 채용공고를 올려요</div>',
                    unsafe_allow_html=True)
    with _btn_col:
        if st.button("다음: 문서 업로드 →", type="primary", key="btn_next"):
            if not (get("user_name") or name):
                show_error("성함을 입력해주세요.")
            else:
                state_set("interviewer_style", selected)
                st.switch_page("pages/031_문서업로드.py")
