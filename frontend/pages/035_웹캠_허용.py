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
    width: 780px !important;
    max-width: 780px !important;
    position: relative !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
}

.wc-card {
    border: 1.5px solid #e5e7eb;
    border-radius: 12px;
    padding: 22px 20px;
    margin-bottom: var(--space-10);
    box-sizing: border-box;
}
.wc-card-highlight { border-color: #3b6def; background: #f7f9ff; }

[data-testid="stBaseButton-primary"] {
    width: 100% !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: var(--space-3) var(--space-4) !important;
    white-space: nowrap !important;
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
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: var(--space-3) var(--space-4) !important;
}

.st-key-allow_btn, .st-key-skip_btn { margin-top: var(--space-4) !important; }
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
            '<p style="text-align:center;font-size:22px;font-weight:700;'
            'color:#1f1f1f;margin:0 0 6px;">면접 방식을 선택해주세요</p>'
            '<p style="text-align:center;font-size:14px;color:#6b7280;margin:0 0 28px;">'
            '웹캠을 켜면 시선 처리·발화 속도까지 분석해드려요.</p>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<style>.st-key-webcam_choice_row [data-testid="stHorizontalBlock"] '
            '{ gap: var(--space-6) !important; }</style>',
            unsafe_allow_html=True,
        )
        with st.container(key="webcam_choice_row"):
            col_on, col_off = st.columns(2, gap="medium")

        with col_on:
            st.markdown(
                '<div class="wc-card wc-card-highlight">'
                '<div style="display:flex;justify-content:center;margin-bottom:14px;">'
                '<svg width="52" height="52" viewBox="0 0 88 88" fill="none">'
                '<circle cx="44" cy="44" r="44" fill="#eef2ff"/>'
                '<rect x="23" y="30" width="42" height="30" rx="5" fill="#3b6def"/>'
                '<rect x="38" y="23" width="12" height="9" rx="3" fill="#3b6def"/>'
                '<circle cx="44" cy="45" r="8" fill="white"/>'
                '<circle cx="44" cy="45" r="4" fill="#3b6def"/>'
                '</svg></div>'
                '<p style="text-align:center;font-size:16px;font-weight:700;color:#1f1f1f;margin:0 0 4px;">웹캠 켜고 진행</p>'
                '<p style="text-align:center;font-size:12px;color:#3b6def;font-weight:600;margin:0 0 16px;">AI 분석 항목 추가 · 추천</p>'
                '<div style="height:34px;background:white;border-radius:8px;display:flex;align-items:center;padding:0 12px;margin-bottom:8px;">'
                '<div style="width:6px;height:6px;border-radius:50%;background:#3b6def;margin-right:9px;flex-shrink:0;"></div>'
                '<span style="font-size:12px;font-weight:500;color:#1a3380;">시선 처리 점수화</span></div>'
                '<div style="height:34px;background:white;border-radius:8px;display:flex;align-items:center;padding:0 12px;margin-bottom:8px;">'
                '<div style="width:6px;height:6px;border-radius:50%;background:#f59e0b;margin-right:9px;flex-shrink:0;"></div>'
                '<span style="font-size:12px;font-weight:500;color:#1a3380;">발화 속도 분석</span></div>'
                '<div style="height:34px;background:white;border-radius:8px;display:flex;align-items:center;padding:0 12px;margin-bottom:18px;">'
                '<div style="width:6px;height:6px;border-radius:50%;background:#ef4444;margin-right:9px;flex-shrink:0;"></div>'
                '<span style="font-size:12px;font-weight:500;color:#1a3380;">영상 녹화 및 저장 허용</span></div>'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button("카메라 & 마이크 허용하고 시작", type="primary", key="allow_btn", use_container_width=True):
                st.session_state.webcam_on = True
                st.switch_page("pages/04_면접_진행.py")

        with col_off:
            st.markdown(
                '<div class="wc-card">'
                '<div style="display:flex;justify-content:center;margin-bottom:14px;">'
                '<svg width="52" height="52" viewBox="0 0 88 88" fill="none">'
                '<circle cx="44" cy="44" r="44" fill="#f3f4f6"/>'
                '<rect x="23" y="30" width="42" height="30" rx="5" fill="#9ca3af"/>'
                '<rect x="38" y="23" width="12" height="9" rx="3" fill="#9ca3af"/>'
                '<circle cx="44" cy="45" r="8" fill="white"/>'
                '<line x1="20" y1="20" x2="68" y2="68" stroke="#9ca3af" stroke-width="4"/>'
                '</svg></div>'
                '<p style="text-align:center;font-size:16px;font-weight:700;color:#1f1f1f;margin:0 0 4px;">웹캠 없이 진행</p>'
                '<p style="text-align:center;font-size:12px;color:#6b7280;font-weight:600;margin:0 0 16px;">음성·텍스트 답변만으로 평가</p>'
                '<div style="height:34px;background:#f9fafb;border-radius:8px;display:flex;align-items:center;padding:0 12px;margin-bottom:8px;">'
                '<div style="width:6px;height:6px;border-radius:50%;background:#9ca3af;margin-right:9px;flex-shrink:0;"></div>'
                '<span style="font-size:12px;font-weight:500;color:#4b5563;">답변 내용·논리성 분석은 동일</span></div>'
                '<div style="height:34px;background:#f9fafb;border-radius:8px;display:flex;align-items:center;padding:0 12px;margin-bottom:8px;">'
                '<div style="width:6px;height:6px;border-radius:50%;background:#9ca3af;margin-right:9px;flex-shrink:0;"></div>'
                '<span style="font-size:12px;font-weight:500;color:#4b5563;">카메라·영상 녹화 없음</span></div>'
                '<div style="height:34px;background:#f9fafb;border-radius:8px;display:flex;align-items:center;padding:0 12px;margin-bottom:18px;">'
                '<div style="width:6px;height:6px;border-radius:50%;background:#9ca3af;margin-right:9px;flex-shrink:0;"></div>'
                '<span style="font-size:12px;font-weight:500;color:#4b5563;">얼굴 노출 없이 편안하게 진행</span></div>'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button("웹캠 없이 시작", key="skip_btn", use_container_width=True):
                st.session_state.webcam_on = False
                st.switch_page("pages/04_면접_진행.py")
