import math
import os
import time
import base64
import json
import threading
import html as htmlmod
import requests
import streamlit as st
from utils.brand import FAVICON
import streamlit.components.v1 as components
from utils.paths import resource
from components.sidebar import render_sidebar
from components.loading_card import LOADING_CSS, LOADING_CSS_TEXT, loading_html
from utils.state import init_session, get, set as state_set, mark_session_expired, render_session_expired_banner
from utils.ui import show_error
from utils import api

st.set_page_config(
    page_title="면접 진행 | intro",
    page_icon=FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "iv_messages" not in st.session_state and not st.session_state.get("session_id"):
    st.session_state["_suppress_session_id_restore"] = True

init_session()
render_sidebar(active="면접 시작")

if st.session_state.pop("_iv_nav_ready_consumed", False):
    st.session_state["_iv_nav_ready"] = ""

st.markdown(
    "<style>.st-key-_iv_nav_ready { position:absolute; width:0; height:0; "
    "overflow:hidden; clip:rect(0,0,0,0); margin:0; padding:0; }</style>",
    unsafe_allow_html=True,
)
_nav_ready = st.text_input(
    "_iv_nav_ready", key="_iv_nav_ready", label_visibility="collapsed"
)
if _nav_ready and _nav_ready.startswith("go:"):
    st.session_state.webcam_on = _nav_ready.split(":", 1)[1] == "1"
    # 영상 업로드는 브라우저에서 백그라운드로 계속되므로, 결과 리포트가 이 세션의 영상을
    # 아직 못 찾으면(404) "없음" 대신 "저장 중"으로 기다리게 표시해 둔다.
    if st.session_state.webcam_on:
        st.session_state["_video_upload_pending_sid"] = get("session_id")
    st.session_state["_iv_nav_ready_consumed"] = True
    st.switch_page("pages/045_결과로딩.py")

if "iv_messages" not in st.session_state:
    session_id = get("session_id")
    first_q    = get("first_question")

    if not session_id:
        resume_id = get("resume_id") or 0
        jd_id     = get("jd_id") or 0
        persona   = get("interviewer_style") or "기술 리드"
        st.markdown("""<style>
        [data-testid="stAppViewContainer"] { background: #f8fafc !important; }
        [data-testid="stMain"]             { background: #f8fafc !important; }
        [data-testid="stMainBlockContainer"] { padding: 0 !important; }
        [data-testid="stVerticalBlock"]    { gap: 0 !important; }
        header, footer, [data-testid="stSidebar"] { display: none !important; }
        </style>""", unsafe_allow_html=True)
        st.markdown(LOADING_CSS, unsafe_allow_html=True)
        _IV_STAGE_KEYS   = ["parsing", "matching", "generating"]
        _IV_PREP_STAGES  = ["이력서·채용공고 읽는 중...", "직무 적합도 분석 중...", "맞춤 질문 만드는 중..."]

        def _iv_prep_html(stage_idx: int) -> str:
            return loading_html(
                "INTERVIEW READY",
                "이력서와 채용공고를 분석해 맞춤 질문을 만들고 있어요.<br>잠시만 기다려 주세요.",
                _IV_PREP_STAGES, stage_idx, show_progress=True,
                done_labels=["이력서·채용공고 읽기", "직무 적합도 분석", "맞춤 질문 만들기"],
            )

        if "_iv_result" not in st.session_state:
            st.session_state["_iv_result"] = {}
        _iv_result = st.session_state["_iv_result"]
        _iv_access_token = st.session_state.get("access_token", "")

        def _iv_start_worker():
            try:
                for event in api.start_interview_stream(
                    resume_id, jd_id, persona, access_token=_iv_access_token
                ):
                    _etype = event.get("type")
                    if _etype == "progress":
                        _iv_result["stage"] = event.get("stage")
                    elif _etype == "done":
                        _iv_result["resp"] = {
                            "session_id": event.get("session_id"),
                            "first_question": event.get("first_question"),
                        }
                    elif _etype == "error":
                        _iv_result["error"] = RuntimeError(
                            event.get("detail") or "면접 준비 중 오류가 발생했습니다."
                        )
            except Exception as e:
                _iv_result["error"] = e

        if "_iv_thread" not in st.session_state:
            st.session_state["_iv_thread"] = threading.Thread(target=_iv_start_worker, daemon=True)
            st.session_state["_iv_thread"].start()
        _iv_thread = st.session_state["_iv_thread"]

        _iv_placeholder = st.empty()
        _iv_stage_idx = 0
        while _iv_thread.is_alive():
            _stage_key = _iv_result.get("stage")
            if _stage_key in _IV_STAGE_KEYS:
                _iv_stage_idx = _IV_STAGE_KEYS.index(_stage_key)
            _iv_placeholder.markdown(_iv_prep_html(_iv_stage_idx), unsafe_allow_html=True)
            time.sleep(0.2)
        _iv_thread.join()
        _iv_placeholder.empty()
        del st.session_state["_iv_thread"]
        del st.session_state["_iv_result"]
        st.session_state.pop("_suppress_session_id_restore", None)

        _iv_error = _iv_result.get("error")
        if _iv_error is None and "resp" not in _iv_result:
            _iv_error = RuntimeError("면접 준비 중 연결이 끊겼습니다. 다시 시도해주세요.")
        if _iv_error is None:
            resp = _iv_result["resp"]
            state_set("session_id", resp["session_id"])
            first_q = resp["first_question"]
            state_set("first_question", first_q)
        elif isinstance(_iv_error, api.SessionExpiredError):
            mark_session_expired()
        elif isinstance(_iv_error, requests.exceptions.ConnectionError):
            show_error("서버에 연결할 수 없습니다. 백엔드 서버가 켜져 있는지 확인해주세요.")
            st.stop()
        elif isinstance(_iv_error, requests.exceptions.Timeout):
            show_error("면접 준비 요청이 시간 초과되었습니다. 잠시 후 다시 시도해주세요.")
            st.stop()
        elif isinstance(_iv_error, requests.exceptions.HTTPError):
            show_error(api.error_detail(_iv_error, "면접 준비에 실패했습니다."))
            st.stop()
        elif isinstance(_iv_error, RuntimeError):
            show_error(str(_iv_error))
            st.stop()
        else:
            show_error(f"면접 준비 중 알 수 없는 오류가 발생했습니다: {_iv_error}")
            st.stop()

    st.session_state.iv_messages = [
        {"role": "ai", "tag": None, "text": first_q or "안녕하세요, 면접을 시작하겠습니다."},
    ]
    st.session_state["realtime_is_rapport"] = True
    st.session_state.iv_start = time.time()

_ai_indices  = [i for i, m in enumerate(st.session_state.iv_messages) if m["role"] == "ai"]
_last_ai_idx = _ai_indices[-1] if _ai_indices else None
_last_ai_text = st.session_state.iv_messages[_last_ai_idx]["text"] if _last_ai_idx is not None else ""

if "iv_start" not in st.session_state:
    st.session_state.iv_start = time.time()
if "webcam_on" not in st.session_state:
    st.session_state.webcam_on = False
if "voice_guide_on" not in st.session_state:
    _vg_default = get("voice_guide_default")
    st.session_state.voice_guide_on = True if _vg_default is None else _vg_default

webcam_on = st.session_state.webcam_on
voice_guide_on = st.session_state.voice_guide_on
_access_token = st.session_state.get("access_token", "")

_persona  = get("interviewer_style") or "기술 리드"
_img_map  = {
    "기술 리드":   "assets/images/기술리드.png",
    "인사 담당자": "assets/images/인사 담당자.png",
    "임원 면접관": "assets/images/임원 면접관.png",
}
try:
    _avatar_b64 = base64.b64encode(
        resource(_img_map.get(_persona, "assets/images/기술리드.png")).read_bytes()
    ).decode()
    _avatar_src = f"data:image/png;base64,{_avatar_b64}"
except Exception:
    _avatar_src = ""

# ── 질문 음성 (Google Cloud TTS, Chirp 3 HD) ─────────────────────────────
# 이 파이썬 코드는 브라우저가 아니라 web 컨테이너에서 돌기 때문에, 여기서 Google을 부르면
# API 키가 브라우저에 노출되지 않는다 (백엔드 /voice/speak 불필요). 받은 mp3(base64)를
# 아래 components.html에 data URL로 실어 보내고, 브라우저는 그걸 재생만 한다.
# 키가 없거나 호출이 실패하면 None → 화면은 기존 브라우저 음성(speechSynthesis)으로 읽는다.
_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
_TTS_API_KEY = os.getenv("GOOGLE_TTS_API_KEY", "").strip()
_TTS_VOICES = {
    "기술 리드":   os.getenv("GOOGLE_TTS_VOICE_TECH", "ko-KR-Chirp3-HD-Iapetus"),
    "인사 담당자": os.getenv("GOOGLE_TTS_VOICE_HR", "ko-KR-Chirp3-HD-Vindemiatrix"),
    "임원 면접관": os.getenv("GOOGLE_TTS_VOICE_EXEC", "ko-KR-Chirp3-HD-Algieba"),
}


def _env_number(name, default, cast, lo, hi):
    try:
        return min(hi, max(lo, cast(os.getenv(name, default))))
    except (TypeError, ValueError):
        return default

_VIDEO_UPLOAD_WAIT_SEC = _env_number("VIDEO_UPLOAD_WAIT_SEC", 20, int, 5, 300)

_INTERVIEW_LIMIT_MIN = _env_number("INTERVIEW_TIME_LIMIT_MIN", 30, int, 1, 180)
_INTERVIEW_LIMIT_SEC = _INTERVIEW_LIMIT_MIN * 60

_TTS_SPEAKING_RATE = _env_number("GOOGLE_TTS_SPEAKING_RATE", 1.0, float, 0.25, 4.0)
_TTS_MAX_CHARS = _env_number("TTS_MAX_CHARS", 600, int, 1, 5000)


def _tts_text(text):
    return (text or "").replace("\n", " ").strip()


def _question_audio_b64(persona, text):
    text = _tts_text(text)
    if not _TTS_API_KEY or not text or len(text) > _TTS_MAX_CHARS:
        return None
    cache = st.session_state.setdefault("_iv_tts_cache", {})
    cache_key = (persona, text)
    if cache_key in cache:
        return cache[cache_key]
    audio_b64 = None
    try:
        res = requests.post(
            _TTS_URL,
            headers={"X-Goog-Api-Key": _TTS_API_KEY},
            json={
                "input": {"text": text},
                "voice": {
                    "languageCode": "ko-KR",
                    "name": _TTS_VOICES.get(persona, _TTS_VOICES["기술 리드"]),
                },
                "audioConfig": {"audioEncoding": "MP3", "speakingRate": _TTS_SPEAKING_RATE},
            },
            timeout=10,
        )
        res.raise_for_status()
        audio_b64 = res.json().get("audioContent") or None
    except Exception as e:  
        print(f"[TTS] Google 음성 생성 실패 → 브라우저 음성으로 대체: {type(e).__name__}: {e}")
    cache[cache_key] = audio_b64
    return audio_b64


_last_ai_audio_b64 = _question_audio_b64(_persona, _last_ai_text) if _last_ai_text else None
_last_ai_audio_src = f"data:audio/mpeg;base64,{_last_ai_audio_b64}" if _last_ai_audio_b64 else None

st.markdown(
    "<style>.intro-account-menu { display:none !important; }</style>",
    unsafe_allow_html=True,
)

# ── 레이아웃 ──────────────────────────────────────────────────────────────
FEEDBACK_W = 288
right_px   = FEEDBACK_W

# ── 타이머 초기값 ────────────────────────────
elapsed   = int(time.time() - st.session_state.iv_start)
remaining = max(0, _INTERVIEW_LIMIT_SEC - elapsed)
timer_str = f"{remaining // 60:02d}:{remaining % 60:02d}"

# ── 실시간 피드백 데이터 ───────────────────────────────────────────────────
_rt_pending    = bool(st.session_state.get("_pending_answer"))
_rt_is_rapport = bool(st.session_state.get("realtime_is_rapport"))
_rt_score    = None if (_rt_pending or _rt_is_rapport) else st.session_state.get("realtime_score")
_rt_feedback = [] if (_rt_pending or _rt_is_rapport) else (st.session_state.get("realtime_feedback") or [])

TOTAL = _rt_score.get("total") if _rt_score else None
SCORES = [
    ("논리성",       _rt_score.get("logic", 0)),
    ("커뮤니케이션", _rt_score.get("communication", 0)),
    ("전문 지식",    _rt_score.get("expertise", 0)),
    ("태도",         _rt_score.get("attitude", 0)),
    ("문제 해결력",  _rt_score.get("problem_solving", 0)),
] if _rt_score else []

R = 40; cx = cy = 52
circ = 2 * math.pi * R
if TOTAL is None:
    donut_svg = (
        f'<svg width="108" height="108" viewBox="0 0 104 104">'
        f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#e5e7eb" stroke-width="10"/>'
        f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" font-size="12"'
        f' fill="#9ca3af" font-family="sans-serif">'
        f'{"분석 중" if _rt_pending else ("채점 제외" if _rt_is_rapport else "대기 중")}</text>'
        f'</svg>'
    )
else:
    fill = circ * TOTAL / 100
    donut_svg = (
        f'<svg width="108" height="108" viewBox="0 0 104 104">'
        f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#e5e7eb" stroke-width="10"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#3b6def" stroke-width="10"'
        f' stroke-dasharray="{fill:.1f} {circ - fill:.1f}"'
        f' transform="rotate(-90 {cx} {cy})" stroke-linecap="round"/>'
        f'<text x="{cx}" y="{cy + 7}" text-anchor="middle" font-size="22" font-weight="700"'
        f' fill="#111827" font-family="sans-serif">{TOTAL}</text>'
        f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" font-size="10"'
        f' fill="#9ca3af" font-family="sans-serif">/100</text>'
        f'</svg>'
    )

_SKEL_LABELS = ["논리성", "커뮤니케이션", "전문 지식", "태도", "문제 해결력"]

def _skeleton_scores(note: str, animated: bool) -> str:
    bar_cls = "iv-skel-bar" + (" iv-skel-anim" if animated else "")
    rows = ""
    for label in _SKEL_LABELS:
        rows += (
            f'<div style="font-size:12px;color:#9ca3af;margin-bottom:4px;">{label}</div>'
            f'<div style="border-radius:3px;height:5px;margin-bottom:14px;overflow:hidden;">'
            f'<div class="{bar_cls}" style="height:5px;border-radius:3px;"></div></div>'
        )
    if note:
        rows += f'<div style="font-size:11px;color:#9ca3af;text-align:center;margin-top:2px;">{note}</div>'
    return rows

def _skeleton_feedback(note: str, animated: bool) -> str:
    bar_cls = "iv-skel-bar" + (" iv-skel-anim" if animated else "")
    rows = ""
    for h in (36, 36):
        rows += (
            f'<div style="border-radius:8px;height:{h}px;margin-bottom:6px;overflow:hidden;">'
            f'<div class="{bar_cls}" style="height:{h}px;border-radius:8px;"></div></div>'
        )
    rows += f'<div style="font-size:12px;color:#9ca3af;text-align:center;padding:8px 0 0;">{note}</div>'
    return rows

if SCORES:
    scores_html = ""
    for label, score in SCORES:
        scores_html += (
            f'<div style="display:flex;justify-content:space-between;font-size:12px;'
            f'color:#111827;margin-bottom:4px;">'
            f'<span>{label}</span>'
            f'<span style="font-weight:600;color:#3b6def;">{score}</span></div>'
            f'<div style="height:5px;border-radius:3px;margin-bottom:14px;">'
            f'<div style="width:{score}%;min-width:{"3px" if score else "0"};'
            f'background:#3b6def;height:5px;border-radius:3px;"></div></div>'
        )
elif _rt_pending:
    scores_html = _skeleton_scores("분석 중입니다...", animated=True)
elif _rt_is_rapport:
    # 패널 제목 아래에 이미 "자기소개 답변은 채점하지 않아요"가 있어 여기서는 다시 쓰지 않는다.
    scores_html = _skeleton_scores("", animated=False)
else:
    scores_html = _skeleton_scores("첫 답변을 제출하면 표시돼요", animated=False)

if _rt_feedback:
    feedback_html = ""
    for item in _rt_feedback:
        is_positive = item.get("type") == "positive"
        bg    = "#f9fafb" if is_positive else "#fffbeb"
        color = "#374151" if is_positive else "#92400e"
        icon = '<i class="ph-bold ph-check-circle"></i>' if is_positive else '<i class="ph-bold ph-lightbulb"></i>'
        feedback_html += (
            f'<div style="background:{bg};border-radius:8px;padding:10px 12px;'
            f'margin-bottom:6px;font-size:12px;color:{color};display:flex;align-items:center;gap:6px;">'
            f'{icon} {item.get("text", "")}</div>'
        )
elif _rt_pending:
    feedback_html = _skeleton_feedback("분석 중입니다...", animated=True)
elif _rt_is_rapport:
    feedback_html = _skeleton_feedback("다음 답변부터 채점이 시작돼요", animated=False)
else:
    feedback_html = _skeleton_feedback("첫 답변을 제출하면 표시돼요", animated=False)

# ── CSS ──────────────────────────────────────────────────────────────────
st.markdown(f"""<style>
[data-testid="stMain"] {{ padding-right: {right_px}px !important; }}
[data-testid="stMainBlockContainer"] {{ padding: 20px {right_px + 24}px 140px 40px !important; }}
[data-testid="stVerticalBlock"] {{ gap: 0 !important; }}

[data-testid="stBottom"] {{
    position: fixed !important;
    left: -9999px !important;
    bottom: 0 !important;
    opacity: 0 !important;
    z-index: -999 !important;
}}
.st-key-btn_end_interview {{
    position: fixed !important;
    left: -9999px !important; top: 0 !important;
    opacity: 0 !important;
}}
.st-key-input_type_hidden {{
    position: absolute !important;
    width: 0 !important; height: 0 !important;
    overflow: hidden !important; clip: rect(0,0,0,0) !important;
    margin: 0 !important; padding: 0 !important;
}}
[data-testid="stHeader"] {{ pointer-events: none !important; }}

#webcam-preview-video::-webkit-media-controls-start-playback-button {{
    display: none !important;
    -webkit-appearance: none !important;
}}
#webcam-preview-video::-webkit-media-controls {{ display: none !important; }}

.iv-ai-row {{ display:flex; align-items:flex-start; gap:12px; margin-bottom:28px; }}
.iv-ai-avatar {{
    width:36px; height:36px; border-radius:50%; background:#3b6def;
    flex-shrink:0; margin-top:2px; overflow:hidden;
}}
.iv-ai-bubble {{
    background:white; border-radius:4px 14px 14px 14px;
    padding:14px 16px; font-size:13px; color:#111827; line-height:1.65;
    box-shadow:0 1px 4px rgba(0,0,0,0.08); max-width:540px; white-space:pre-wrap;
}}
.iv-user-row {{ display:flex; justify-content:flex-end; margin-bottom:28px; }}
.iv-user-bubble {{
    background:#f8fafc; border-radius:14px 4px 14px 14px;
    padding:14px 16px; font-size:13px; color:#111827; line-height:1.65;
    max-width:540px; white-space:pre-wrap;
}}

.iv-playback-divider {{ height:1px; background:#e5e7eb; margin:10px 0 8px; }}
.iv-playback-row {{ display:flex; justify-content:flex-end; align-items:center; }}
.iv-playback-row.playing {{ justify-content:space-between; }}
.iv-playback-status {{ display:none; font-size:12px; font-weight:600; color:#3b6def; }}
.iv-playback-row.playing .iv-playback-status {{ display:inline; }}
.iv-playback-replay {{
    font-size:12px; color:#9ca3af; text-decoration:underline; cursor:pointer;
}}

.iv-skel-bar {{ background:#eef0f3; }}
.iv-skel-anim {{
    background:linear-gradient(90deg,#eef0f3 25%,#f8fafc 37%,#eef0f3 63%);
    background-size:400px 100%;
    animation:iv-skel-shimmer 1.6s ease-in-out infinite;
}}
@keyframes iv-skel-shimmer {{
    0%   {{ background-position:-120px 0; }}
    100% {{ background-position:120px 0; }}
}}
</style>""", unsafe_allow_html=True)

# ── 헤더 우측 ─────────────────────────────────
_vg_track_bg  = '#3b6def' if voice_guide_on else '#e5e7eb'
_vg_knob_left = '18px'    if voice_guide_on else '2px'

_end_btn_bg     = '#e5e7eb'  if _rt_pending else '#dc2626'
_end_btn_color  = '#9ca3af'  if _rt_pending else 'white'
_end_btn_cursor = 'default'  if _rt_pending else 'pointer'
_end_btn_label  = '처리 중...' if _rt_pending else '면접 종료'

st.markdown(
    f'<div style="position:fixed;top:0;right:0;height:60px;'
    f'display:flex;align-items:center;gap:10px;padding:0 20px;z-index:99999;">'
    f'<div id="voice-guide-toggle" style="display:flex;align-items:center;gap:8px;'
    f'background:#eef3ff;border-radius:16px;height:32px;padding:0 12px;cursor:pointer;">'
    f'<span style="font-size:13px;font-weight:600;color:#3b6def;">음성 안내</span>'
    f'<div id="vg-track" style="width:36px;height:20px;border-radius:10px;background:{_vg_track_bg};'
    f'position:relative;transition:background 0.15s;">'
    f'<div id="vg-knob" style="width:16px;height:16px;border-radius:50%;background:white;'
    f'position:absolute;top:2px;left:{_vg_knob_left};transition:left 0.15s;"></div>'
    f'</div></div>'
    f'<div style="display:flex;align-items:center;gap:6px;background:#fff5f5;'
    f'border-radius:8px;height:34px;padding:0 14px;">'
    f'<i class="ph-bold ph-clock" style="font-size:14px;color:#dc2626;"></i>'
    f'<span id="iv-timer" style="font-size:13px;font-weight:700;color:#dc2626;">{timer_str}</span>'
    f'</div>'
    f'<div id="end-interview" data-pending="{str(_rt_pending).lower()}" '
    f'style="background:{_end_btn_bg};color:{_end_btn_color};font-size:13px;font-weight:600;'
    f'height:34px;display:flex;align-items:center;padding:0 16px;'
    f'border-radius:8px;cursor:{_end_btn_cursor};">'
    f'{_end_btn_label}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── 피드백 패널 ───────────────────────────
_webcam_display = "" if webcam_on else "display:none;"
webcam_html = (
    f'<div id="webcam-preview-block" style="width:100%;height:210px;overflow:hidden;{_webcam_display}'
    'background:#111827;position:relative;">'
    '<video id="webcam-preview-video" autoplay playsinline muted '
    'style="width:100%;height:100%;object-fit:cover;transform:scaleX(-1);"></video>'
    '<div id="webcam-preview-status" style="display:none;position:absolute;inset:0;'
    'align-items:center;justify-content:center;text-align:center;padding:12px;'
    'font-size:11px;color:#e5e7eb;background:rgba(0,0,0,0.55);"></div>'
    '<select id="webcam-cam-select" style="position:absolute;left:6px;right:6px;bottom:6px;'
    'font-size:10px;background:rgba(0,0,0,0.55);color:white;border:1px solid rgba(255,255,255,0.3);'
    'border-radius:5px;padding:3px 5px;box-sizing:border-box;"></select>'
    '</div>'
    f'<div id="webcam-preview-divider" style="height:1px;background:#e5e7eb;margin-bottom:16px;{_webcam_display}"></div>'
)

_panel_subtitle = (
    "자기소개 답변은 채점하지 않아요" if (_rt_is_rapport and not _rt_pending)
    else "AI가 분석 중입니다"
)
_panel_body = (
    '<div style="font-size:14px;font-weight:600;color:#111827;margin-bottom:2px;">실시간 피드백</div>'
    f'<div style="font-size:12px;color:#6b7280;margin-bottom:16px;">{_panel_subtitle}</div>'
    '<div style="display:flex;flex-direction:column;align-items:center;margin-bottom:8px;">'
    + donut_svg
    + '<div style="font-size:12px;font-weight:500;color:#111827;margin-top:4px;">현재 점수</div>'
    '<div style="font-size:10px;color:#9ca3af;margin-top:2px;">※ 영상은 점수에 반영되지 않습니다</div>'
    '</div>'
    '<div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:12px;">세부 평가 항목</div>'
    + scores_html
    + '<div style="font-size:13px;font-weight:600;color:#111827;margin-bottom:10px;">AI 실시간 피드백</div>'
    + feedback_html
)

st.markdown(
    '<div style="position:fixed;top:60px;right:0;width:288px;'
    'height:calc(100vh - 60px);background:white;border-left:1px solid #e5e7eb;'
    'overflow-y:auto;z-index:300;box-sizing:border-box;">'
    + webcam_html
    + '<div style="padding:16px 18px 20px;">'
    + _panel_body
    + '</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.text_input("input_type", value="text", key="input_type_hidden", label_visibility="collapsed")

# ── 커스텀 입력바 ─────────────────
_cam_bg = '#3b6def' if webcam_on else '#f8fafc'
_cam_bd = '#3b6def' if webcam_on else '#e5e7eb'

if webcam_on:
    _cam_icon_svg = (
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none">'
        '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" fill="white"/>'
        '<circle cx="12" cy="13" r="4" fill="#3b6def"/>'
        '</svg>'
    )
else:
    _cam_icon_svg = (
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6b7280"'
        ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>'
        '<circle cx="12" cy="13" r="4"/>'
        '</svg>'
    )

components.html(f"""<!DOCTYPE html><html><head>
<style>
*{{box-sizing:border-box;margin:0;padding:0;
   font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}}
body{{
  background:white;border-top:1px solid #f8fafc;
  display:flex;flex-direction:column;justify-content:center;
  overflow:hidden;
}}
#hint-row{{
  display:none;text-align:center;font-size:12px;font-weight:600;
  color:#3b6def;padding:8px 20px 0;
}}
#note-row{{
  display:none;text-align:center;font-size:11px;color:#9ca3af;
  padding:0 20px 6px;
}}
#timeup-row{{
  display:none;text-align:center;font-size:12px;font-weight:600;
  color:#dc2626;background:#fff5f5;margin:8px 20px 0;padding:8px 12px;
  border-radius:8px;
}}
#speech-rate-row{{
  display:none;align-items:center;justify-content:center;gap:8px;
  text-align:center;font-size:14px;color:#6b7280;
  padding:0 20px 10px;
}}
#speech-rate-row .srr-badge{{
  font-weight:700;padding:2px 10px;border-radius:10px;font-size:13px;
}}
#controls-row{{
  display:flex;align-items:center;padding:16px 20px;
}}
#ta-wrap{{flex:1;margin-right:12px;}}
#cta{{
  display:block;width:100%;height:44px;min-height:44px;max-height:120px;
  border:1px solid #e5e7eb;border-radius:14px;
  background:#f9fafb;font-size:14px;color:#111827;
  padding:11px 21px;resize:none;outline:none;
  font-family:inherit;line-height:20px;overflow-y:auto;
}}
#cta::placeholder{{color:#9ca3af;}}
#cta:focus{{border-color:#e5e7eb;background:#f9fafb;box-shadow:none;}}
.ibtn{{
  width:40px;height:40px;border-radius:8px;
  border:1.5px solid #e5e7eb;background:#f8fafc;
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;flex-shrink:0;user-select:none;
}}
#sbtn{{background:#3b6def;border-color:#3b6def;}}
#mbtn{{margin-left:8px;}}
#cbtn{{background:{_cam_bg};border-color:{_cam_bd};margin-left:8px;}}
</style></head><body>
<div id="hint-row">음성 인식 중... 말씀하신 내용이 아래에 입력됩니다</div>
<div id="timeup-row">면접이 종료되었습니다. 지금 작성 중인 답변을 보내시면 정상적으로 함께 제출돼요.</div>
<div id="controls-row">
<div id="ta-wrap">
  <textarea id="cta" placeholder="답변을 입력하세요..." rows="1"></textarea>
</div>
<div class="ibtn" id="sbtn">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
    <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z"/>
  </svg>
</div>
<div class="ibtn" id="mbtn">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
    <line x1="12" y1="19" x2="12" y2="22"/>
    <line x1="8" y1="22" x2="16" y2="22"/>
  </svg>
</div>
<div class="ibtn" id="cbtn">
  {_cam_icon_svg}
</div>
</div>
<div id="note-row">전사된 텍스트는 전송 전에 직접 수정할 수 있습니다</div>
<div id="speech-rate-row"></div>
<script>
(function(){{
  // ── 실시간 타이머 ────────────────────────────────────────────────
  var _startSec = {int(st.session_state.iv_start)};
  var _ivAutoEnded = false;
  var _answerPending = {str(bool(st.session_state.get("_pending_answer"))).lower()};
  var _awaitingAnswer = {str(bool(st.session_state.iv_messages and st.session_state.iv_messages[-1]["role"] == "ai")).lower()};
  var _timeupNoteShown = false;
  function _tick() {{
    var rem = Math.max(0, {_INTERVIEW_LIMIT_SEC} - Math.floor(Date.now()/1000 - _startSec));
    var el  = window.parent.document.getElementById('iv-timer');
    if (el) el.textContent =
      String(Math.floor(rem/60)).padStart(2,'0') + ':' +
      String(rem%60).padStart(2,'0');
    var shouldShowTimeup = rem <= 0 && !_ivAutoEnded && !_answerPending && _awaitingAnswer;
    if (timeupRowEl && shouldShowTimeup !== _timeupNoteShown) {{
      _timeupNoteShown = shouldShowTimeup;
      timeupRowEl.style.display = shouldShowTimeup ? 'block' : 'none';
      recomputeBarHeight();
    }}
    if (rem <= 0 && !_ivAutoEnded && !_answerPending && !_awaitingAnswer) {{
      _ivAutoEnded = true;
      if (typeof showLoadingAndEnd === 'function') {{
        showLoadingAndEnd();
      }}
    }}
  }}
  _tick();
  setInterval(_tick, 1000);

  var fr = window.frameElement;
  var barHeight = 76;
  function applyFixed() {{
    if (!fr) return;
    fr.style.position = 'fixed';
    fr.style.bottom   = '0';
    fr.style.left     = '0px';
    fr.style.width    = 'calc(100vw - {right_px}px)';
    fr.style.height   = barHeight + 'px';
    fr.style.zIndex   = '500';
    fr.style.border   = 'none';
    fr.style.display  = 'block';
  }}
  applyFixed();
  if (fr) {{
    new MutationObserver(applyFixed)
      .observe(fr, {{attributes:true, attributeFilter:['style']}});
  }}

  var doc  = window.parent.document;
  var cta  = document.getElementById('cta');
  var mbtn = document.getElementById('mbtn');
  var sbtn = document.getElementById('sbtn');
  var cbtn = document.getElementById('cbtn');

  // ── 입력창 자동 높이 ─────
  var controlsRowEl = document.getElementById('controls-row');
  var hintRowEl = document.getElementById('hint-row');
  var noteRowEl = document.getElementById('note-row');
  var speechRateRowEl = document.getElementById('speech-rate-row');
  var timeupRowEl = document.getElementById('timeup-row');
  function recomputeBarHeight() {{
    requestAnimationFrame(function() {{
      var h = controlsRowEl.offsetHeight;
      if (hintRowEl.style.display !== 'none') h += hintRowEl.offsetHeight;
      if (noteRowEl.style.display !== 'none') h += noteRowEl.offsetHeight;
      if (speechRateRowEl.style.display !== 'none') h += speechRateRowEl.offsetHeight;
      if (timeupRowEl.style.display !== 'none') h += timeupRowEl.offsetHeight;
      barHeight = h;
      applyFixed();
    }});
  }}
  function autosize() {{
    cta.style.height = 'auto';
    cta.style.height = cta.scrollHeight + 'px';
    recomputeBarHeight();
  }}

  function getStTa() {{ return doc.querySelector('[data-testid="stChatInputTextArea"]'); }}
  function syncSt(val) {{
    var t = getStTa();
    if (!t) return;
    var setter = Object.getOwnPropertyDescriptor(
      window.parent.HTMLTextAreaElement.prototype, 'value'
    ).set;
    setter.call(t, val);
    t.dispatchEvent(new Event('input', {{bubbles:true}}));
  }}

  var lastInputType = 'text';
  function syncInputType(val) {{
    var el = doc.querySelector('.st-key-input_type_hidden input');
    if (!el) return;
    var setter = Object.getOwnPropertyDescriptor(
      window.parent.HTMLInputElement.prototype, 'value'
    ).set;
    setter.call(el, val);
    el.dispatchEvent(new Event('input', {{bubbles:true}}));
  }}

  cta.addEventListener('input', function() {{
    lastInputType = 'text';
    syncSt(cta.value);
    autosize();
  }});

  // ── 전송 ─────────────────────────────────────────────────────────
  function send() {{
    var value = cta.value;
    syncInputType(lastInputType);
    syncSt(value);
    function doClick() {{
      var btn = doc.querySelector('[data-testid="stChatInputSubmitButton"]');
      if (btn) {{ btn.click(); cta.value = ''; }}
      lastInputType = 'text';
      autosize();
    }}
    var topWin = window.parent;
    if (topWin && topWin.requestAnimationFrame) {{
      topWin.requestAnimationFrame(function() {{
        topWin.requestAnimationFrame(function() {{ setTimeout(doClick, 30); }});
      }});
    }} else {{
      setTimeout(doClick, 80);
    }}
  }}
  cta.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); send(); }}
  }});
  sbtn.addEventListener('click', send);

  // ── 카메라 토글 ──────
  var _camGen = (window.parent.__ivCamGen = (window.parent.__ivCamGen || 0) + 1);
  var webcamOn = {str(webcam_on).lower()};
  var CAM_OUTLINE =
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6b7280" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>' +
    '<circle cx="12" cy="13" r="4"/>' +
    '</svg>';
  var CAM_FILLED =
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" fill="white"/>' +
    '<circle cx="12" cy="13" r="4" fill="#3b6def"/>' +
    '</svg>';

  (function syncCamToActualStream() {{
    var vr = window.parent.__ivVideoRec;
    if (vr && vr.stream) {{
      webcamOn = true;
      cbtn.innerHTML = CAM_FILLED;
      cbtn.style.background  = '#3b6def';
      cbtn.style.borderColor = '#3b6def';
      var pv0 = doc.getElementById('webcam-preview-block');
      var pd0 = doc.getElementById('webcam-preview-divider');
      if (pv0) pv0.style.display = '';
      if (pd0) pd0.style.display = '';
      startVideoRecording();
    }}
  }})();

  cbtn.addEventListener('click', function() {{
    if (window.parent.__ivCamGen !== _camGen) return;  // 낡은 iframe에서 온 클릭은 무시
    webcamOn = !webcamOn;
    cbtn.innerHTML = webcamOn ? CAM_FILLED : CAM_OUTLINE;
    cbtn.style.background  = webcamOn ? '#3b6def' : '#f8fafc';
    cbtn.style.borderColor = webcamOn ? '#3b6def' : '#e5e7eb';
    var pv = doc.getElementById('webcam-preview-block');
    var pd = doc.getElementById('webcam-preview-divider');
    if (pv) pv.style.display = webcamOn ? '' : 'none';
    if (pd) pd.style.display = webcamOn ? '' : 'none';
    if (webcamOn) startVideoRecording();
  }});

  // ── 영상 녹화 (웹캠 허용 시, 면접 시작과 동시에 자동 시작) ─────
  var _accessToken = {json.dumps(_access_token)};
  var _videoSessionId = {json.dumps(str(get("session_id")))};
  var _videoRecActive = {str(webcam_on).lower()};

  function startVideoRecording() {{
    var pWin = window.parent;
    if (!pWin.__ivVideoInit) {{
      pWin.__ivVideoInit = true;
      var _s = pWin.document.createElement('script');
      _s.textContent = [
        'window.__ivVideoRec = window.__ivVideoRec || {{ recorder: null, stream: null, chunks: [], uploaded: false, connecting: false }};',
        'window.__ivStartVideoRecording = function(onReady) {{',
        '  var vr = window.__ivVideoRec;',
        '  if (vr.stream) {{ onReady(vr.stream); return; }}',
        '  if (vr.connecting) {{ return; }}',
        '  vr.connecting = true;',
        '  function onStreamReady(stream) {{',
        '    vr.connecting = false;',
        '    vr.stream = stream;',
        '    try {{',
        '      var mimeCandidates = ["video/webm;codecs=vp8", "video/webm;codecs=vp9", "video/webm", "video/mp4"];',
        '      var chosen = "";',
        '      for (var i = 0; i < mimeCandidates.length; i++) {{',
        '        if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(mimeCandidates[i])) {{ chosen = mimeCandidates[i]; break; }}',
        '      }}',
        '      var opts = {{ videoBitsPerSecond: 500000 }};',
        '      if (chosen) opts.mimeType = chosen;',
        '      vr.recorder = new MediaRecorder(stream, opts);',
        '      vr.recorder.ondataavailable = function(e) {{ if (e.data.size > 0) vr.chunks.push(e.data); }};',
        '      vr.recorder.onerror = function(e) {{ console.warn("[영상] 레코더 에러:", e.error || e); }};',
        '      vr.recorder.start(2000);',
        '    }} catch (err) {{ console.warn("[영상] 레코더 생성 실패:", err); }}',
        '    onReady(stream);',
        '  }}',
        '  var _baseConstraints = {{ width: {{ ideal: 640 }}, height: {{ ideal: 480 }}, frameRate: {{ ideal: 15, max: 15 }} }};',
        '  function openCamera(constraints) {{',
        '    return navigator.mediaDevices.getUserMedia({{ video: constraints, audio: false }});',
        '  }}',
        '  var _camId = null;',
        '  try {{ _camId = localStorage.getItem("iv_camera_device_id"); }} catch (e) {{}}',
        '  if (_camId) {{',
        '    var _withDevice = Object.assign({{}}, _baseConstraints, {{ deviceId: {{ exact: _camId }} }});',
        '    openCamera(_withDevice).then(onStreamReady).catch(function(err) {{',
        '      console.warn("[영상] 저장된 카메라를 열지 못해 기본 카메라로 재시도:", err);',
        '      openCamera(_baseConstraints).then(onStreamReady).catch(function(err2) {{',
        '        vr.connecting = false;',
        '        console.warn("[영상] 웹캠 접근 실패:", err2);',
        '      }});',
        '    }});',
        '  }} else {{',
        '    openCamera(_baseConstraints).then(onStreamReady).catch(function(err) {{',
        '      vr.connecting = false;',
        '      console.warn("[영상] 웹캠 접근 실패:", err);',
        '    }});',
        '  }}',
        '}};',

        'window.__ivSwitchCamera = function(deviceId, onDone) {{',
        '  var vr = window.__ivVideoRec;',
        '  if (!vr || !vr.stream) {{ if (onDone) onDone(false); return; }}',
        '  navigator.mediaDevices.getUserMedia({{',
        '    video: {{ deviceId: {{ exact: deviceId }}, width: {{ ideal: 640 }}, height: {{ ideal: 480 }}, frameRate: {{ ideal: 15, max: 15 }} }},',
        '    audio: false',
        '  }}).then(function(newStream) {{',
        '    var newTrack = newStream.getVideoTracks()[0];',
        '    vr.stream.getVideoTracks().forEach(function(t) {{',
        '      vr.stream.removeTrack(t);',
        '      t.stop();',
        '    }});',
        '    vr.stream.addTrack(newTrack);',
        '    try {{ localStorage.setItem("iv_camera_device_id", newTrack.getSettings().deviceId || deviceId); }} catch (e) {{}}',
        '    if (onDone) onDone(true);',
        '  }}).catch(function(err) {{',
        '    console.warn("[영상] 카메라 전환 실패:", err);',
        '    if (onDone) onDone(false);',
        '  }});',
        '}};',

        'window.__ivStopAndUploadVideo = function(sessionId, accessToken, baseUrl, onDone) {{',
        '  var vr = window.__ivVideoRec;',
        '  if (!vr || !vr.recorder) {{ onDone(false); return; }}',
        '  if (vr.recorder.state === "inactive" || vr.uploaded) {{ onDone(!!vr.uploadSucceeded); return; }}',
        '  vr.uploaded = true;',
        '  vr.recorder.onstop = function() {{',
        '    var actualType = vr.recorder.mimeType || "video/webm";',
        '    var ext = actualType.indexOf("mp4") !== -1 ? "mp4" : "webm";',
        '    var blob = new Blob(vr.chunks, {{ type: actualType }});',
        '    if (blob.size === 0) {{',
        '      console.warn("[영상] 녹화된 데이터가 0바이트입니다.");',
        '      vr.uploadSucceeded = false;',
        '      onDone(false);',
        '      return;',
        '    }}',
        '    var form = new FormData();',
        '    form.append("video", blob, "interview_" + sessionId + "." + ext);',
        '    fetch(baseUrl + "/interview/" + sessionId + "/video", {{',
        '      method: "POST",',
        '      headers: {{ "Authorization": "Bearer " + accessToken }},',
        '      body: form',
        '    }}).then(function(res) {{',
        '      if (!res.ok) {{',
        '        res.text().then(function(t) {{ console.warn("[영상] 업로드 실패 HTTP " + res.status + ": " + t); }});',
        '        vr.uploadSucceeded = false;',
        '        onDone(false);',
        '      }} else {{',
        '        vr.uploadSucceeded = true;',
        '        onDone(true);',
        '      }}',
        '    }}).catch(function(err) {{',
        '      console.warn("[영상] 업로드 네트워크 오류:", err);',
        '      vr.uploadSucceeded = false;',
        '      onDone(false);',
        '    }});',
        '  }};',
        '  vr.recorder.stop();',
        '  if (vr.stream) {{ vr.stream.getTracks().forEach(function(t) {{ t.stop(); }}); }}',
        '}};'
      ].join('\\n');
      pWin.document.head.appendChild(_s);
    }}
    pWin.__ivStartVideoRecording(function(stream) {{
      _videoRecActive = true;
      var preview = doc.getElementById('webcam-preview-video');
      if (preview) {{
        preview.srcObject = stream;
        var p = preview.play();
        if (p && p.catch) p.catch(function(err) {{ console.warn('미리보기 재생 실패:', err); }});
      }}
      var statusEl = doc.getElementById('webcam-preview-status');
      if (statusEl) {{ statusEl.style.display = 'none'; }}
      populateCamSelect();
    }});
  }}
  function populateCamSelect() {{
    var sel = doc.getElementById('webcam-cam-select');
    if (!sel || !navigator.mediaDevices.enumerateDevices) return;
    navigator.mediaDevices.enumerateDevices().then(function(devices) {{
      var cams = devices.filter(function(d) {{ return d.kind === 'videoinput'; }});
      if (!cams.length) {{ sel.style.display = 'none'; return; }}
      var vr = window.parent.__ivVideoRec;
      var activeTrack = vr && vr.stream ? vr.stream.getVideoTracks()[0] : null;
      var activeId = activeTrack ? activeTrack.getSettings().deviceId : null;
      sel.innerHTML = '';
      cams.forEach(function(d, i) {{
        var opt = doc.createElement('option');
        opt.value = d.deviceId;
        opt.textContent = d.label || ('카메라 ' + (i + 1));
        if (d.deviceId === activeId) opt.selected = true;
        sel.appendChild(opt);
      }});
      sel.onchange = function() {{
        var chosen = sel.value;
        window.parent.__ivSwitchCamera(chosen, function(ok) {{
          if (!ok) console.warn('[영상] 카메라 전환에 실패했습니다.');
        }});
      }};
    }}).catch(function(err) {{
      console.warn('[영상] 카메라 목록을 불러오지 못했습니다:', err);
    }});
  }}

  if (_videoRecActive) {{ startVideoRecording(); }}

  function stopAndUploadVideo(onDone) {{
    if (window.parent.__ivStopAndUploadVideo) {{
      window.parent.__ivStopAndUploadVideo(_videoSessionId, _accessToken, '{api.PUBLIC_BASE_URL}', onDone);
    }} else {{
      console.warn('[영상] 녹화가 시작된 적이 없습니다 (카메라 권한/시작 단계에서 실패).');
      onDone(false);
    }}
  }}

  function pickKoreanVoice(pWin) {{
    var voices = pWin.speechSynthesis.getVoices() || [];
    if (!voices.length) return null;
    var picked = voices.find(function(v) {{
      return /^ko/i.test(v.lang) && !v.localService;
    }});
    return picked || voices[0];
  }}

  // ── 질문 음성: 서버(Google TTS)가 만든 mp3 우선, 없으면 브라우저 음성 ─────
  (function initTtsPlayer() {{
    var pWin = window.parent;
    if (pWin.__ivTtsInit) return;
    pWin.__ivTtsInit = true;
    var _s = pWin.document.createElement('script');
    _s.textContent = [
      'window.__ivTtsClips = window.__ivTtsClips || {{}};',
      'window.__ivTtsAudio = null;',
      'window.__ivTtsRow = function(msgIdx) {{',
      '  var rows = document.querySelectorAll(".iv-playback-row");',
      '  for (var i = 0; i < rows.length; i++) {{',
      '    if (rows[i].getAttribute("data-msg-idx") === String(msgIdx)) return rows[i];',
      '  }}',
      '  return null;',
      '}};',
      'window.__ivTtsStop = function() {{',
      '  var a = window.__ivTtsAudio;',
      '  window.__ivTtsAudio = null;',
      '  if (a) {{ a.onplay = a.onended = a.onerror = null; try {{ a.pause(); }} catch (e) {{}} }}',
      '  if (window.speechSynthesis) window.speechSynthesis.cancel();',
      '  document.querySelectorAll(".iv-playback-row.playing").forEach(function(r) {{ r.classList.remove("playing"); }});',
      '}};',
      'window.__ivTtsPlay = function(key, msgIdx, onFail) {{',
      '  var src = window.__ivTtsClips[key];',
      '  if (!src) return false;',
      '  var row = window.__ivTtsRow(msgIdx);',
      '  var a = new Audio(src);',
      '  window.__ivTtsAudio = a;',
      '  function fail(err) {{',
      '    if (window.__ivTtsAudio !== a) return;',
      '    window.__ivTtsAudio = null;',
      '    if (row) row.classList.remove("playing");',
      '    console.warn("[음성] mp3 재생 실패 → 브라우저 음성으로 대체:", err);',
      '    if (onFail) onFail();',
      '  }}',
      '  a.onplay = function() {{ if (row) row.classList.add("playing"); }};',
      '  a.onended = function() {{ if (row) row.classList.remove("playing"); if (window.__ivTtsAudio === a) window.__ivTtsAudio = null; }};',
      '  a.onerror = function() {{ fail(a.error); }};',
      '  var p = a.play();',
      '  if (p && p.catch) p.catch(fail);',
      '  return true;',
      '}};'
    ].join('\\n');
    pWin.document.head.appendChild(_s);
  }})();

  var _ttsPersona = {json.dumps(_persona)};
  function ttsKey(text) {{
    return _ttsPersona + '|' + String(text || '').replace(/\\n/g, ' ').trim();
  }}
  var _lastAiAudioSrc = {json.dumps(_last_ai_audio_src)};
  if (_lastAiAudioSrc && window.parent.__ivTtsClips) {{
    window.parent.__ivTtsClips[ttsKey({json.dumps(_last_ai_text)})] = _lastAiAudioSrc;
  }}

  function stopAllSpeech() {{
    var pWin = window.parent;
    if (pWin.__ivTtsStop) {{ pWin.__ivTtsStop(); return; }}
    if (pWin.speechSynthesis) pWin.speechSynthesis.cancel();
    pWin.document.querySelectorAll('.iv-playback-row.playing').forEach(function(r) {{
      r.classList.remove('playing');
    }});
  }}

  // 자동 읽기와 "다시 듣기"가 모두 이 함수를 부른다 (호출 방식은 그대로).
  function speakText(text, msgIdx) {{
    stopAllSpeech();
    var pWin = window.parent;
    var usedMp3 = pWin.__ivTtsPlay && pWin.__ivTtsPlay(ttsKey(text), msgIdx, function() {{
      speakWithBrowserVoice(text, msgIdx);
    }});
    if (!usedMp3) speakWithBrowserVoice(text, msgIdx);
  }}

  function speakWithBrowserVoice(text, msgIdx) {{
    var pWin = window.parent;
    if (!pWin.speechSynthesis) return;
    pWin.speechSynthesis.cancel();
    if (!(pWin.speechSynthesis.getVoices() || []).length) {{
      var started = false;
      var go = function() {{
        if (started) return;
        started = true;
        pWin.speechSynthesis.removeEventListener('voiceschanged', go);
        speakWithBrowserVoiceNow(text, msgIdx);
      }};
      pWin.speechSynthesis.addEventListener('voiceschanged', go);
      setTimeout(go, 1000);
      return;
    }}
    speakWithBrowserVoiceNow(text, msgIdx);
  }}

  function speakWithBrowserVoiceNow(text, msgIdx) {{
    var pWin = window.parent;
    var row = pWin.document.querySelector('.iv-playback-row[data-msg-idx="' + msgIdx + '"]');
    var u = new (pWin.SpeechSynthesisUtterance)(text);
    u.lang = 'ko-KR';
    var voice = pickKoreanVoice(pWin);
    if (voice) u.voice = voice;
    u.rate = 1.0;   
    u.pitch = 0.8; 
    u.onstart = function() {{ if (row) row.classList.add('playing'); }};
    u.onend   = function() {{ if (row) row.classList.remove('playing'); }};
    u.onerror = function() {{ if (row) row.classList.remove('playing'); }};
    pWin.speechSynthesis.speak(u);
  }}
  (function() {{
    var tries = 0;
    function attachReplayHandlers() {{
      doc.querySelectorAll('.iv-playback-replay').forEach(function(el) {{
        el.onclick = function() {{
          var row = el.closest('.iv-playback-row');
          var idx = row ? row.getAttribute('data-msg-idx') : null;
          speakText(el.getAttribute('data-tts'), idx);
        }};
      }});
      tries++;
      if (tries < 15) setTimeout(attachReplayHandlers, 200);
    }}
    attachReplayHandlers();
  }})();

  if (!window.parent.__ivCopyGuardBound) {{
    window.parent.__ivCopyGuardBound = true;
    window.parent.addEventListener('keydown', function(e) {{
      if ((e.key === 'c' || e.key === 'C') && (e.metaKey || e.ctrlKey)) {{
        e.stopPropagation();
      }}
    }}, true);
  }}

  // ── 음성 안내 토글 ────

  if (typeof window.parent.__ivVoiceGuideOn === 'undefined') {{
    window.parent.__ivVoiceGuideOn = {str(voice_guide_on).lower()};
  }}
  var vgTrack = doc.getElementById('vg-track');
  var vgKnob  = doc.getElementById('vg-knob');
  (function() {{
    var on = window.parent.__ivVoiceGuideOn;
    if (vgTrack) vgTrack.style.background = on ? '#3b6def' : '#e5e7eb';
    if (vgKnob)  vgKnob.style.left        = on ? '18px' : '2px';
    doc.querySelectorAll('.iv-playback-block').forEach(function(b) {{
      b.style.display = on ? '' : 'none';
    }});
  }})();

  var vgToggleEl = doc.getElementById('voice-guide-toggle');
  if (vgToggleEl) {{
    vgToggleEl.onclick = function() {{
      var on = !window.parent.__ivVoiceGuideOn;
      window.parent.__ivVoiceGuideOn = on;
      var pdoc = window.parent.document;
      var t = pdoc.getElementById('vg-track');
      var k = pdoc.getElementById('vg-knob');
      if (t) t.style.background = on ? '#3b6def' : '#e5e7eb';
      if (k) k.style.left       = on ? '18px' : '2px';
      pdoc.querySelectorAll('.iv-playback-block').forEach(function(b) {{
        b.style.display = on ? '' : 'none';
      }});
      if (!on) {{
        stopAllSpeech();
      }}
    }};
  }}

  var _lastAiIdx  = {_last_ai_idx if _last_ai_idx is not None else -1};
  var _lastAiText = {json.dumps(_last_ai_text)};

  var _spokenKey = {json.dumps(str(get("session_id")))} + ':' + _lastAiIdx;
  if (window.parent.__ivVoiceGuideOn && window.parent.__ivLastSpoken !== _spokenKey) {{
    window.parent.__ivLastSpoken = _spokenKey;
    if (_lastAiText) {{
      var _autoSpoken = false;
      var _attemptAutoSpeak = function() {{
        if (_autoSpoken || !window.parent.__ivVoiceGuideOn) return;
        _autoSpoken = true;
        speakText(_lastAiText, _lastAiIdx);
      }};
      setTimeout(_attemptAutoSpeak, 300);
      doc.addEventListener('click', _attemptAutoSpeak, {{ once: true }});
    }}
  }}

  // ── 면접 종료 ─────────────────────────

  function showLoadingAndEnd(timeUpNote) {{
    // 시간이 이미 끝난 채로 화면이 열리면 아래쪽 'var doc' 할당보다 먼저 _tick에서 불린다
    var doc = window.parent.document;
    stopAllSpeech();
    if (timeUpNote && !doc.getElementById('_iv_ov') && !doc.getElementById('_iv_timeup_modal')) {{
      var modal = doc.createElement('div');
      modal.id = '_iv_timeup_modal';
      modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;' +
        'background:rgba(17,24,39,0.45);z-index:10000000;display:flex;align-items:center;justify-content:center;';
      modal.innerHTML =
        '<div style="background:white;border-radius:20px;padding:40px 44px;' +
        'box-shadow:0 4px 24px rgba(0,0,0,0.12);text-align:center;max-width:420px;width:90%;">' +
        '<div style="font-size:18px;font-weight:700;color:#111827;margin-bottom:12px;">면접이 종료되었습니다</div>' +
        '<div style="font-size:14px;color:#6b7280;line-height:1.7;margin-bottom:28px;">' +
        '{_INTERVIEW_LIMIT_MIN}분 제한 시간이 지나 면접이 자동으로 종료되었습니다.<br>' +
        '방금 작성하신 답변까지는 정상적으로 제출됐어요.</div>' +
        '<button id="_iv_timeup_ok" style="background:#3b6def;color:white;border:none;' +
        'border-radius:10px;padding:12px 32px;font-size:14px;font-weight:600;cursor:pointer;">확인</button>' +
        '</div>';
      doc.body.appendChild(modal);
      doc.getElementById('_iv_timeup_ok').onclick = function() {{
        modal.remove();
        _startEndFlow();
      }};
      return;
    }}
    _startEndFlow();
  }}

  function _startEndFlow() {{
    var vr = window.parent.__ivVideoRec;
    var hasVideoStream = !!(vr && vr.stream);

    // 화면 모양은 면접 준비 · 결과 분석 로딩과 같은 카드(components/loading_card.py)를 쓴다.
    // /end 는 백엔드 버전에 따라 리포트 생성까지 기다리기도(동기), 바로 202 로 끝나기도(비동기) 한다.
    // 어느 쪽이든 맞도록 '면접 종료 처리'로 보여 주고, 리포트 대기는 다음 화면(결과 분석 로딩)에서 안내한다.
    var _ldCheck = '<svg width="12" height="12" viewBox="0 0 256 256" aria-hidden="true">' +
      '<path d="M40 144l56 56L216 80" fill="none" stroke="#fff" stroke-width="28" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    var _ldCross = '<svg width="11" height="11" viewBox="0 0 256 256" aria-hidden="true">' +
      '<path d="M64 64l128 128M192 64L64 192" fill="none" stroke="#fff" stroke-width="28" stroke-linecap="round"/></svg>';

    if (!doc.getElementById('_iv_ov')) {{
      var sty = doc.createElement('style');
      sty.id = '_iv_sty';
      sty.textContent = {json.dumps(LOADING_CSS_TEXT)};
      doc.head.appendChild(sty);

      var ov = doc.createElement('div');
      ov.id = '_iv_ov';
      ov.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;' +
        'background:#f8fafc;z-index:9999999;display:flex;align-items:center;justify-content:center;';
      // 영상 업로드는 종료 요청과 동시에 시작되므로 처음부터 '진행 중'으로 보여 준다.
      var _videoRowHtml = hasVideoStream ?
        '<div id="_iv_ov_row_video" class="ld-li now"><span class="k"></span>영상 저장 중...</div>' : '';
      ov.innerHTML =
        '<div class="ld-wrap" style="width:100%;"><div class="ld-card">' +
        '<div class="ld-cap">WRAPPING UP</div><div class="ld-spin"></div>' +
        '<div id="_iv_ov_heading" class="ld-title">면접을 마무리하고 있어요</div>' +
        '<div id="_iv_ov_desc" class="ld-desc">답변을 정리하고 결과 분석을 준비하고 있어요.<br>잠시만 기다려 주세요.</div>' +
        '<div class="ld-list">' +
        '<div id="_iv_ov_row_end" class="ld-li now"><span class="k"></span>면접 종료 처리 중...</div>' +
        _videoRowHtml +
        '</div></div></div>';
      doc.body.appendChild(ov);
    }}

    function markDone(rowId, label, failed) {{
      var row = doc.getElementById(rowId);
      if (!row) return;
      row.className = 'ld-li ' + (failed ? 'fail' : 'done');
      row.innerHTML = '<span class="k">' + (failed ? _ldCross : _ldCheck) + '</span>' + label +
        (failed ? '' : '<span class="r">완료</span>');
    }}
    // 실패가 아니라 "아직 진행 중"인 상태 — 회색 … + 안내 문구 (빨간 ✕를 쓰지 않음)
    function markPending(rowId, label) {{
      var row = doc.getElementById(rowId);
      if (!row) return;
      row.className = 'ld-li wait';
      row.innerHTML = '<span class="k">…</span>' + label;
    }}
    function markActive(rowId, label) {{
      var row = doc.getElementById(rowId);
      if (!row || row.className.indexOf('done') !== -1 || row.className.indexOf('fail') !== -1) return;
      row.className = 'ld-li now';
      row.innerHTML = '<span class="k"></span>' + label;
    }}

    var endResolved = false, videoResolved = !hasVideoStream;
    function updateHeading() {{
      var h = doc.getElementById('_iv_ov_heading');
      var d = doc.getElementById('_iv_ov_desc');
      if (!h) return;
      if (endResolved && videoResolved) {{
        h.textContent = '결과 분석으로 넘어가요';
        if (d) d.innerHTML = '면접이 종료됐어요.<br>곧 결과 분석 화면으로 이동해요.';
      }} else if (endResolved) {{
        h.textContent = '영상을 저장하고 있어요';
        if (d) d.innerHTML = '면접이 종료됐어요.<br>영상 저장이 끝나면 바로 이동해요.';
      }} else {{
        h.textContent = '면접을 마무리하고 있어요';
      }}
    }}

    function navigate() {{
      markDone('_iv_ov_row_end', '면접 종료 처리');
      updateHeading();

      var wc = hasVideoStream ? '1' : '0';
      var input = doc.querySelector('.st-key-_iv_nav_ready input');
      if (input) {{
        var setter = Object.getOwnPropertyDescriptor(
          window.parent.HTMLInputElement.prototype, 'value'
        ).set;
        setter.call(input, 'go:' + wc);
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        input.dispatchEvent(new FocusEvent('focusout', {{ bubbles: true }}));
        input.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', bubbles: true }}));
      }}
      window.parent.eval(
        'setTimeout(function() {{' +
        '  var ov = document.getElementById("_iv_ov");' +
        '  if (ov) {{ ov.remove(); }}' +
        '  var sty = document.getElementById("_iv_sty");' +
        '  if (sty) {{ sty.remove(); }}' +
        '}}, 800);'
      );
    }}

    var _videoTimedOut = false;
    var videoDone = hasVideoStream ? new Promise(function(res) {{
      stopAndUploadVideo(function(success) {{
        if (_videoTimedOut) {{ res(); return; }}  
        videoResolved = true;
        markDone('_iv_ov_row_video', success ? '영상 저장' : '영상 저장 실패', !success);
        updateHeading();
        res();
      }});
    }}) : Promise.resolve();
    var videoTimeout = hasVideoStream ? new Promise(function(res) {{
      setTimeout(function() {{
        if (videoResolved) {{ res(); return; }}  
        console.warn('[영상] 업로드가 {_VIDEO_UPLOAD_WAIT_SEC}초 안에 끝나지 않음 — 저장은 백그라운드에서 계속되고, 결과 화면으로 먼저 진행합니다.');
        _videoTimedOut = true;
        videoResolved = true;
        markPending('_iv_ov_row_video', '영상은 백그라운드에서 계속 저장돼요');
        updateHeading();
        res();
      }}, {_VIDEO_UPLOAD_WAIT_SEC * 1000});
    }}) : Promise.resolve();
    var endDone = fetch('{api.PUBLIC_BASE_URL}/interview/sessions/' + _videoSessionId + '/end', {{
      method: 'POST',
      headers: {{ 'Authorization': 'Bearer ' + _accessToken }}
    }}).catch(function(err) {{
      console.warn('[면접 종료] 서버에 종료 알림 실패:', err);
    }}).then(function(v) {{
      endResolved = true;
      markDone('_iv_ov_row_end', '면접 종료 처리');
      if (hasVideoStream) markActive('_iv_ov_row_video', '영상 저장 중...');
      updateHeading();
      return v;
    }});
    Promise.all([endDone, Promise.race([videoDone, videoTimeout])]).then(navigate);
  }}

  window.parent.__ivShowLoadingAndEnd = showLoadingAndEnd;
  var endBtnEl = doc.getElementById('end-interview');
  if (endBtnEl) {{
    endBtnEl.onclick = function() {{
      if (endBtnEl.getAttribute('data-pending') === 'true') return;
      showLoadingAndEnd();
    }};
  }}

  // ── 마이크 (녹음 → 백엔드 STT: gpt-4o-transcribe) ──────────────────
  var hintRow  = document.getElementById('hint-row');
  var noteRow  = document.getElementById('note-row');
  var speechRateRow = document.getElementById('speech-rate-row');
  var SPEECH_LEVEL_COLOR = {{
    '빠름': {{ bg: '#fef3c7', fg: '#92400e' }},
    '적정': {{ bg: '#dcfce7', fg: '#16a34a' }},
    '느림': {{ bg: '#eef3ff', fg: '#2563eb' }}
  }};
  var MIC_OUTLINE =
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6b7280" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>' +
    '<path d="M19 10v2a7 7 0 0 1-14 0v-2"/>' +
    '<line x1="12" y1="19" x2="12" y2="22"/>' +
    '<line x1="8" y1="22" x2="16" y2="22"/>' +
    '</svg>';
  var MIC_FILLED =
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" fill="white"/>' +
    '<path d="M19 10v2a7 7 0 0 1-14 0v-2"/>' +
    '<line x1="12" y1="19" x2="12" y2="22"/>' +
    '<line x1="8" y1="22" x2="16" y2="22"/>' +
    '</svg>';

  var mediaRecorder = null;
  var audioChunks   = [];
  var micStream     = null;
  var recording     = false;
  var _recordStartedAt = 0;

  function setMicIdle() {{
    recording = false;
    mbtn.style.background  = '#f8fafc';
    mbtn.style.borderColor = '#e5e7eb';
    mbtn.innerHTML = MIC_OUTLINE;
    hintRow.style.display = 'none';
    noteRow.style.display = 'none';
    recomputeBarHeight();
  }}

  function setMicRecording() {{
    recording = true;
    mbtn.style.background  = '#3b6def';
    mbtn.style.borderColor = '#3b6def';
    mbtn.innerHTML = MIC_FILLED;
    hintRow.textContent = '녹음 중... 다시 누르면 텍스트로 변환됩니다';
    hintRow.style.display = 'block';
    noteRow.style.display = 'block';
    speechRateRow.style.display = 'none';  
    recomputeBarHeight();
  }}

  function setMicProcessing() {{
    hintRow.textContent = '음성을 텍스트로 변환하는 중...';
    recomputeBarHeight();
  }}

  function startRecording() {{
    navigator.mediaDevices.getUserMedia({{ audio: true }}).then(function(stream) {{
      micStream = stream;
      audioChunks = [];
      var _mimeCandidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
      var _chosenMime = '';
      for (var _i = 0; _i < _mimeCandidates.length; _i++) {{
        if (window.MediaRecorder.isTypeSupported && window.MediaRecorder.isTypeSupported(_mimeCandidates[_i])) {{
          _chosenMime = _mimeCandidates[_i];
          break;
        }}
      }}
      mediaRecorder = _chosenMime ? new MediaRecorder(stream, {{ mimeType: _chosenMime }}) : new MediaRecorder(stream);
      mediaRecorder.ondataavailable = function(e) {{
        if (e.data.size > 0) audioChunks.push(e.data);
      }};
      mediaRecorder.onstop = function() {{
        micStream.getTracks().forEach(function(t) {{ t.stop(); }});
        setMicProcessing();
        var actualType = mediaRecorder.mimeType || 'audio/webm';
        var ext = actualType.indexOf('mp4') !== -1 ? 'm4a'
                : actualType.indexOf('ogg') !== -1 ? 'ogg'
                : 'webm';
        var blob = new Blob(audioChunks, {{ type: actualType }});
        var formData = new FormData();
        formData.append('audio', blob, 'recording.' + ext);
        var durationSec = _recordStartedAt ? (Date.now() - _recordStartedAt) / 1000 : 0;
        formData.append('duration', String(durationSec));
        fetch('{api.PUBLIC_BASE_URL}/voice/transcribe', {{
          method: 'POST',
          headers: {{ 'Authorization': 'Bearer ' + _accessToken }},
          body: formData
        }})
          .then(function(res) {{
            if (!res.ok) throw new Error('transcribe failed: ' + res.status);
            return res.json();
          }})
          .then(function(data) {{
            var t = data.text || '';
            var prev = cta.value || '';
            var joined = prev && t ? (prev.replace(/\\s+$/, '') + ' ' + t) : (prev || t);
            cta.value = joined;
            lastInputType = 'voice';
            syncSt(joined);
            autosize();
            setMicIdle();
            if (data.speech_cpm && data.speech) {{
              var lv = SPEECH_LEVEL_COLOR[data.speech.level] || {{ bg: '#f8fafc', fg: '#6b7280' }};
              speechRateRow.innerHTML =
                '<span class="srr-badge" style="background:' + lv.bg + ';color:' + lv.fg + ';">' +
                data.speech.level + '</span><span>' + data.speech.message + '</span>';
              speechRateRow.style.display = 'flex';
            }} else {{
              speechRateRow.style.display = 'none';
            }}
            recomputeBarHeight();
          }})
          .catch(function(err) {{
            alert('음성 변환에 실패했습니다. 다시 시도해주세요.');
            setMicIdle();
          }});
      }};
      _recordStartedAt = Date.now();
      mediaRecorder.start();
      setMicRecording();
    }}).catch(function(err) {{
      alert('마이크 권한이 필요합니다.');
    }});
  }}

  function stopRecording() {{
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
      mediaRecorder.stop();
    }}
  }}

  if (navigator.mediaDevices && window.MediaRecorder) {{
    mbtn.addEventListener('click', function() {{
      if (recording) {{ stopRecording(); }}
      else {{ startRecording(); }}
    }});
  }} else {{
    mbtn.style.opacity = '0.4';
    mbtn.title = '음성 녹음 미지원';
  }}
}})();
</script>
</body></html>""", height=76, scrolling=False)

# ── 채팅 메시지 ───────────────────────────────────────────────────────────
TAG_COLORS = {
    "꼬리 질문": "#2563eb",
    "압박":      "#991b1b",
}

for i, msg in enumerate(st.session_state.iv_messages):
    if msg["role"] == "ai":
        tag   = msg.get("tag")
        text  = msg["text"]
        if tag:
            color     = TAG_COLORS.get(tag, "#374151")
            tag_span  = f'<span style="font-weight:700;color:{color};">[{tag}]</span> '
            body      = tag_span + text
        else:
            body = text
        _avatar_img = (
            f'<img src="{_avatar_src}" style="width:100%;height:100%;object-fit:cover;">'
            if _avatar_src else ""
        )

        tts_text = htmlmod.escape(text.replace("\n", " "))
        playback_html = (
            f'<div class="iv-playback-block" style="{"" if voice_guide_on else "display:none;"}">'
            '<div class="iv-playback-divider"></div>'
            f'<div class="iv-playback-row" data-msg-idx="{i}">'
            '<span class="iv-playback-status">▶  재생 중</span>'
            f'<span class="iv-playback-replay" data-tts="{tts_text}">다시 듣기</span>'
            '</div>'
            '</div>'
        )
        st.markdown(
            f'<div class="iv-ai-row">'
            f'<div class="iv-ai-avatar">{_avatar_img}</div>'
            f'<div class="iv-ai-bubble">{body}{playback_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="iv-user-row">'
            f'<div class="iv-user-bubble">{msg["text"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── 채팅 입력 ─────────────────────────────────────────────────────────────

_SELF_INTRO_MIN_CHARS = 10
_answered_count = sum(1 for m in st.session_state.iv_messages if m["role"] == "user")

if prompt := st.chat_input("답변을 입력하세요..."):
    if _answered_count == 0 and len("".join(prompt.split())) < _SELF_INTRO_MIN_CHARS:
        show_error("답변이 너무 짧습니다. 조금 더 자세히 답변해 주세요.")
    else:
        st.session_state.iv_messages.append({"role": "user", "tag": None, "text": prompt})
        st.session_state["_pending_answer"] = {
            "prompt": prompt,
            "input_type": st.session_state.get("input_type_hidden", "text"),
        }
        st.rerun()

_pending = st.session_state.get("_pending_answer")
if _pending:
    session_id = get("session_id")
    if not session_id:
        st.session_state.iv_messages.pop()
        st.session_state["_pending_answer"] = None
        show_error("면접 세션이 없습니다. 처음부터 다시 시작해주세요.")
    else:
        try:
            with st.spinner("AI가 답변을 분석하고 있습니다..."):
                resp = api.send_answer(
                    session_id, _pending["prompt"], input_type=_pending["input_type"]
                )
            st.session_state["_pending_answer"] = None
            st.session_state["realtime_score"] = resp.get("realtime_score")
            st.session_state["realtime_feedback"] = resp.get("realtime_feedback")
            st.session_state["realtime_is_rapport"] = bool(resp.get("is_rapport"))
            _iv_time_up = (time.time() - st.session_state.iv_start) >= _INTERVIEW_LIMIT_SEC
            if resp.get("question_type") == "end" or _iv_time_up:
                try:
                    api.end_session(session_id)
                except Exception:
                    pass
                state_set("interview_done", True)
            
                _iv_time_up_js = str(_iv_time_up).lower()
                components.html(f"""
                <script>
                (function () {{
                    var tries = 0;
                    function attempt() {{
                        if (window.parent.__ivShowLoadingAndEnd) {{
                            window.parent.__ivShowLoadingAndEnd({_iv_time_up_js});
                            return;
                        }}
                        tries++;
                        if (tries < 40) {{ setTimeout(attempt, 50); return; }}
                        var doc2 = window.parent.document;
                        var input = doc2.querySelector('.st-key-_iv_nav_ready input');
                        if (input) {{
                            var setter = Object.getOwnPropertyDescriptor(
                                window.parent.HTMLInputElement.prototype, 'value'
                            ).set;
                            setter.call(input, 'go:0');
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new FocusEvent('focusout', {{ bubbles: true }}));
                            input.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', bubbles: true }}));
                        }}
                    }}
                    attempt();
                }}());
                </script>
                """, height=0)
                st.stop()
            else:
                tag = "꼬리 질문" if resp.get("question_type") == "follow_up" else None
                st.session_state["_pending_next_question"] = {
                    "tag": tag, "text": resp["next_question"]
                }
                st.rerun()
        except api.SessionExpiredError:
            st.session_state.iv_messages.pop()
            st.session_state["_pending_answer"] = None
            mark_session_expired()
        except requests.exceptions.ConnectionError:
            st.session_state.iv_messages.pop()
            st.session_state["_pending_answer"] = None
            show_error("서버에 연결할 수 없습니다. 답변이 전송되지 않았습니다.")
        except requests.exceptions.Timeout:
            st.session_state.iv_messages.pop()
            st.session_state["_pending_answer"] = None
            show_error("응답 생성이 시간 초과되었습니다. 다시 시도해주세요.")
        except requests.exceptions.HTTPError as e:
            st.session_state.iv_messages.pop()
            st.session_state["_pending_answer"] = None
            show_error(api.error_detail(e, "답변 전송에 실패했습니다."))
        except Exception as e:
            st.session_state.iv_messages.pop()
            st.session_state["_pending_answer"] = None
            show_error(f"알 수 없는 오류가 발생했습니다: {e}")

_pending_q = st.session_state.get("_pending_next_question")
if _pending_q:
    time.sleep(1.2)
    st.session_state.iv_messages.append({
        "role": "ai",
        "tag":  _pending_q["tag"],
        "text": _pending_q["text"],
    })
    st.session_state["_pending_next_question"] = None
    st.rerun()

# ── 숨김 종료 버튼 ──────────
if st.button("종료", key="btn_end_interview"):
    st.switch_page("pages/05_결과리포트.py")

render_session_expired_banner()
