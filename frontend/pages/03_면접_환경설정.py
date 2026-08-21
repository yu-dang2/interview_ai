import streamlit as st
import streamlit.components.v1 as components
import base64
from utils.paths import resource
from components.sidebar import render_sidebar
from utils.state import init_session, get, set as state_set
from utils.ui import show_error

st.set_page_config(
    page_title="면접 환경설정 | intro",
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
st.markdown("""
<style>
[data-testid="stMainBlockContainer"] { padding: 40px 48px 60px !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stHorizontalBlock"] { gap: 0; }

[data-testid="stMainBlockContainer"] {
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
}

[data-testid="stTextInput"] label p {
    font-size:14px !important; font-weight:600 !important; color:#1f1f1f !important;
}

[data-testid="stBaseButton-primary"] {
    font-size: 17px !important;
    padding: 12px 50px !important;
    white-space: nowrap !important;
    width: auto !important;
}
.st-key-next_area {
    display: grid !important;
    grid-template-columns: max-content !important;
    justify-content: center !important;
    row-gap: 8px !important;
}
.st-key-next_area [data-testid="stAlert"] {
    justify-self: stretch !important;
    box-sizing: border-box !important;
}

[data-persona-card]:hover {
    box-shadow: 0 4px 16px rgba(59,109,239,0.15) !important;
    transform: translateY(-1px) !important;
}

@media (max-width: 900px) {
    [data-persona-card] {
        flex-direction: column !important;
        text-align: center !important;
        padding: 20px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ── 스텝 인디케이터 ────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;justify-content:center;margin-bottom:32px;">
  <div style="width:10px;height:10px;border-radius:50%;background:#3b6def;flex-shrink:0;"></div>
  <span style="font-size:11px;font-weight:600;color:#3b6def;margin:0 6px 0 4px;">기본 정보</span>
  <div style="width:52px;height:1px;background:#d9dee8;"></div>
  <div style="width:10px;height:10px;border-radius:50%;background:#d9dee8;flex-shrink:0;margin-left:4px;"></div>
  <span style="font-size:11px;color:#9ca3af;margin-left:4px;">문서 업로드</span>
</div>
""", unsafe_allow_html=True)

# ── 타이틀 ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:60px;">
  <div style="font-size:24px;font-weight:700;color:#1f1f1f;margin:0 0 6px;">
    면접 환경을 설정해주세요
  </div>
  <p style="font-size:14px;color:#9ca3af;margin:0;">
    성함과 AI 면접관 스타일을 먼저 정해주세요. 다음 단계에서 문서를 업로드해요.
  </p>
</div>
""", unsafe_allow_html=True)

# ── 성함 ────────────────────────────────────────────────────────────────

if st.session_state.get("setup_name"):
    state_set("user_name", st.session_state["setup_name"])

name_col, _ = st.columns([1, 2])
with name_col:
    name = st.text_input("성함", placeholder="홍길동",
                         value=get("user_name") or "", key="setup_name")
if name:
    state_set("user_name", name)

st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)

# ── 면접관 스타일 ────────────────────────────────────────────────────────
st.markdown('<p style="font-size:14px;font-weight:600;color:#1f1f1f;margin:0 0 20px;">면접관 스타일 선택</p>',
            unsafe_allow_html=True)

# 페르소나 카드
cards_html = '<div style="display:flex;gap:28px;">'
for p in PERSONAS:
    is_active  = selected == p["key"]
    border     = "1.5px solid #3b6def" if is_active else "1px solid #e5e7eb"
    bg         = "#eff6ff"             if is_active else "white"
    name_color = "#3b6def"             if is_active else "#1f1f1f"
    detail_html = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;margin-top:4px;">'
        f'<div style="width:4px;height:4px;border-radius:50%;background:#3b6def;flex-shrink:0;"></div>'
        f'<span style="font-size:11px;color:#6b7280;word-break:keep-all;">{d}</span></div>'
        for d in p["detail"]
    )
    cards_html += f"""
    <div data-persona-card="{p['key']}"
         style="flex:1;min-width:0;border:{border};background:{bg};border-radius:12px;
                padding:20px;display:flex;align-items:flex-start;gap:20px;
                cursor:pointer;box-sizing:border-box;
                transition:transform 0.15s,box-shadow 0.15s;">
      <img src="data:image/png;base64,{p['img']}"
           style="width:64px;height:64px;border-radius:50%;
                  object-fit:cover;flex-shrink:0;">
      <div style="min-width:0;">
        <div style="font-size:15px;font-weight:700;color:{name_color};
                    margin-bottom:2px;word-break:keep-all;">{p['key']}</div>
        <div style="font-size:12px;color:#9ca3af;word-break:keep-all;margin-bottom:8px;">{p['desc']}</div>
        {detail_html}
      </div>
    </div>"""
cards_html += '</div>'
st.markdown(cards_html, unsafe_allow_html=True)

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

st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)

# ── 다음 단계 버튼 ──────────────────────────────────────────────────────
_, center, _ = st.columns([4.3, 2, 4.3])
with center:
    with st.container(key="next_area"):
        if st.button("다음: 문서 업로드 →", type="primary", key="btn_next"):
            if not (get("user_name") or name):
                show_error("성함을 입력해주세요.")
            else:
                state_set("interviewer_style", selected)
                st.switch_page("pages/031_문서업로드.py")
