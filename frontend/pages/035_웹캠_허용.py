import streamlit as st
from utils.brand import FAVICON
from components.sidebar import render_sidebar
from components.setup_steps import SETUP_CSS, steps_html
from utils.state import init_session

st.set_page_config(
    page_title="웹캠 허용 | intro",
    page_icon=FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
render_sidebar(active="면접 시작")

# 단계 표시·카드·번호 제목은 환경설정·문서 업로드와 같은 규칙(components/setup_steps.py)을 쓴다.
st.markdown(SETUP_CSS, unsafe_allow_html=True)
st.markdown("""<style>
.st-key-cam_choice_card [data-testid="stHorizontalBlock"] { gap: 16px !important; align-items: stretch !important; }
.st-key-cam_choice_card [data-testid="stColumn"] > [data-testid="stVerticalBlock"] { height: 100%; }
.st-key-cam_opt_on, .st-key-cam_opt_off { border-radius: 16px !important; padding: 24px 22px !important; height: 100%;
    box-sizing: border-box !important; display: flex !important; flex-direction: column !important; }
.st-key-cam_opt_on { border: 1.5px solid #3b6def !important; background: #f5f8ff !important; }
.st-key-cam_opt_off { border: 1px solid #e9ecf2 !important; background: #fff !important; }
.st-key-cam_opt_on [data-testid="stElementContainer"]:last-child,
.st-key-cam_opt_off [data-testid="stElementContainer"]:last-child { margin-top: auto !important; }
.cam-top { display: flex; align-items: center; gap: 14px; }
.cam-top .ic { width: 52px; height: 52px; border-radius: 14px; display: flex; align-items: center; justify-content: center;
    font-size: 24px; flex-shrink: 0; }
.cam-top .nm { font-size: 17px; font-weight: 800; color: #111827; display: flex; align-items: center; gap: 8px; }
.cam-top .tg { font-size: 11px; font-weight: 800; color: #2f5bd8; background: #fff; border-radius: 999px; padding: 3px 9px; }
.cam-top .ds { font-size: 13px; color: #6b7280; margin-top: 3px; }
.cam-list { margin: 18px 0 22px; padding: 16px 0 0; border-top: 1px solid #eef0f4; display: flex; flex-direction: column; gap: 9px; }
.cam-list div { font-size: 13.5px; color: #374151; display: flex; gap: 8px; align-items: center; }
.cam-list i { font-size: 14px; }
.st-key-cam_opt_on button, .st-key-cam_opt_off button { width: 100% !important; padding: 12px 0 !important;
    border-radius: 12px !important; min-height: 0 !important; }
.st-key-cam_opt_on button p, .st-key-cam_opt_off button p { font-size: 14.5px !important; font-weight: 700 !important; }
.st-key-cam_opt_off button { background: #fff !important; border: 1px solid #e5e7eb !important; }
.st-key-btn_back_cam { margin-top: 6px; }
.st-key-btn_back_cam button { background: transparent !important; border: none !important; padding: 8px 0 !important;
    min-height: 0 !important; box-shadow: none !important; }
.st-key-btn_back_cam button p { font-size: 14px !important; font-weight: 700 !important; color: #4b5563 !important; }
@media (max-width: 760px) {
    .st-key-cam_choice_card [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
}
</style>""", unsafe_allow_html=True)

st.markdown(
    steps_html(3)
    + '<div class="su-head"><div class="t">면접 방식을 선택해주세요</div>'
    '<div class="sub">웹캠을 켜면 시선 처리·발화 속도까지 분석해드려요.</div></div>',
    unsafe_allow_html=True,
)


def _option_html(icon: str, icon_style: str, name: str, tag: str, desc: str, items: list[str], check_color: str) -> str:
    tag_html = f'<span class="tg">{tag}</span>' if tag else ""
    rows = "".join(f'<div><i class="ph-bold ph-check" style="color:{check_color}"></i>{t}</div>' for t in items)
    return (
        f'<div class="cam-top"><span class="ic" style="{icon_style}"><i class="ph-fill {icon}"></i></span>'
        f'<div><div class="nm">{name}{tag_html}</div><div class="ds">{desc}</div></div></div>'
        f'<div class="cam-list">{rows}</div>'
    )


with st.container(key="cam_choice_card"):
    st.markdown(
        '<div class="su-sh"><span class="n">01</span>웹캠 사용</div>'
        '<div class="su-sd">답변 내용·논리성 평가는 두 방식 모두 같아요</div>',
        unsafe_allow_html=True,
    )
    col_on, col_off = st.columns(2)
    with col_on:
        with st.container(key="cam_opt_on"):
            st.markdown(_option_html(
                "ph-video-camera", "background:#3b6def;color:#fff", "웹캠 켜고 진행", "추천", "AI 분석 항목 추가",
                ["시선 처리 점수화", "발화 속도 분석", "영상 녹화 및 저장 허용"], "#3b6def",
            ), unsafe_allow_html=True)
            if st.button("카메라 & 마이크 허용하고 시작", type="primary", key="allow_btn", use_container_width=True):
                st.session_state.webcam_on = True
                st.switch_page("pages/04_면접_진행.py")
    with col_off:
        with st.container(key="cam_opt_off"):
            st.markdown(_option_html(
                "ph-video-camera-slash", "background:#f3f4f6;color:#6b7280", "웹캠 없이 진행", "", "음성·텍스트 답변만으로 평가",
                ["답변 내용·논리성 분석은 동일", "카메라·영상 녹화 없음", "얼굴 노출 없이 편안하게 진행"], "#9ca3af",
            ), unsafe_allow_html=True)
            if st.button("웹캠 없이 시작", key="skip_btn", use_container_width=True):
                st.session_state.webcam_on = False
                st.switch_page("pages/04_면접_진행.py")

if st.button("← 이전 단계", key="btn_back_cam"):
    st.switch_page("pages/031_문서업로드.py")
