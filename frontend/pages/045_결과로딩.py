import time
import threading
import streamlit as st
from utils.brand import FAVICON
from utils.state import init_session, get, set as state_set, mark_session_expired
from utils import api
from components.loading_card import LOADING_CSS, loading_html

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

</style>""", unsafe_allow_html=True)
st.markdown(LOADING_CSS, unsafe_allow_html=True)

_webcam_on = bool(get("webcam_on"))

_STAGES = ["답변 내용 분석 중...", "역량 점수 산출 중...", "개선 피드백 생성 중..."]
_STAGE_AT = [0.0, 40.0, 80.0]

if _webcam_on:
    _STAGES = _STAGES + ["시선·표정 분석 중..."]
    _STAGE_AT = _STAGE_AT + [110.0]


def _loading_html(stage_idx: int) -> str:
    return loading_html(
        "ANALYZING",
        "면접 답변을 AI가 종합 분석 중입니다.<br>리포트가 완성되기까지 1~2분 정도 걸릴 수 있어요.",
        _STAGES, stage_idx,
        done_labels=["답변 내용 분석", "역량 점수 산출", "개선 피드백 생성", "시선·표정 분석"][:len(_STAGES)],
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
