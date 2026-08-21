import streamlit as st


@st.dialog("안내")
def _notice_dialog(message: str):
    st.markdown(
        f'<div style="font-size:var(--text-md);color:var(--gray-700);line-height:1.7;'
        f'margin-bottom:var(--space-5);word-break:keep-all;">{message}</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="_notice_dialog_actions"):
        if st.button("확인", type="primary", key="_notice_dialog_confirm"):
            st.rerun()


def show_error(message: str):
    st.markdown(
        '<style>'
        '[data-testid="stDialog"] { background: rgba(17,24,39,0.45) !important; }'
        '[data-testid="stDialog"] > div { border-radius: var(--radius-xl) !important; }'
        '[data-testid="stDialog"] h2 { '
        'font-size: var(--text-xl) !important; font-weight: 700 !important; '
        'color: var(--gray-900) !important; }'
        '.st-key-_notice_dialog_actions { display:flex !important; flex-direction:row !important; justify-content:flex-end !important; }'
        '.st-key-_notice_dialog_actions button { border-radius: var(--radius-md) !important; }'
        '</style>',
        unsafe_allow_html=True,
    )
    _notice_dialog(message)
