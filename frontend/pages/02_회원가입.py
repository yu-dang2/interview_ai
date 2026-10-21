import requests
import streamlit as st
from utils.brand import FAVICON, logo_img
from utils.paths import resource
from utils.state import init_session, set as state_set
from utils.ui import show_error
from utils import api

st.set_page_config(
    page_title="회원가입 | intro",
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
    background: white !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 6px !important;
    height: 48px !important;
    font-size: 14px !important;
    color: #111827 !important;
    padding: 0 44px 0 13px !important;
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
    border-radius: 6px !important;
}
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
      지금 시작하면<br>합격이 가까워집니다
    </div>
    <p style="font-size:16px;color:#dbeafe;line-height:1.75;margin:0 0 32px;">
      무료로 시작하고,<br>AI 면접 코치와 함께 준비하세요.
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


# ── 오른쪽 폼 ─────────────────────────────────────────────────────────
st.markdown("<div style='height:163px;margin:0;padding:0;'></div>", unsafe_allow_html=True)

_, form_col, _ = st.columns([15, 52, 15])

with form_col:

    st.markdown("""
    <div style="font-size:28px;font-weight:800;color:#111827;
               margin:0 0 56px;line-height:1.2;">회원가입</div>
    """, unsafe_allow_html=True)

    with st.form("signup_form", border=False):
        name = st.text_input("이름", placeholder="홍길동", key="signup_name")

        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

        email = st.text_input("이메일", placeholder="example@email.com", key="signup_email")

        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

        password = st.text_input("비밀번호", placeholder="비밀번호를 입력하세요",
                                 type="password", key="signup_pw")

        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

        password_confirm = st.text_input("비밀번호 확인", placeholder="비밀번호를 다시 입력하세요",
                                         type="password", key="signup_pw_confirm")

        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

        submitted = st.form_submit_button("회원가입", type="primary", use_container_width=True)

    if submitted:
        if not name or not email or not password or not password_confirm:
            show_error("모든 항목을 입력해주세요.")
        elif len(password) < 8: 
            show_error("비밀번호는 8자 이상이어야 합니다.")
        elif len(password.encode("utf-8")) > 72: 
            show_error(api.PASSWORD_TOO_LONG_MSG)
        elif password != password_confirm:
            show_error("비밀번호가 일치하지 않습니다.")
        else:
            try:
                api.register(name, email, password)
                resp = api.login(email, password)
                state_set("access_token", resp["access_token"])
                state_set("user_name", name)
                state_set("user_email", email)
                state_set("is_logged_in", True)
                st.switch_page("pages/03_면접_환경설정.py")
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 409:
                    show_error("이미 가입된 이메일입니다.")
                else:
                    show_error(api.error_detail(e, "회원가입에 실패했습니다."))
            except Exception:
                show_error("회원가입에 실패했습니다. 다시 시도해주세요.")

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    st.markdown("""
    <p style="text-align:center;font-size:13px;color:#9ca3af;margin:0;">
      이미 계정이 있으신가요?&nbsp;→&nbsp;
      <a href="/%EB%A1%9C%EA%B7%B8%EC%9D%B8"
         style="color:#3b6def;font-weight:600;text-decoration:none;">
        로그인
      </a>
    </p>
    """, unsafe_allow_html=True)
