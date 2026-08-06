import streamlit as st
import streamlit.components.v1 as components

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
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stExpandSidebarButton"] { display:none !important; }
header, [data-testid="stToolbar"] { visibility:hidden !important; height:0 !important; }
#MainMenu, footer { display:none !important; }
[data-testid="stAppViewContainer"] { background:#f8fafc !important; }
[data-testid="stMain"] {
    padding-top: 60px !important;
    padding-left: 220px !important;
    box-sizing: border-box !important;
}
.main .block-container,
[data-testid="stMainBlockContainer"] {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    background: #f8fafc !important;
    box-sizing: border-box !important;
}
[data-testid="stVerticalBlock"]  { gap:0 !important; }
[data-testid="stHorizontalBlock"] { gap:0 !important; }
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondary"] {
    font-size: 14px !important;
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
</style>"""


def render_sidebar(active: str):
    nav_html = ""
    for label, url in NAV_ITEMS:
        is_active = label == active
        if is_active:
            nav_html += (
                f'<a href="{url}" target="_self" style="text-decoration:none;display:block;position:relative;">'
                '<div style="position:absolute;right:0;top:0;'
                'width:3px;height:44px;background:#3b6def;'
                'border-radius:2px 0 0 2px;"></div>'
                '<div style="background:#eef3ff;height:44px;'
                'display:flex;align-items:center;padding:0 24px;">'
                f'<span style="font-size:13px;font-weight:700;color:#3b6def;">{label}</span>'
                '</div></a>'
            )
        else:
            nav_html += (
                f'<a href="{url}" target="_self" style="text-decoration:none;display:block;">'
                '<div style="height:44px;display:flex;align-items:center;padding:0 24px;">'
                f'<span style="font-size:13px;font-weight:400;color:#6b7280;">{label}</span>'
                '</div></a>'
            )

    logout_html = ""
    if active == "마이페이지":
        logout_html = (
            '<div>'
            '<div style="height:1px;background:#dedede;"></div>'
            '<a href="#" id="logout-link" '
            'style="text-decoration:none;display:block;cursor:pointer;">'
            '<div style="height:44px;display:flex;align-items:center;gap:10px;'
            'padding:0 24px;background:#fff7f7;">'
            + LOGOUT_ICON +
            '<span style="font-size:13px;font-weight:600;color:#dc2626;">로그아웃</span>'
            '</div></a>'
            '</div>'
        )

    st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)

    if active == "마이페이지":
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

        # 인라인 onclick은 Streamlit의 unsafe_allow_html 새니타이저가 제거하므로
        # JS에서 .onclick 프로퍼티로 나중에 붙인다.
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
        'background:white;border-bottom:1px solid #e5e7eb;'
        'display:flex;align-items:center;padding:0 24px;'
        'z-index:500;box-sizing:border-box;">'
        '<a href="/" target="_self" style="font-size:16px;font-weight:700;color:#3b6def;text-decoration:none;">intro</a>'
        '</div>'
        '<div style="position:fixed;top:60px;left:0;width:220px;'
        'height:calc(100vh - 60px);background:#fafafc;'
        'border-right:1px solid #dedede;z-index:400;'
        'box-sizing:border-box;display:flex;'
        'flex-direction:column;justify-content:space-between;">'
        f'<nav style="padding-top:4px;">{nav_html}</nav>'
        + logout_html +
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
