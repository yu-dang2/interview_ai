import streamlit as st
from components.sidebar import render_sidebar
from utils.state import init_session

st.set_page_config(
    page_title="웹캠 허용 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
render_sidebar(active="면접 시작")

st.markdown("""<style>
[data-testid="stMainBlockContainer"] {
    padding: 200px 0 0 0 !important;
    background: #f8fafc !important;
    min-height: 100vh !important;
}
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stHorizontalBlock"] { gap: 0 !important; }
[data-testid="stColumn"] { padding: 0 !important; }
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] {
    width: 100% !important;
}

[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"],
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
    background: white !important;
    border: none !important;
    outline: none !important;
}

[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] {
    border-radius: 16px !important;
    box-shadow: 0px 4px 24px rgba(0,0,0,0.1) !important;
    padding: 20px !important;
    box-sizing: border-box !important;
    width: 480px !important;
    max-width: 480px !important;
    position: relative !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
}

[data-testid="stBaseButton-primary"] {
    font-size: 16px !important;
    padding: 12px 50px !important;
}
[data-testid="stBaseButton-primary"]:hover {
    background: #2d55c8 !important;
    border-color: #2d55c8 !important;
}

[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] > [data-testid="element-container"]:last-child {
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
}

[data-testid="stBaseButton-secondary"] {
    width: 100% !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #a6afbc !important;
    font-size: 13px !important;
    font-weight: 400 !important;
}
[data-testid="stBaseButton-secondary"]:hover {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #6b7280 !important;
}
[data-testid="stBaseButton-secondary"] p {
    color: inherit !important;
    font-size: 13px !important;
}
</style>""", unsafe_allow_html=True)

_, card_col, _ = st.columns([36, 50, 36])

with card_col:
    with st.container(border=True):

        st.markdown(
            '<div style="display:flex;align-items:center;justify-content:center;margin-bottom:32px;">'
            '<div style="width:10px;height:10px;border-radius:50%;background:#d9dee8;flex-shrink:0;"></div>'
            '<span style="font-size:11px;color:#6b7280;margin:0 6px 0 4px;">환경 설정</span>'
            '<div style="width:52px;height:1px;background:#d9dee8;"></div>'
            '<div style="width:10px;height:10px;border-radius:50%;background:#3b6def;flex-shrink:0;margin:0 4px;"></div>'
            '<span style="font-size:11px;font-weight:600;color:#3b6def;margin-right:6px;">웹캠 허용</span>'
            '<div style="width:52px;height:1px;background:#d9dee8;"></div>'
            '<div style="width:10px;height:10px;border-radius:50%;background:#d9dee8;flex-shrink:0;margin-left:4px;"></div>'
            '<span style="font-size:11px;color:#6b7280;margin-left:4px;">면접 시작</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div style="display:flex;justify-content:center;margin-bottom:24px;">'
            '<svg width="88" height="88" viewBox="0 0 88 88" fill="none">'
            '<circle cx="44" cy="44" r="44" fill="#eef2ff"/>'
            '<rect x="23" y="30" width="42" height="30" rx="5" fill="#3b6def"/>'
            '<rect x="38" y="23" width="12" height="9" rx="3" fill="#3b6def"/>'
            '<circle cx="44" cy="45" r="8" fill="white"/>'
            '<circle cx="44" cy="45" r="4" fill="#3b6def"/>'
            '</svg></div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<p style="text-align:center;font-size:22px;font-weight:700;'
            'color:#1f1f1f;margin:0 0 20px;">웹캠을 허용해주세요</p>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<p style="text-align:center;font-size:14px;color:#6b7280;'
            'line-height:22px;margin:0 0 28px;">'
            'AI가 면접 중 시선 처리와 발화 속도를 실시간으로<br>'
            '분석하여 더 정확한 피드백을 제공합니다.</p>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div style="height:36px;background:#eef2ff;border-radius:8px;'
            'display:flex;align-items:center;padding:0 14px;margin-bottom:12px;">'
            '<div style="width:7px;height:7px;border-radius:50%;background:#3b6def;'
            'margin-right:10px;flex-shrink:0;"></div>'
            '<span style="font-size:13px;font-weight:500;color:#1a3380;">시선 처리 점수화</span>'
            '</div>'
            '<div style="height:36px;background:#eef2ff;border-radius:8px;'
            'display:flex;align-items:center;padding:0 14px;margin-bottom:12px;">'
            '<div style="width:7px;height:7px;border-radius:50%;background:#f59e0b;'
            'margin-right:10px;flex-shrink:0;"></div>'
            '<span style="font-size:13px;font-weight:500;color:#1a3380;">발화 속도 분석</span>'
            '</div>'
            '<div style="height:36px;background:#eef2ff;border-radius:8px;'
            'display:flex;align-items:center;padding:0 14px;margin-bottom:32px;">'
            '<div style="width:7px;height:7px;border-radius:50%;background:#ef4444;'
            'margin-right:10px;flex-shrink:0;"></div>'
            '<span style="font-size:13px;font-weight:500;color:#1a3380;">영상 녹화 및 저장 허용</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        # 허용 버튼
        _bl, _bc, _br = st.columns([1, 4.5, 1])
        with _bc:
            if st.button("카메라 & 마이크 허용하기", type="primary",
                         use_container_width=True, key="allow_btn"):
                st.session_state.webcam_on = True
                st.switch_page("pages/04_면접_진행.py")

        st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)

        if st.button("웹캠 없이 면접 진행하기 →",
                     use_container_width=True, key="skip_btn"):
            st.session_state.webcam_on = False
            st.switch_page("pages/04_면접_진행.py")
