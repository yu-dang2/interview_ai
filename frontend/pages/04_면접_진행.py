import math
import time
import base64
import json
import html as htmlmod
import requests
import streamlit as st
import streamlit.components.v1 as components
from utils.paths import resource
from components.sidebar import render_sidebar
from utils.state import init_session, get, set as state_set
from utils import api

st.set_page_config(
    page_title="면접 진행 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()

if "iv_messages" not in st.session_state:
    session_id = get("session_id")
    first_q    = get("first_question")

    if not session_id:
        resume_id = get("resume_id") or 0
        jd_id     = get("jd_id") or 0
        persona   = get("interviewer_style") or "기술 리드"
        try:
            with st.spinner("면접을 준비하는 중..."):
                resp = api.start_interview(resume_id, jd_id, persona)
            state_set("session_id", resp["session_id"])
            first_q = resp["first_question"]
            state_set("first_question", first_q)
        except requests.exceptions.ConnectionError:
            st.error("서버에 연결할 수 없습니다. 백엔드 서버가 켜져 있는지 확인해주세요.")
            st.stop()
        except requests.exceptions.Timeout:
            st.error("면접 준비 요청이 시간 초과되었습니다. 잠시 후 다시 시도해주세요.")
            st.stop()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            st.error(f"면접 준비에 실패했습니다. (서버 오류: {status})")
            st.stop()
        except Exception as e:
            st.error(f"면접 준비 중 알 수 없는 오류가 발생했습니다: {e}")
            st.stop()

    st.session_state.iv_messages = [
        {"role": "ai", "tag": None, "text": first_q or "안녕하세요, 면접을 시작하겠습니다."},
    ]

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

render_sidebar(active="면접 시작")

# ── 레이아웃 ──────────────────────────────────────────────────────────────
FEEDBACK_W = 288
right_px   = FEEDBACK_W

# ── 타이머 초기값 ────────────────────────────
elapsed   = int(time.time() - st.session_state.iv_start)
remaining = max(0, 30 * 60 - elapsed)
timer_str = f"{remaining // 60:02d}:{remaining % 60:02d}"

# ── 데이터 ───────────────────────────────────────────────────────────────
TOTAL  = 72
SCORES = [("논리성", 78), ("커뮤니케이션", 82), ("전문 지식", 65), ("태도", 71), ("문제 해결력", 75)]
VIDEO_METRICS = [("시선 처리", 76, "#3b6def")]

R = 40; cx = cy = 52
circ = 2 * math.pi * R
fill = circ * TOTAL / 100
donut_svg = (
    f'<svg width="108" height="108" viewBox="0 0 104 104">'
    f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#e5e7eb" stroke-width="10"/>'
    f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#3b6def" stroke-width="10"'
    f' stroke-dasharray="{fill:.1f} {circ - fill:.1f}"'
    f' transform="rotate(-90 {cx} {cy})" stroke-linecap="round"/>'
    f'<text x="{cx}" y="{cy + 7}" text-anchor="middle" font-size="22" font-weight="700"'
    f' fill="#1f1f1f" font-family="sans-serif">{TOTAL}</text>'
    f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" font-size="10"'
    f' fill="#9ca3af" font-family="sans-serif">/100</text>'
    f'</svg>'
)

scores_html = ""
for label, score in SCORES:
    scores_html += (
        f'<div style="display:flex;justify-content:space-between;font-size:12px;'
        f'color:#1f1f1f;margin-bottom:4px;">'
        f'<span>{label}</span>'
        f'<span style="font-weight:600;color:#3b6def;">{score}</span></div>'
        f'<div style="background:#edeef0;border-radius:3px;height:5px;margin-bottom:14px;">'
        f'<div style="width:{score}%;background:#3b6def;height:5px;border-radius:3px;"></div></div>'
    )

video_bars_html = ""
for label, score, color in VIDEO_METRICS:
    video_bars_html += (
        f'<div style="display:flex;justify-content:space-between;font-size:12px;'
        f'color:#1f1f1f;margin-bottom:6px;">'
        f'<span style="font-weight:500;">{label}</span>'
        f'<span style="font-weight:700;color:{color};">{score}</span></div>'
        f'<div style="background:#edeef0;border-radius:3px;height:6px;margin-bottom:18px;">'
        f'<div style="width:{score}%;background:{color};height:6px;border-radius:3px;"></div></div>'
    )

# ── CSS ──────────────────────────────────────────────────────────────────
st.markdown(f"""<style>
[data-testid="stMain"] {{ padding-right: {right_px}px !important; }}
[data-testid="stMainBlockContainer"] {{ padding: 20px {right_px + 24}px 140px 240px !important; }}
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

.iv-ai-row {{ display:flex; align-items:flex-start; gap:12px; margin-bottom:28px; }}
.iv-ai-avatar {{
    width:36px; height:36px; border-radius:50%; background:#3b6def;
    flex-shrink:0; margin-top:2px; overflow:hidden;
}}
.iv-ai-bubble {{
    background:white; border-radius:4px 14px 14px 14px;
    padding:14px 16px; font-size:13px; color:#1f1f1f; line-height:1.65;
    box-shadow:0 1px 4px rgba(0,0,0,0.08); max-width:540px; white-space:pre-wrap;
}}
.iv-user-row {{ display:flex; justify-content:flex-end; margin-bottom:28px; }}
.iv-user-bubble {{
    background:#f1f3f9; border-radius:14px 4px 14px 14px;
    padding:14px 16px; font-size:13px; color:#1f1f1f; line-height:1.65;
    max-width:540px; white-space:pre-wrap;
}}

.iv-playback-divider {{ height:1px; background:#e0e0e6; margin:10px 0 8px; }}
.iv-playback-row {{ display:flex; justify-content:flex-end; align-items:center; }}
.iv-playback-row.playing {{ justify-content:space-between; }}
.iv-playback-status {{ display:none; font-size:12px; font-weight:600; color:#3b6def; }}
.iv-playback-row.playing .iv-playback-status {{ display:inline; }}
.iv-playback-replay {{
    font-size:12px; color:#8c8c8c; text-decoration:underline; cursor:pointer;
}}
</style>""", unsafe_allow_html=True)

# ── 헤더 우측 ─────────────────────────────────
_vg_track_bg  = '#3b6def' if voice_guide_on else '#d1d5db'
_vg_knob_left = '18px'    if voice_guide_on else '2px'

st.markdown(
    f'<div style="position:fixed;top:0;right:0;height:60px;'
    f'display:flex;align-items:center;gap:10px;padding:0 20px;z-index:99999;">'
    f'<div id="voice-guide-toggle" style="display:flex;align-items:center;gap:8px;'
    f'background:#eff6ff;border-radius:16px;height:32px;padding:0 12px;cursor:pointer;">'
    f'<span style="font-size:13px;font-weight:600;color:#3b6def;">음성 안내</span>'
    f'<div id="vg-track" style="width:36px;height:20px;border-radius:10px;background:{_vg_track_bg};'
    f'position:relative;transition:background 0.15s;">'
    f'<div id="vg-knob" style="width:16px;height:16px;border-radius:50%;background:white;'
    f'position:absolute;top:2px;left:{_vg_knob_left};transition:left 0.15s;"></div>'
    f'</div></div>'
    f'<div style="display:flex;align-items:center;gap:6px;background:#fff5f5;'
    f'border-radius:8px;height:34px;padding:0 14px;">'
    f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#dc2626"'
    f' stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/>'
    f'<polyline points="12 6 12 12 16 14"/></svg>'
    f'<span id="iv-timer" style="font-size:13px;font-weight:700;color:#dc2626;">{timer_str}</span>'
    f'</div>'
    f'<div id="end-interview" style="background:#dc2626;color:white;font-size:13px;font-weight:600;'
    f'height:34px;display:flex;align-items:center;padding:0 16px;'
    f'border-radius:8px;cursor:pointer;">'
    f'면접 종료</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── 피드백 패널 ───────────────────────────
person_svg = (
    '<svg width="100%" height="100%" viewBox="0 0 288 210" preserveAspectRatio="xMidYMid slice"'
    ' xmlns="http://www.w3.org/2000/svg">'
    '<rect width="288" height="210" fill="#12151e"/>'
    '<circle cx="144" cy="74" r="30" fill="#4d5973"/>'
    '<rect x="108" y="110" width="72" height="52" rx="5" fill="#4d5973"/>'
    '</svg>'
)

_webcam_display = "" if webcam_on else "display:none;"
webcam_html = (
    f'<div id="webcam-preview-block" style="width:100%;height:210px;overflow:hidden;{_webcam_display}">'
    + person_svg
    + '</div>'
    f'<div id="webcam-preview-divider" style="height:1px;background:#e5e8ec;margin-bottom:16px;{_webcam_display}"></div>'
)

st.markdown(
    '<div style="position:fixed;top:60px;right:0;width:288px;'
    'height:calc(100vh - 60px);background:white;border-left:1px solid #e5e8ec;'
    'overflow-y:auto;z-index:300;box-sizing:border-box;">'
    + webcam_html
    + '<div style="padding:16px 18px 20px;">'
    '<div style="font-size:14px;font-weight:600;color:#1f1f1f;margin-bottom:2px;">실시간 피드백</div>'
    '<div style="font-size:12px;color:#6b7280;margin-bottom:16px;">AI가 분석 중입니다</div>'
    '<div style="display:flex;flex-direction:column;align-items:center;margin-bottom:8px;">'
    + donut_svg
    + '<div style="font-size:12px;font-weight:500;color:#1f1f1f;margin-top:4px;">현재 점수</div>'
    '<div style="font-size:11px;color:#3b6def;font-weight:500;">상위 28%</div>'
    '</div>'
    '<div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:12px;">세부 평가 항목</div>'
    + scores_html
    + '<div style="font-size:13px;font-weight:600;color:#1f1f1f;margin-bottom:10px;">AI 실시간 피드백</div>'
    '<div style="background:#f7f8fc;border-radius:8px;padding:10px 12px;margin-bottom:6px;font-size:12px;color:#374151;">'
    '✓ 답변 구조가 명확합니다</div>'
    '<div style="background:#f7f8fc;border-radius:8px;padding:10px 12px;margin-bottom:6px;font-size:12px;color:#374151;">'
    '✓ 전문 용어 사용이 적절합니다</div>'
    '<div style="background:#fffbeb;border-radius:8px;padding:10px 12px;font-size:12px;color:#92400e;">'
    '💡 조금 더 구체적인 예시를 추가해보세요</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.text_input("input_type", value="text", key="input_type_hidden", label_visibility="collapsed")

# ── 커스텀 입력바 ─────────────────
_cam_bg = '#3b6def' if webcam_on else '#f3f4f6'
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
  background:white;border-top:1px solid #f3f4f6;
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
#controls-row{{
  display:flex;align-items:center;padding:16px 20px;
}}
#ta-wrap{{flex:1;margin-right:12px;}}
#cta{{
  display:block;width:100%;height:44px;min-height:44px;max-height:120px;
  border:1px solid #e5e7eb;border-radius:14px;
  background:#f9fafb;font-size:14px;color:#1f1f1f;
  padding:11px 21px;resize:none;outline:none;
  font-family:inherit;line-height:20px;overflow-y:auto;
}}
#cta::placeholder{{color:#9ca3af;}}
#cta:focus{{border-color:#e5e7eb;background:#f9fafb;box-shadow:none;}}
.ibtn{{
  width:40px;height:40px;border-radius:8px;
  border:1.5px solid #e5e7eb;background:#f3f4f6;
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;flex-shrink:0;user-select:none;
}}
#sbtn{{background:#3b6def;border-color:#3b6def;}}
#mbtn{{margin-left:8px;}}
#cbtn{{background:{_cam_bg};border-color:{_cam_bd};margin-left:8px;}}
</style></head><body>
<div id="hint-row">음성 인식 중... 말씀하신 내용이 아래에 입력됩니다</div>
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
<script>
(function(){{
  // ── 실시간 타이머 ────────────────────────────────────────────────
  var _startSec = {int(st.session_state.iv_start)};
  function _tick() {{
    var rem = Math.max(0, 30*60 - Math.floor(Date.now()/1000 - _startSec));
    var el  = window.parent.document.getElementById('iv-timer');
    if (el) el.textContent =
      String(Math.floor(rem/60)).padStart(2,'0') + ':' +
      String(rem%60).padStart(2,'0');
  }}
  _tick();
  setInterval(_tick, 1000);

  var fr = window.frameElement;
  var barHeight = 76;
  function applyFixed() {{
    if (!fr) return;
    fr.style.position = 'fixed';
    fr.style.bottom   = '0';
    fr.style.left     = '220px';
    fr.style.width    = 'calc(100vw - 220px - {right_px}px)';
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
  function recomputeBarHeight() {{
    requestAnimationFrame(function() {{
      var h = controlsRowEl.offsetHeight;
      if (hintRowEl.style.display !== 'none') h += hintRowEl.offsetHeight;
      if (noteRowEl.style.display !== 'none') h += noteRowEl.offsetHeight;
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
    syncInputType(lastInputType);
    syncSt(cta.value);
    setTimeout(function() {{
      var btn = doc.querySelector('[data-testid="stChatInputSubmitButton"]');
      if (btn) {{ btn.click(); cta.value = ''; }}
      lastInputType = 'text';
      autosize();
    }}, 50);
  }}
  cta.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); send(); }}
  }});
  sbtn.addEventListener('click', send);

  // ── 카메라 토글 ──────
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
  cbtn.addEventListener('click', function() {{
    webcamOn = !webcamOn;
    cbtn.innerHTML = webcamOn ? CAM_FILLED : CAM_OUTLINE;
    cbtn.style.background  = webcamOn ? '#3b6def' : '#f3f4f6';
    cbtn.style.borderColor = webcamOn ? '#3b6def' : '#e5e7eb';
    var pv = doc.getElementById('webcam-preview-block');
    var pd = doc.getElementById('webcam-preview-divider');
    if (pv) pv.style.display = webcamOn ? '' : 'none';
    if (pd) pd.style.display = webcamOn ? '' : 'none';
  }});

  // ── AI 질문 음성 안내 (백엔드 TTS: gpt-4o-mini-tts) ────────
  var _accessToken = {json.dumps(_access_token)};
  var _ttsAudio = null;
  function stopSpeaking() {{
    if (_ttsAudio) {{ _ttsAudio.pause(); _ttsAudio = null; }}
    doc.querySelectorAll('.iv-playback-row.playing').forEach(function(r) {{
      r.classList.remove('playing');
    }});
  }}
  function speakText(text, msgIdx) {{
    stopSpeaking();
    var row = doc.querySelector('.iv-playback-row[data-msg-idx="' + msgIdx + '"]');
    fetch('{api.BASE_URL}/voice/speak', {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + _accessToken
      }},
      body: JSON.stringify({{ text: text }})
    }})
      .then(function(res) {{
        if (!res.ok) throw new Error('speak failed: ' + res.status);
        return res.blob();
      }})
      .then(function(blob) {{
        var url = URL.createObjectURL(blob);
        var audio = new Audio(url);
        _ttsAudio = audio;
        audio.onplay  = function() {{ if (row) row.classList.add('playing'); }};
        audio.onended = function() {{ if (row) row.classList.remove('playing'); URL.revokeObjectURL(url); }};
        audio.onerror = function() {{ if (row) row.classList.remove('playing'); URL.revokeObjectURL(url); }};
        audio.play();
      }})
      .catch(function(err) {{
        if (row) row.classList.remove('playing');
      }});
  }}
  doc.addEventListener('click', function(e) {{
    var el = e.target && e.target.closest && e.target.closest('.iv-playback-replay');
    if (el) {{
      var row = el.closest('.iv-playback-row');
      var idx = row ? row.getAttribute('data-msg-idx') : null;
      speakText(el.getAttribute('data-tts'), idx);
    }}
  }});

  // ── 음성 안내 토글 ────
  var voiceGuideOn = {str(voice_guide_on).lower()};
  var vgTrack = doc.getElementById('vg-track');
  var vgKnob  = doc.getElementById('vg-knob');
  doc.addEventListener('click', function(e) {{
    if (e.target && e.target.closest && e.target.closest('#voice-guide-toggle')) {{
      voiceGuideOn = !voiceGuideOn;
      if (vgTrack) vgTrack.style.background = voiceGuideOn ? '#3b6def' : '#d1d5db';
      if (vgKnob)  vgKnob.style.left        = voiceGuideOn ? '18px' : '2px';
      doc.querySelectorAll('.iv-playback-block').forEach(function(b) {{
        b.style.display = voiceGuideOn ? '' : 'none';
      }});
      if (!voiceGuideOn) {{
        stopSpeaking();
        doc.querySelectorAll('.iv-playback-row.playing').forEach(function(r) {{
          r.classList.remove('playing');
        }});
      }}
    }}
  }});

  var _lastAiIdx  = {_last_ai_idx if _last_ai_idx is not None else -1};
  var _lastAiText = {json.dumps(_last_ai_text)};
  if (voiceGuideOn && window.parent.__ivLastSpoken !== _lastAiIdx) {{
    window.parent.__ivLastSpoken = _lastAiIdx;
    if (_lastAiText) speakText(_lastAiText, _lastAiIdx);
  }}

  // ── 면접 종료 ─────────────────────────
  function showLoadingAndEnd() {{
    if (!doc.getElementById('_iv_ov')) {{
      var sty = doc.createElement('style');
      sty.id = '_iv_sty';
      sty.textContent = '@keyframes _ivspin {{ to {{ transform: rotate(360deg); }} }}' +
        '#_iv_sp {{ animation: _ivspin 0.9s linear infinite; }}';
      doc.head.appendChild(sty);

      var ov = doc.createElement('div');
      ov.id = '_iv_ov';
      ov.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;' +
        'background:#f3f4f6;z-index:9999999;display:flex;align-items:center;justify-content:center;';
      ov.innerHTML =
        '<div style="background:white;border-radius:20px;padding:52px 56px;' +
        'box-shadow:0 4px 24px rgba(0,0,0,0.08);text-align:center;max-width:480px;width:90%;">' +
        '<div id="_iv_sp" style="width:52px;height:52px;border:4px solid #e5e7eb;' +
        'border-top-color:#3b6def;border-radius:50%;margin:0 auto 28px;"></div>' +
        '<div style="font-size:20px;font-weight:700;color:#1f1f1f;margin-bottom:12px;">' +
        '결과를 분석하고 있습니다</div>' +
        '<div style="font-size:14px;color:#6b7280;line-height:1.7;margin-bottom:32px;">' +
        '면접 답변을 AI가 종합 분석 중입니다.<br>잠시만 기다려 주세요.</div>' +
        '<div style="text-align:left;display:inline-block;">' +
        '<div style="font-size:13px;color:#374151;margin-bottom:10px;">● 답변 내용 분석 중...</div>' +
        '<div style="font-size:13px;color:#374151;margin-bottom:10px;">● 역량 점수 산출 중...</div>' +
        '<div style="font-size:13px;color:#374151;">● 개선 피드백 생성 중...</div>' +
        '</div></div>';
      doc.body.appendChild(ov);
    }}
    setTimeout(function() {{
      var wc = webcamOn ? '1' : '0';
      var s = doc.createElement('script');
      s.textContent = "window.location.href = window.location.origin + '/결과리포트?webcam_on=" + wc + "';";
      doc.head.appendChild(s);
    }}, 5000);
  }}
  doc.addEventListener('click', function(e) {{
    if (e.target && e.target.closest && e.target.closest('#end-interview')) {{
      showLoadingAndEnd();
    }}
  }});

  // ── 마이크 (녹음 → 백엔드 STT: gpt-4o-transcribe) ──────────────────
  var hintRow  = document.getElementById('hint-row');
  var noteRow  = document.getElementById('note-row');
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

  function setMicIdle() {{
    recording = false;
    mbtn.style.background  = '#f3f4f6';
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
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = function(e) {{
        if (e.data.size > 0) audioChunks.push(e.data);
      }};
      mediaRecorder.onstop = function() {{
        micStream.getTracks().forEach(function(t) {{ t.stop(); }});
        setMicProcessing();
        var blob = new Blob(audioChunks, {{ type: 'audio/webm' }});
        var formData = new FormData();
        formData.append('audio', blob, 'recording.webm');
        fetch('{api.BASE_URL}/voice/transcribe', {{
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
            cta.value = t;
            lastInputType = 'voice';
            syncSt(t);
            autosize();
            setMicIdle();
          }})
          .catch(function(err) {{
            alert('음성 변환에 실패했습니다. 다시 시도해주세요.');
            setMicIdle();
          }});
      }};
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
    "꼬리 질문": "#1d4ed8",
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

        tts_text = htmlmod.escape(text)
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
if prompt := st.chat_input("답변을 입력하세요..."):
    st.session_state.iv_messages.append({"role": "user", "tag": None, "text": prompt})

    answer_input_type = st.session_state.get("input_type_hidden", "text")

    session_id = get("session_id")
    if not session_id:
        st.session_state.iv_messages.pop()
        st.error("면접 세션이 없습니다. 처음부터 다시 시작해주세요.")
    else:
        try:
            resp = api.send_answer(session_id, prompt, input_type=answer_input_type)
            if resp.get("question_type") == "end":
                state_set("interview_done", True)
                st.switch_page("pages/05_결과리포트.py")
            else:
                tag = "꼬리 질문" if resp.get("question_type") == "follow_up" else None
                st.session_state.iv_messages.append({
                    "role": "ai",
                    "tag":  tag,
                    "text": resp["next_question"],
                })
                st.rerun()
        except requests.exceptions.ConnectionError:
            st.session_state.iv_messages.pop()
            st.error("서버에 연결할 수 없습니다. 답변이 전송되지 않았습니다.")
        except requests.exceptions.Timeout:
            st.session_state.iv_messages.pop()
            st.error("응답 생성이 시간 초과되었습니다. 다시 시도해주세요.")
        except requests.exceptions.HTTPError as e:
            st.session_state.iv_messages.pop()
            status = e.response.status_code if e.response is not None else "?"
            st.error(f"답변 전송에 실패했습니다. (서버 오류: {status})")
        except Exception as e:
            st.session_state.iv_messages.pop()
            st.error(f"알 수 없는 오류가 발생했습니다: {e}")

# ── 숨김 종료 버튼 ──────────
if st.button("종료", key="btn_end_interview"):
    st.switch_page("pages/05_결과리포트.py")
