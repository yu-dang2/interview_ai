import streamlit as st
import streamlit.components.v1 as components
from utils.paths import resource

NAV_ITEMS = [
    ("면접 시작",     "/%EB%A9%B4%EC%A0%91_%ED%99%98%EA%B2%BD%EC%84%A4%EC%A0%95"),
    ("결과 리포트",   "/%EA%B2%B0%EA%B3%BC%EB%A6%AC%ED%8F%AC%ED%8A%B8"),
    ("피드백 보고서", "/%ED%94%BC%EB%93%9C%EB%B0%B1%EB%B3%B4%EA%B3%A0%EC%84%9C"),
    ("이력서 최적화", "/%EC%9D%B4%EB%A0%A5%EC%84%9C%EC%B5%9C%EC%A0%81%ED%99%94"),
    ("마이페이지",    "/%EB%A7%88%EC%9D%B4%ED%8E%98%EC%9D%B4%EC%A7%80"),
]

LOGOUT_ICON = (
    '<svg width="16" height="16" viewBox="0 0 17 17" fill="none">'
    '<path d="M7 1.5L2 1.5L2 15.5L7 15.5" stroke="#dc2626" stroke-width="1.8"'
    ' stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M6 8.5L15 8.5M11 5L15 8.5L11 12" stroke="#dc2626" stroke-width="1.8"'
    ' stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
)

_SIDEBAR_CSS = """<style>
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stExpandSidebarButton"] { display:none !important; }
header, [data-testid="stToolbar"] { visibility:hidden !important; height:0 !important; }
#MainMenu, footer { display:none !important; }
[data-testid="stAppViewContainer"] { background:var(--bg) !important; }
[data-testid="stMain"] {
    padding-top: 60px !important;
    padding-left: 0 !important;
    box-sizing: border-box !important;
}
.main .block-container,
[data-testid="stMainBlockContainer"] {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    background: var(--bg) !important;
    box-sizing: border-box !important;
}
[data-testid="stVerticalBlock"]  { gap:0 !important; }
[data-testid="stHorizontalBlock"] { gap:0 !important; }
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondary"] {
    font-size: var(--text-md) !important;
    font-weight: 600 !important;
    font-family: 'Pretendard', -apple-system, sans-serif !important;
    padding: 0.95em 2.25em !important;
    height: auto !important;
    line-height: 1.4 !important;
    border-radius: 10px !important;
}
.intro-sidebar-root {
    height: 0 !important;
    overflow: visible !important;
    position: relative !important;
}

/* 계정 드롭다운 (마이페이지 / 로그아웃) */
.intro-account-menu summary { list-style:none; cursor:pointer; }
.intro-account-menu summary::-webkit-details-marker { display:none; }
</style>"""


def render_sidebar(active: str):
    nav_html = ""
    for label, url in NAV_ITEMS:
        is_active = label == active
        color  = "var(--blue)" if is_active else "var(--gray-500)"
        weight = "700" if is_active else "500"
        border = "border-bottom:2px solid var(--blue);" if is_active else "border-bottom:2px solid transparent;"
        nav_html += (
            f'<a href="{url}" target="_self" style="text-decoration:none;display:flex;'
            f'align-items:center;height:60px;padding:0 16px;{border}flex-shrink:0;">'
            f'<span style="font-size:13px;font-weight:{weight};color:{color};white-space:nowrap;">{label}</span>'
            '</a>'
        )

    ACCOUNT_ICON = (
        '<svg width="16" height="16" viewBox="0 0 20 20" fill="none">'
        '<circle cx="10" cy="6.5" r="3.2" stroke="#374151" stroke-width="1.6"/>'
        '<path d="M3.5 16.5c1.4-3 4-4.5 6.5-4.5s5.1 1.5 6.5 4.5" stroke="#374151" '
        'stroke-width="1.6" stroke-linecap="round"/>'
        '</svg>'
    )
    CHEVRON_ICON = (
        '<svg width="12" height="12" viewBox="0 0 12 12" fill="none">'
        '<path d="M3 4.5L6 7.5L9 4.5" stroke="#6b7280" stroke-width="1.5" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )
    mypage_url = dict(NAV_ITEMS)["마이페이지"]
    logout_html = (
        '<details class="intro-account-menu" style="position:relative;flex-shrink:0;">'
        '<summary style="display:flex;align-items:center;gap:6px;padding:6px 12px;'
        'border-radius:6px;border:1px solid var(--border);">'
        + ACCOUNT_ICON +
        '<span style="font-size:12px;font-weight:600;color:var(--gray-700);white-space:nowrap;">내 계정</span>'
        + CHEVRON_ICON +
        '</summary>'
        '<div style="position:absolute;right:0;top:38px;min-width:160px;background:white;'
        'border:1px solid var(--border);border-radius:10px;box-shadow:var(--shadow-md);'
        'overflow:hidden;z-index:600;">'
        f'<a href="{mypage_url}" target="_self" style="text-decoration:none;display:block;'
        'padding:10px 16px;font-size:13px;font-weight:500;color:var(--gray-700);">마이페이지</a>'
        '<div style="height:1px;background:var(--border);"></div>'
        '<a href="#" id="logout-link" style="text-decoration:none;display:flex;'
        'align-items:center;gap:8px;padding:10px 16px;cursor:pointer;">'
        + LOGOUT_ICON +
        '<span style="font-size:13px;font-weight:600;color:var(--red);">로그아웃</span>'
        '</a>'
        '</div>'
        '</details>'
    )

    css = resource("styles/global.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)

    st.markdown(
        "<style>.st-key-logout_proxy_btn { position:absolute; width:0; height:0; "
        "overflow:hidden; clip:rect(0,0,0,0); margin:0; padding:0; }</style>",
        unsafe_allow_html=True,
    )
    if st.button("로그아웃", key="logout_proxy_btn"):
        st.session_state["access_token"] = ""
        st.session_state["is_logged_in"] = False
        st.session_state["user_name"] = ""
        st.session_state["user_email"] = ""
        st.session_state["user_id"] = 0
        st.session_state["_logout_pending"] = True
        st.switch_page("app.py")

    components.html("""
    <script>
    (function () {
        function attach() {
            var doc = window.parent.document;
            var link = doc.getElementById('logout-link');
            var btn  = doc.querySelector('.st-key-logout_proxy_btn button');
            if (!link || !btn) { setTimeout(attach, 200); return; }
            link.onclick = function () { btn.click(); return false; };
        }
        attach();
    }());
    </script>
    """, height=0)

    html = (
        '<div class="intro-sidebar-root">'
        '<div style="position:fixed;top:0;left:0;right:0;height:60px;'
        'background:white;border-bottom:1px solid var(--border);'
        'display:flex;align-items:center;padding:0 24px;gap:20px;'
        'z-index:500;box-sizing:border-box;">'
        '<a href="/" target="_self" style="font-size:21px;font-weight:800;color:var(--blue);'
        'letter-spacing:-0.3px;text-decoration:none;flex-shrink:0;">intro</a>'
        f'<nav style="display:flex;align-items:center;gap:4px;overflow-x:auto;flex:1;min-width:0;">{nav_html}</nav>'
        + logout_html +
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
