"""로그인 · 회원가입 화면이 같이 쓰는 "Google로 로그인" 버튼.

버튼은 Streamlit 버튼이 아니라 링크다. 백엔드 /auth/google 이 구글 화면으로 302 를
걸어 주므로 브라우저가 그 주소로 직접 이동해야 한다. (fetch 로는 리디렉션을 못 따라간다)
구글 로그인을 마치면 백엔드가 /?login=<코드> 로 돌려보내고 app.py 가 나머지를 처리한다.
"""

import requests
import streamlit as st

from utils import api

_GOOGLE_CSS = """<style>
.google-divider {
    display:flex; align-items:center; gap:12px;
    margin:0; font-size:12px; color:#9ca3af;
}
.google-divider::before, .google-divider::after {
    content:""; flex:1; height:1px; background:#e5e7eb;
}
a.google-login {
    display:flex; align-items:center; justify-content:center; gap:10px;
    width:100%; height:48px; box-sizing:border-box;
    background:#ffffff; border:1px solid #e5e7eb;
    font-size:14px; font-weight:600; color:#111827 !important;
    text-decoration:none !important;
    transition:background .15s, border-color .15s;
}
a.google-login:hover { background:#f9fafb; border-color:#d1d5db; }
a.google-login svg { width:18px; height:18px; flex-shrink:0; }
</style>"""

_GOOGLE_G = """<svg viewBox="0 0 48 48" aria-hidden="true">
<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
</svg>"""


@st.cache_data(ttl=300, show_spinner=False)
def _google_login_ready() -> bool:
    """백엔드에 구글 키가 들어 있는지 확인한다.

    키가 없으면 /auth/google 이 501 JSON 을 돌려줘서, 버튼을 그대로 누르면
    빈 화면에 오류 글자만 보인다. 그래서 미리 물어보고, 준비가 안 됐으면
    버튼이 첫 화면의 안내 문구(login_error=not_configured)로 가게 한다.
    """
    try:
        res = requests.get(f"{api.BASE_URL}/auth/google", allow_redirects=False, timeout=3)
        return res.status_code in (302, 307)
    except requests.exceptions.RequestException:
        return False


def google_login_button(label: str = "Google로 로그인", radius: int = 8) -> None:
    """"또는" 구분선과 구글 버튼을 그린다. radius 는 화면의 입력칸 모서리에 맞춘다."""
    # 버튼은 브라우저가 직접 이동하는 주소라 PUBLIC_BASE_URL 을 쓴다.
    # (API_BASE_URL 은 컨테이너끼리 부르는 주소라 브라우저에서는 열리지 않는다)
    href = (
        f"{api.PUBLIC_BASE_URL}/auth/google" if _google_login_ready()
        else "/?login_error=not_configured"
    )
    st.markdown(_GOOGLE_CSS, unsafe_allow_html=True)
    st.markdown(f"""
    <div style="height:8px"></div>
    <div class="google-divider">또는</div>
    <div style="height:24px"></div>
    <a class="google-login" href="{href}" target="_self" style="border-radius:{radius}px;">
      {_GOOGLE_G}<span>{label}</span>
    </a>
    <div style="height:32px"></div>
    """, unsafe_allow_html=True)
