import requests
import streamlit as st
from utils.brand import FAVICON, logo_img
from utils.paths import resource
from utils.state import init_session, set as state_set
from utils.ui import show_error
from utils import api

st.set_page_config(
    page_title="로그인 | intro",
    page_icon=FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()

css = resource("styles/global.css").read_text(encoding="utf-8")
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.markdown("""
<style>

#MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stSidebarNav"] { display:none !important; }
header, [data-testid="stToolbar"] { visibility:hidden !important; height:0 !important; }
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stExpandSidebarButton"] { display:none !important; }

html, body { overflow-x:hidden; min-height:100vh; margin:0; padding:0; }
[data-testid="stAppViewContainer"],
[data-testid="stMain"] { min-height:100vh !important; overflow-y:auto !important; overflow-x:hidden !important; }

.main .block-container,
[data-testid="stMainBlockContainer"] {
    margin-left: 43% !important;
    width: 57% !important;
    max-width: 57% !important;
    min-height: 100vh !important;
    padding: 0 !important;
    background: white !important;
    box-sizing: border-box !important;
}

[data-testid="stVerticalBlock"]  { gap:0 !important; }
[data-testid="stHorizontalBlock"] { gap:0 !important; }

[data-testid="stTextInput"] { margin:0 !important; padding:0 0 6px 0 !important; overflow:visible !important; }
[data-testid="stTextInput"] > div { padding:0 !important; margin:0 !important; overflow:visible !important; }
[data-testid="stTextInput"] label,
[data-testid="stTextInput"] label p {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #374151 !important;
    margin: 0 0 6px !important;
    padding: 0 !important;
}
[data-testid="stTextInput"] input {
    background: #f9fafb !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    height: 48px !important;
    font-size: 14px !important;
    color: #111827 !important;
    padding: 0 44px 0 16px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #3b6def !important;
    box-shadow: 0 0 0 3px rgba(30,50,38,0.15) !important;
    outline: none !important;
}
[data-testid="stTextInput"] > div > div {
    position: relative !important;
    overflow: visible !important;
}
[data-testid="stTextInput"] button {
    position: absolute !important;
    right: 12px !important;
    top: 60% !important;
    transform: translateY(-50%) !important;
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    cursor: pointer !important;
    color: #9ca3af !important;
    display: flex !important;
    align-items: center !important;
    z-index: 1 !important;
}

[data-testid="stBaseButton-primary"] {
    width: 100% !important;
    height: 48px !important;
    border-radius: 8px !important;
}

[data-testid="stPageLink"] { display:flex !important; justify-content:center !important; margin:0 !important; padding:0 !important; }
[data-testid="stPageLink"] a { font-size:13px !important; font-weight:600 !important; color:#3b6def !important; text-decoration:none !important; }
[data-testid="stPageLink"] svg { display:none !important; }
</style>
""", unsafe_allow_html=True)


# ── 왼쪽 패널 ───────────────────────────────────────
CHECK = """<div style="width:22px;height:22px;border-radius:50%;background:rgba(255,255,255,0.2);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
  <i class="ph-bold ph-check" style="font-size:13px;color:white;"></i>
</div>"""

st.markdown(f"""
<div style="
    position:fixed; top:0; left:0;
    width:43%; height:100vh;
    background:#3b6def;
    z-index:100; overflow:hidden;
    padding:60px; box-sizing:border-box;
    display:flex; flex-direction:column; justify-content:space-between;
">
  <a href="/" target="_self" aria-label="intro 홈" style="position:relative;z-index:1;display:inline-block;
            text-decoration:none;">{logo_img(30, white=True)}</a>

  <div style="position:relative;z-index:1;">
    <div style="font-size:clamp(24px, 2.6vw, 34px);font-weight:800;color:white;
               line-height:1.4;margin:0 0 16px;word-break:keep-all;overflow-wrap:break-word;">
      AI와 함께하는<br>스마트한 취업 준비
    </div>
    <p style="font-size:16px;color:#dbeafe;line-height:1.75;margin:0 0 32px;">
      이력서부터 면접까지,<br>당신의 합격을 AI가 코치합니다.
    </p>
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div style="display:flex;align-items:center;gap:12px;">
        {CHECK}<span style="font-size:14px;color:white;">이력서 AI 분석 &amp; 최적화</span>
      </div>
      <div style="display:flex;align-items:center;gap:12px;">
        {CHECK}<span style="font-size:14px;color:white;">LangGraph 꼬리질문 면접</span>
      </div>
      <div style="display:flex;align-items:center;gap:12px;">
        {CHECK}<span style="font-size:14px;color:white;">웹캠 시선 처리 분석</span>
      </div>
    </div>
  </div>

  <div></div>
</div>
""", unsafe_allow_html=True)


# ── 오른쪽: 상단 여백 + 중앙 폼 ──────────────────────────────────────

st.markdown("<div style='height:163px;margin:0;padding:0;'></div>", unsafe_allow_html=True)

_, form_col, _ = st.columns([15, 52, 15])

with form_col:

    st.markdown("""
    <div style="font-size:28px;font-weight:800;color:#111827;
               margin:0 0 60px;line-height:1.2;">로그인</div>
    """, unsafe_allow_html=True)

    with st.form("login_form", border=False):
        email = st.text_input("이메일", placeholder="example@email.com",
                              key="login_email")

        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

        password = st.text_input("비밀번호", placeholder="비밀번호를 입력하세요",
                                 type="password", key="login_pw")

        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

        submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

    if submitted:
        if not email or not password:
            show_error("이메일과 비밀번호를 입력해주세요.")
        else:
            try:
                resp = api.login(email, password)
                state_set("access_token", resp["access_token"])
                state_set("is_logged_in", True)
                state_set("user_email", email)
                st.switch_page("pages/03_면접_환경설정.py")
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    show_error("이메일 또는 비밀번호가 올바르지 않습니다.")
                else:
                    show_error(api.error_detail(e, "로그인에 실패했습니다."))
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                show_error("서버에 연결할 수 없습니다. 백엔드 서버가 켜져 있는지 확인해주세요.")
            except Exception as e:
                show_error(f"알 수 없는 오류가 발생했습니다: {e}")

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # 회원가입 링크
    st.markdown("""
    <p style="text-align:center;font-size:13px;color:#9ca3af;margin:0;">
      계정이 없으신가요?&nbsp;
      <a href="/%ED%9A%8C%EC%9B%90%EA%B0%80%EC%9E%85"
         style="color:#3b6def;font-weight:600;text-decoration:none;">
        → 무료 회원가입
      </a>
    </p>
    """, unsafe_allow_html=True)
