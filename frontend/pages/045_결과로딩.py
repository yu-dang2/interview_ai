import time
import threading
import streamlit as st
from utils.brand import FAVICON
from utils.state import init_session, get, set as state_set, mark_session_expired
from utils import api

st.set_page_config(
    page_title="결과 분석 중 | intro",
    page_icon=FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()

st.markdown("""<style>
[data-testid="stAppViewContainer"] { background: #f8fafc !important; }
[data-testid="stMain"]             { background: #f8fafc !important; }
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

_webcam_on = bool(get("webcam_on"))

_STAGES = ["답변 내용 분석 중...", "역량 점수 산출 중...", "개선 피드백 생성 중..."]
_STAGE_AT = [0.0, 2.2, 4.4]

if _webcam_on:
    _STAGES = _STAGES + ["시선·표정 분석 중..."]
    _STAGE_AT = _STAGE_AT + [6.6]


def _loading_html(stage_idx: int) -> str:
    rows = ""
    for i, label in enumerate(_STAGES):
        if i < stage_idx:
            dot = (
                '<span style="display:inline-flex;align-items:center;justify-content:center;'
                'width:14px;height:14px;border-radius:50%;background:#3b6def;color:white;'
                'font-size:9px;flex-shrink:0;"><i class="ph-bold ph-check" style="font-size:9px;"></i></span>'
            )
            text_style = "color:#9ca3af;"
        elif i == stage_idx:
            dot = (
                '<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
                'background:#3b6def;flex-shrink:0;"></span>'
            )
            text_style = "color:#374151;"
        else:
            dot = (
                '<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
                'background:#e5e7eb;flex-shrink:0;"></span>'
            )
            text_style = "color:#9ca3af;"
        rows += (
            f'<div style="font-size:13px;margin-bottom:10px;display:flex;align-items:center;'
            f'gap:10px;{text_style}">{dot}{label}</div>'
        )
    heading = _STAGES[stage_idx]
    return (
        '<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:#f8fafc;">'
        '<div style="background:white;border-radius:20px;padding:52px 56px;'
        'box-shadow:0 4px 24px rgba(0,0,0,0.08);text-align:center;max-width:480px;width:90%;">'
        '<div class="loading-spinner"></div>'
        f'<div style="font-size:20px;font-weight:700;color:#111827;margin-bottom:12px;">{heading}</div>'
        '<div style="font-size:14px;color:#6b7280;line-height:1.7;margin-bottom:32px;">'
        '면접 답변을 AI가 종합 분석 중입니다.<br>잠시만 기다려 주세요.</div>'
        f'<div style="text-align:left;display:inline-block;">{rows}</div>'
        '</div></div>'
    )


session_id = get("session_id")

if session_id and not get("result"):
    _access_token = st.session_state.get("access_token", "")
    _result: dict = {}

    def _fetch_result_worker():
        try:
            _result["data"] = api.get_result(session_id, access_token=_access_token)
        except Exception as e:
            _result["error"] = e

    _thread = threading.Thread(target=_fetch_result_worker, daemon=True)
    _thread.start()

    _placeholder = st.empty()
    _t0 = time.time()
    while _thread.is_alive():
        _elapsed = time.time() - _t0
        _stage = 0
        for i, at in enumerate(_STAGE_AT):
            if _elapsed >= at:
                _stage = i
        _placeholder.markdown(_loading_html(_stage), unsafe_allow_html=True)
        time.sleep(0.2)
    _thread.join()
    _placeholder.empty()

    if "data" in _result:
        state_set("result", _result["data"])
    elif isinstance(_result.get("error"), api.SessionExpiredError):
        mark_session_expired()
else:
    time.sleep(0.4)

st.session_state.pop("webcam_result_ready", None)
st.switch_page("pages/05_결과리포트.py")
