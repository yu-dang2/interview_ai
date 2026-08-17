import requests
import streamlit as st
from utils.paths import resource
from utils.state import init_session, set as state_set
from utils import api

st.set_page_config(
    page_title="회원가입 | intro",
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

html, body { overflow:hidden; height:100vh; margin:0; padding:0; }
[data-testid="stAppViewContainer"],
[data-testid="stMain"] { height:100vh !important; overflow:hidden !important; }

.main .block-container,
[data-testid="stMainBlockContainer"] {
    margin-left: 43% !important;
    width: 57% !important;
    max-width: 57% !important;
    height: 100vh !important;
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
    border: 1px solid #e5e7ea !important;
    border-radius: 6px !important;
    height: 48px !important;
    font-size: 14px !important;
    color: #111827 !important;
    padding: 0 44px 0 13px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #3b6def !important;
    box-shadow: 0 0 0 3px rgba(59,109,239,0.15) !important;
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
CHECK = """<svg width="22" height="22" viewBox="0 0 22 22" fill="none">
  <circle cx="11" cy="11" r="11" fill="rgba(255,255,255,0.2)"/>
  <path d="M7 11l2.8 2.8 5.2-5.2" stroke="white" stroke-width="2.2"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

st.markdown(f"""
<div style="
    position:fixed; top:0; left:0;
    width:43%; height:100vh;
    background:#3b6def;
    z-index:100; overflow:hidden;
    padding:60px; box-sizing:border-box;
    display:flex; flex-direction:column; justify-content:space-between;
">
  <div style="position:absolute;border-radius:50%;
              width:400px;height:400px;left:-80px;top:100px;
              background:rgba(255,255,255,0.08);pointer-events:none;"></div>
  <div style="position:absolute;border-radius:50%;
              width:300px;height:300px;left:200px;top:500px;
              background:rgba(255,255,255,0.06);pointer-events:none;"></div>

  <a href="/" target="_self" style="position:relative;z-index:1;font-size:22px;font-weight:700;
            color:white;text-decoration:none;">intro</a>

  <div style="position:relative;z-index:1;">
    <div style="font-size:34px;font-weight:800;color:white;
               line-height:1.4;margin:0 0 16px;">
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
            st.error("모든 항목을 입력해주세요.")
        elif password != password_confirm:
            st.error("비밀번호가 일치하지 않습니다.")
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
                    st.error("이미 가입된 이메일입니다.")
                else:
                    status = e.response.status_code if e.response is not None else "?"
                    st.error(f"회원가입에 실패했습니다. (서버 오류: {status})")
            except Exception:
                st.error("회원가입에 실패했습니다. 다시 시도해주세요.")

    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;margin:12px 0 24px;">
      <div style="flex:1;height:1px;background:#e5e7ea;"></div>
      <span style="font-size:11px;color:#9ca3a8;white-space:nowrap;">또는</span>
      <div style="flex:1;height:1px;background:#e5e7ea;"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="display:flex;gap:16px;margin-bottom:24px;">
      <button style="flex:1;height:48px;border-radius:8px;border:none;
                     background:#fee500;color:#191919;font-size:13px;
                     font-weight:600;cursor:pointer;font-family:inherit;">
        카카오로 시작하기
      </button>
      <button style="flex:1;height:48px;border-radius:8px;
                     border:1px solid #e5e7ea;background:white;color:#6b7280;
                     font-size:13px;cursor:pointer;font-family:inherit;">
        Google로 시작하기
      </button>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <p style="text-align:center;font-size:13px;color:#9ca3a8;margin:0;">
      이미 계정이 있으신가요?&nbsp;→&nbsp;
      <a href="/%EB%A1%9C%EA%B7%B8%EC%9D%B8"
         style="color:#3b6def;font-weight:600;text-decoration:none;">
        로그인
      </a>
    </p>
    """, unsafe_allow_html=True)
