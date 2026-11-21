import streamlit as st

_DIALOG_STYLE = (
    '<style>'
    '[data-testid="stDialog"] { background: rgba(17,24,39,0.45) !important; }'
    '[data-testid="stDialog"] > div { border-radius: var(--radius-xl) !important; }'
    '[data-testid="stDialog"] h2 { '
    'font-size: var(--text-xl) !important; font-weight: 700 !important; '
    'color: var(--gray-900) !important; }'
    '.st-key-_notice_dialog_actions { display:flex !important; flex-direction:row !important; justify-content:flex-end !important; }'
    '.st-key-_notice_dialog_actions button { border-radius: var(--radius-md) !important; }'
    '</style>'
)


@st.dialog("안내")
def _notice_dialog(message: str, dismiss_key: str | None):
    st.markdown(
        f'<div style="font-size:var(--text-md);color:var(--gray-700);line-height:1.7;'
        f'margin-bottom:var(--space-8);word-break:keep-all;">{message}</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="_notice_dialog_actions"):
        if st.button("확인", type="primary", key="_notice_dialog_confirm"):
            if dismiss_key:
                st.session_state[dismiss_key] = True
            st.rerun()


def show_error(message: str):
    st.markdown(_DIALOG_STYLE, unsafe_allow_html=True)
    _notice_dialog(message, None)


@st.dialog("안내")
def _session_expired_dialog():
    st.markdown(
        '<div style="font-size:var(--text-md);color:var(--gray-700);line-height:1.7;'
        'margin-bottom:var(--space-8);word-break:keep-all;">'
        '로그인이 만료되었습니다. 다시 로그인해주세요.</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="_notice_dialog_actions"):
        if st.button("로그인 화면으로 이동", type="primary", key="_session_expired_confirm"):
            st.switch_page("pages/01_로그인.py")


def show_session_expired():
    st.markdown(_DIALOG_STYLE, unsafe_allow_html=True)
    _session_expired_dialog()


def show_error_once(message: str, key: str):
    dismiss_key = f"_notice_once_dismissed_{key}"
    if st.session_state.get(dismiss_key):
        return False
    st.markdown(_DIALOG_STYLE, unsafe_allow_html=True)
    _notice_dialog(message, dismiss_key)
    return True
