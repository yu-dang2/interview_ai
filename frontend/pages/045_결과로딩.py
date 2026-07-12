import time
import streamlit as st
from utils.state import init_session

st.set_page_config(
    page_title="결과 분석 중 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()

st.markdown("""<style>
[data-testid="stAppViewContainer"] { background: #f3f4f6 !important; }
[data-testid="stMain"]             { background: #f3f4f6 !important; }
[data-testid="stMainBlockContainer"] { padding: 0 !important; }
[data-testid="stVerticalBlock"]    { gap: 0 !important; }
header, footer, [data-testid="stSidebar"] { display: none !important; }

@keyframes spin {
  to { transform: rotate(360deg); }
}
.loading-spinner {
  width: 52px; height: 52px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b6def;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
  margin: 0 auto 28px;
}
</style>""", unsafe_allow_html=True)

st.markdown("""
<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:#f3f4f6;">
  <div style="background:white;border-radius:20px;padding:52px 56px;
              box-shadow:0 4px 24px rgba(0,0,0,0.08);text-align:center;max-width:480px;width:90%;">
    <div class="loading-spinner"></div>
    <div style="font-size:20px;font-weight:700;color:#1f1f1f;margin-bottom:12px;">
      결과를 분석하고 있습니다
    </div>
    <div style="font-size:14px;color:#6b7280;line-height:1.7;margin-bottom:32px;">
      면접 답변을 AI가 종합 분석 중입니다.<br>잠시만 기다려 주세요.
    </div>
    <div style="text-align:left;display:inline-block;">
      <div style="font-size:13px;color:#374151;margin-bottom:10px;display:flex;align-items:center;gap:10px;">
        <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#3b6def;flex-shrink:0;"></span>
        답변 내용 분석 중...
      </div>
      <div style="font-size:13px;color:#374151;margin-bottom:10px;display:flex;align-items:center;gap:10px;">
        <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#3b6def;flex-shrink:0;"></span>
        역량 점수 산출 중...
      </div>
      <div style="font-size:13px;color:#374151;display:flex;align-items:center;gap:10px;">
        <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#3b6def;flex-shrink:0;"></span>
        개선 피드백 생성 중...
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

time.sleep(2.5)
st.session_state.pop("webcam_result_ready", None)
st.switch_page("pages/05_결과리포트.py")
