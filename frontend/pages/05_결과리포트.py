import html
import math
import os
import time
from datetime import datetime

import requests
import streamlit as st
from utils.brand import FAVICON
from components.sidebar import render_sidebar
from components.report_cover import COVER_CSS, cover_html, score_bottom, stats_bottom
from utils.state import init_session, get, set as state_set, mark_session_expired, render_session_expired_banner, ensure_latest_session_id
from utils.ui import show_error_once
from utils import api

try:
    _VIDEO_RESULT_WAIT_SEC = min(600, max(10, int(os.getenv("VIDEO_RESULT_WAIT_SEC", "120"))))
except ValueError:
    _VIDEO_RESULT_WAIT_SEC = 120
_VIDEO_RESULT_WAIT_TRIES = _VIDEO_RESULT_WAIT_SEC // 3

st.set_page_config(
    page_title="결과 리포트 | intro",
    page_icon=FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()

if "webcam_on" in st.query_params:
    st.session_state.webcam_on = st.query_params["webcam_on"] == "1"

_sid_param = st.query_params.get("sid")
if _sid_param and _sid_param != get("session_id"):
    state_set("session_id", _sid_param)
    state_set("result", None)

ensure_latest_session_id()

render_sidebar(active="결과 리포트")

# ── 결과 데이터 ────────────────────────────────────────────────────────────
result_data = get("result")
session_id  = get("session_id")

if result_data and result_data.get("session_id") != session_id:
    result_data = None
    state_set("result", None)

if not result_data and session_id:
    with st.spinner("AI가 면접 답변을 종합 분석해 리포트를 만들고 있습니다. 잠시만 기다려 주세요."):
        try:
            result_data = api.get_result(session_id)
            state_set("result", result_data)
        except api.SessionExpiredError:
            mark_session_expired()
        except Exception:
            result_data = None

CATEGORIES = ["논리성", "커뮤니케이션", "전문지식", "태도", "문제해결력"]
_CAT_KEYS  = ["logic", "communication", "expertise", "attitude", "problem_solving"]

if result_data:
    radar       = result_data.get("radar_chart", {})
    summary_obj = result_data.get("summary", {})
    MY_SCORES   = [radar.get(key, 0) or 0 for key in _CAT_KEYS]
    _cat_comments = result_data.get("radar_comments") or {}
    COMMENTS    = [_cat_comments.get(key) or "" for key in _CAT_KEYS]
    SUMMARY     = [
        ("강점",      "s", "ph-thumbs-up", summary_obj.get("strength", "")),
        ("개선할 점", "i", "ph-wrench",    summary_obj.get("improvement", "")),
        ("추천",      "r", "ph-compass",   summary_obj.get("recommendation", "")),
    ]
    persona_str         = result_data.get("persona") or get("interviewer_style") or "기술 리드"
    resume_score_val    = result_data.get("resume_score", 0) or 0
    interview_score_val = result_data.get("interview_score", 0) or 0
    total_score_val     = result_data.get("total_score", 0) or 0
    grade_val           = result_data.get("grade") or "-"
else:
    show_error_once("결과를 불러오지 못했습니다. 면접을 끝까지 완료한 뒤 다시 시도해주세요.", "result_fetch_failed")
    MY_SCORES   = [0, 0, 0, 0, 0]
    COMMENTS    = [""] * 5
    SUMMARY     = []
    persona_str = get("interviewer_style") or "기술 리드"
    resume_score_val    = 0
    interview_score_val = 0
    total_score_val     = 0
    grade_val           = "-"

# ── 지난 면접 기록 (마이페이지와 같은 API) ─────────────────────────────────
# 점수 변화 그래프와 '지난 면접보다 ▲' 표시에만 쓴다. 불러오지 못해도 리포트는 그대로 보여준다.
history = []          # 오래된 순, 이번 면접까지
session_date = None
if result_data:
    try:
        _sessions = api.get_my_sessions(limit=20).get("sessions") or []
    except api.SessionExpiredError:
        _sessions = []
        mark_session_expired()
    except Exception:
        _sessions = []
    for _s in _sessions:
        if _s.get("total_score") is None:
            continue
        try:
            _dt = datetime.fromisoformat(str(_s.get("created_at", "")).replace("Z", "+00:00"))
        except ValueError:
            _dt = None
        history.append({
            "sid":    _s.get("session_id"),
            "dt":     _dt,
            "resume": _s.get("resume_score"),
            "iv":     _s.get("interview_score"),
            "total":  _s.get("total_score"),
        })
    history.sort(key=lambda h: h["dt"].replace(tzinfo=None) if h["dt"] else datetime.min)
    _cur_idx = next((i for i, h in enumerate(history) if h["sid"] == session_id), None)
    if _cur_idx is not None:
        session_date = history[_cur_idx]["dt"]
        history = history[: _cur_idx + 1]
    else:
        history.append({"sid": session_id, "dt": None, "resume": resume_score_val,
                        "iv": interview_score_val, "total": total_score_val})
    history = history[-4:]

prev = history[-2] if len(history) >= 2 else None

_d = session_date or datetime.now()
date_str = f"{_d.month}월 {_d.day}일"


# ── 공통 함수 ──────────────────────────────────────────────────────────────

def _esc(text) -> str:
    return html.escape(str(text or "")).replace("\r\n", "\n").replace("\n", "<br>")

def _grade_color(score) -> str:
    if score >= 80: return '#16a34a'   # 우수
    if score >= 65: return '#d97706'   # 보통
    return '#cf5e96'                   # 개선 필요


def _grade_badge(score) -> str:
    if score >= 80: return "우수"
    if score >= 65: return "보통"
    return "개선 필요"


def _ring_svg(score, size=62, stroke=6) -> str:
    color = _grade_color(score)
    r = (size - stroke) / 2
    c = size / 2
    circ = 2 * math.pi * r
    fill = circ * max(0, min(100, score)) / 100
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" style="flex-shrink:0">'
        f'<circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="#eef0f3" stroke-width="{stroke}"/>'
        f'<circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}" '
        f'stroke-dasharray="{fill:.2f} {circ - fill:.2f}" stroke-linecap="round" transform="rotate(-90 {c} {c})"/>'
        f'<text x="{c}" y="{c + 5.5}" text-anchor="middle" font-size="16" font-weight="800" fill="#111827" '
        f'font-family="inherit">{score}</text></svg>'
    )


def _delta_html(cur, before) -> str:
    if before is None:
        return ""
    diff = cur - before
    if diff > 0:
        return f' · <b style="color:#16a34a">▲ {diff}</b>'
    if diff < 0:
        return f' · <b style="color:#cf5e96">▼ {-diff}</b>'
    return ' · 변동 없음'


def _radar_svg(scores) -> str:
    cx, cy, R = 150, 140, 104
    n = len(scores)
    def pt(i, ratio):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        return cx + R * ratio * math.cos(ang), cy + R * ratio * math.sin(ang)
    grid = ""
    for ratio in (1.0, 0.5):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, ratio) for i in range(n)))
        grid += f'<polygon points="{pts}" fill="none" stroke="#e5e7eb"/>'
    spokes = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{pt(i, 1)[0]:.1f}" y2="{pt(i, 1)[1]:.1f}" stroke="#f1f3f7"/>' for i in range(n)
    )
    data = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, max(0, min(100, s)) / 100) for i, s in enumerate(scores)))
    labels = ""
    for i, (cat, s) in enumerate(zip(CATEGORIES, scores)):
        x, y = pt(i, 1.18)
        anchor = "middle" if abs(x - cx) < 10 else ("start" if x > cx else "end")
        labels += (f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="{anchor}" font-size="12" font-weight="700" '
                   f'fill="#374151" font-family="inherit">{cat} {s}</text>')
    return (
        f'<svg width="100%" height="320" viewBox="-62 0 424 290">{grid}{spokes}'
        f'<polygon points="{data}" fill="rgba(59,109,239,.16)" stroke="#3b6def" stroke-width="2.5"/>{labels}</svg>'
    )


def _trend_svg(points) -> str:
    """points: [(라벨, 점수, 이번 면접인지)] — 오래된 순"""
    W, H, L, Rr, top, bottom = 680, 200, 40, 660, 30, 150
    # 아래 끝을 점수에 맞춰 내린다 (50 고정이면 50 미만 점수가 전부 같은 높이로 눌려 보인다)
    lo = max(0, min(50, (min(p[1] for p in points) - 5) // 10 * 10)) if points else 50
    hi = 100
    def y(v): return bottom - (max(lo, min(hi, v)) - lo) / (hi - lo) * (bottom - top)
    n = len(points)
    xs = [L + 40 + (Rr - L - 80) * (i / (n - 1) if n > 1 else 0.5) for i in range(n)]
    ticks = (90, 75, 60) if lo >= 50 else tuple(t for t in (80, 60, 40, 20) if t > lo)
    grid = "".join(
        f'<line x1="{L}" y1="{y(v):.1f}" x2="{Rr}" y2="{y(v):.1f}" stroke="#eef0f4"/>'
        f'<text x="0" y="{y(v) + 4:.1f}" font-size="11" fill="#9ca3af" font-family="inherit">{v}</text>'
        for v in ticks
    )
    # '보통 65 이상' 글자는 제목 옆 범례로 옮겼다 (그래프 안에 두면 이번 점수 라벨과 겹친다)
    guide = f'<line x1="{L}" y1="{y(65):.1f}" x2="{Rr}" y2="{y(65):.1f}" stroke="#d97706" stroke-dasharray="4 4"/>'
    path = " ".join(f'{"M" if i == 0 else "L"} {xs[i]:.1f} {y(p[1]):.1f}' for i, p in enumerate(points))
    dots = ""
    for i, (label, v, is_cur) in enumerate(points):
        if is_cur:
            dots += (f'<circle cx="{xs[i]:.1f}" cy="{y(v):.1f}" r="7" fill="#3b6def"/>'
                     f'<text x="{xs[i]:.1f}" y="{y(v) - 16:.1f}" text-anchor="middle" font-size="13" font-weight="800" '
                     f'fill="#2f5bd8" font-family="inherit" stroke="#fff" stroke-width="4" paint-order="stroke">{label} {v}</text>')
        else:
            dots += (f'<circle cx="{xs[i]:.1f}" cy="{y(v):.1f}" r="5" fill="#fff" stroke="#3b6def" stroke-width="3"/>'
                     f'<text x="{xs[i]:.1f}" y="{y(v) + 25:.1f}" text-anchor="middle" font-size="12" fill="#4b5563" '
                     f'font-family="inherit" stroke="#fff" stroke-width="4" paint-order="stroke">{label} · {v}</text>')
    return (f'<svg width="100%" viewBox="0 0 {W} {H}" style="display:block;height:auto;min-height:150px">{grid}{guide}'
            f'<path d="{path}" fill="none" stroke="#3b6def" stroke-width="3"/>{dots}</svg>')


# ── CSS ───────────────────────────────────────────────────────────────────
st.markdown(COVER_CSS, unsafe_allow_html=True)
st.markdown("""<style>
[data-testid="stMainBlockContainer"] {
    padding: 32px 40px 60px 40px !important;
    max-width: 1240px !important;
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
}
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stHorizontalBlock"] { gap: 22px !important; align-items: flex-start !important; }

.rr-hero { display: grid; grid-template-columns: 360px 1fr; gap: 20px; margin-bottom: 24px; }
.rr-side { display: grid; grid-template-rows: auto 1fr; gap: 14px; }
.rr-card { background: #fff; border: 1px solid #e9ecf2; border-radius: 18px; padding: 22px 24px; }
.rr-kpis { display: grid; grid-template-columns: repeat(3, 1fr); padding: 18px 6px; }
.rr-kpi { display: flex; gap: 14px; align-items: center; padding: 0 16px; }
.rr-kpi + .rr-kpi { border-left: 1px solid #eef0f4; }
.rr-kpi small { display: block; font-size: 11px; font-weight: 800; letter-spacing: .05em; }
.rr-kpi .kt { margin: 3px 0 2px; font-size: 14px; color: #111827; padding: 0; }
.rr-kpi p { margin: 0; font-size: 12px; color: #6b7280; }
.rr-trend .tt { margin: 0 0 4px; font-size: 16px; display: flex; justify-content: space-between; color: #111827; padding: 0; }
.rr-trend .tt span { font-size: 12px; color: #6b7280; font-weight: 500; }
.rr-trend p { margin: 0; font-size: 13px; color: #6b7280; }
.rr-empty { display: flex; align-items: center; justify-content: center; text-align: center; height: 150px;
    font-size: 13px; color: #9ca3af; line-height: 1.7; }

.st-key-rr_toc { background: #fff; border: 1px solid #e9ecf2; border-radius: 16px; padding: 16px 12px; }
.rr-toc .th { margin: 0 0 8px 8px; font-size: 11px; letter-spacing: .1em; color: #9ca3af; padding: 0; }
.rr-toc a { display: flex; justify-content: space-between; padding: 10px; border-radius: 8px; font-size: 14px;
    color: #4b5563 !important; text-decoration: none !important; }
.rr-toc a:hover { background: #eef3ff; color: #2f5bd8 !important; }
.rr-toc a span { color: #9ca3af; font-size: 12px; }
.rr-toc .line { border-top: 1px solid #eef0f4; margin: 10px 0 12px; }
.st-key-rr_toc [data-testid="stButton"], .st-key-rr_toc [data-testid="stElementContainer"] { width: 100% !important; }
.st-key-rr_toc [data-testid="stButton"] { margin-bottom: 8px; }
.st-key-rr_toc [data-testid="stButton"] button { width: 100% !important; border-radius: 10px !important; min-height: 42px !important; }
.st-key-rr_toc [data-testid="stButton"] p { white-space: nowrap !important; font-weight: 700 !important; font-size: 13.5px !important; }

.rr-sec { background: #fff; border: 1px solid #e9ecf2; border-radius: 18px; padding: 26px 28px; margin-bottom: 16px; scroll-margin-top: 20px; }
.rr-sec .sh { font-size: 20px; margin: 0 0 4px; display: flex; gap: 10px; align-items: center; color: #111827; padding: 0; }
.rr-sec .sh .n { font-size: 12px; color: #3b6def; background: #eef3ff; border-radius: 7px; padding: 3px 8px; }
.rr-sec .d { margin: 0 0 18px; color: #6b7280; font-size: 13.5px; }
.rr-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.rr-sb { border-radius: 14px; padding: 18px; }
.rr-sb .h { margin: 0 0 8px; font-size: 13.5px; display: flex; gap: 6px; align-items: center; padding: 0; }
.rr-sb p { margin: 0; font-size: 13.5px; line-height: 1.75; color: #374151; }
.rr-sb.s { background: #effaf3; } .rr-sb.s .h { color: #15803d; }
.rr-sb.i { background: #fdf5f9; } .rr-sb.i .h { color: #cf5e96; }
.rr-sb.r { background: #f2f6ff; } .rr-sb.r .h { color: #3b6def; }
.rr-row2 { display: grid; grid-template-columns: 370px 1fr; gap: 18px; align-items: center; }
.rr-c { display: grid; grid-template-columns: 96px 1fr 34px; gap: 12px; align-items: center; padding: 12px 0; border-bottom: 1px solid #f1f3f7; }
.rr-c:last-child { border-bottom: 0; }
.rr-c .name { font-size: 14px; font-weight: 700; color: #111827; }
.rr-c b { text-align: right; font-variant-numeric: tabular-nums; }
.rr-c .t { height: 8px; border-radius: 4px; background: #eef0f4; position: relative; }
.rr-c .t i { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 4px; }
.rr-c .cm { grid-column: 2 / 4; font-size: 12.5px; color: #4b5563; line-height: 1.6; margin-top: -2px; }
.rr-vgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.rr-vm { border: 1px solid #eef0f4; border-radius: 14px; padding: 16px 18px; }
.rr-vm .h { margin: 0 0 6px; font-size: 14px; display: flex; gap: 8px; align-items: center; color: #3b6def; padding: 0; }
.rr-vm p { margin: 0; font-size: 13.5px; line-height: 1.7; color: #374151; }
.rr-state { border-radius: 14px; padding: 26px 20px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.rr-state .ico { width: 46px; height: 46px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 22px; }
.rr-state b { font-size: 15px; color: #111827; }
.rr-state p { margin: 0; font-size: 13px; line-height: 1.7; color: #4b5563; }
.rr-state .prog { width: 220px; height: 6px; border-radius: 3px; background: #e5e9f2; overflow: hidden; margin-top: 4px; position: relative; }
.rr-state .prog i { position: absolute; top: 0; bottom: 0; width: 40%; background: #3b6def; border-radius: 3px; animation: rrslide 1.4s ease-in-out infinite; }
@keyframes rrslide { 0% { left: -40%; } 100% { left: 100%; } }
.rr-sk { background: #eef0f4; border-radius: 4px; height: 10px; margin-top: 8px; }

.rr-kpi .kt, .rr-trend .tt, .rr-sb .h, .rr-vm .h, .rr-toc .th { font-weight: 700; }
.rr-trend .tt span { font-weight: 500; }
.rr-trend .tt span .rr-legend { display: inline-block; width: 16px; margin: 0 6px 3px 12px; border-top: 2px dashed #d97706; vertical-align: middle; }

/* 마크다운 블록끼리는 margin이 적용되지 않아, 블록을 감싼 요소에 간격을 준다 */
[data-testid="stElementContainer"]:has(.rr-hero) { margin-bottom: 22px !important; }
.rr-gap { height: 32px; }   /* Streamlit 마크다운 블록의 -16px 여백을 상쇄하고 16px 간격을 남긴다 */
.rr-sec { margin-bottom: 0; }

@media (max-width: 900px) {
    .rr-hero, .rr-row2, .rr-summary, .rr-vgrid { grid-template-columns: 1fr; }
    .rr-kpis { grid-template-columns: 1fr; gap: 12px; }
    .rr-kpi + .rr-kpi { border-left: 0; border-top: 1px solid #eef0f4; padding-top: 12px; }
}
</style>""", unsafe_allow_html=True)

# ── 표지 + 점수 ────────────────────────────────────────────────────────────
_total_color = _grade_color(total_score_val)


def _kpi(score, label, title, before):
    color = _grade_color(score)
    return (
        f'<div class="rr-kpi">{_ring_svg(score)}<div><small style="color:{color}">{label}</small>'
        f'<div class="kt">{title}</div><p>{_grade_badge(score)}{_delta_html(score, before)}</p></div></div>'
    )


if len(history) >= 2:
    def _pt_label(h):
        if h is history[-1]:
            return "이번"
        return f'{h["dt"].month}/{h["dt"].day}' if h["dt"] else "-"
    _pts = [(_pt_label(h), int(h["total"] or 0), h is history[-1]) for h in history]
    _best = max(h["total"] or 0 for h in history)
    _trend_msg = ("이번이 가장 높은 종합 점수예요." if (history[-1]["total"] or 0) >= _best
                  else "지난 면접들과 비교해 보세요.")
    trend_html = (
        f'<div class="rr-card rr-trend"><div class="tt">내 면접 점수 변화 <span>최근 {len(history)}회 · 종합 점수'
        '<i class="rr-legend"></i>보통 65 이상</span></div>'
        f'<p>{_trend_msg}</p>{_trend_svg(_pts)}</div>'
    )
else:
    trend_html = (
        '<div class="rr-card rr-trend"><div class="tt">내 면접 점수 변화</div>'
        '<div class="rr-empty">면접을 두 번 이상 보면<br>여기에 점수 변화가 보여요</div></div>'
    )

st.markdown(
    '<div class="rr-hero">'
    + cover_html("INTERVIEW REPORT", f"{date_str} · {persona_str} 면접관", ["면접 결과", "리포트"],
                 score_bottom(["최종 종합 평가", "이력서·면접 합산"], total_score_val, grade_val, _total_color))
    + '<div class="rr-side"><div class="rr-card rr-kpis">'
    + _kpi(resume_score_val, "1차 서류 전형", "이력서 분석", prev["resume"] if prev else None)
    + _kpi(interview_score_val, "2차 면접 전형", "AI 면접 코칭", prev["iv"] if prev else None)
    + _kpi(total_score_val, "최종 종합 평가", "합산 결과", prev["total"] if prev else None)
    + '</div>' + trend_html + '</div></div>',
    unsafe_allow_html=True,
)

# ── 목차 + 본문 ────────────────────────────────────────────────────────────
col_toc, col_main = st.columns([210, 950])

with col_toc:
    with st.container(key="rr_toc"):
        st.markdown(
            '<div class="rr-toc"><div class="th">목차</div>'
            '<a href="#rr-summary" target="_self">종합 총평</a>'
            f'<a href="#rr-competency" target="_self">역량 상세 리포트 <span>{len(CATEGORIES)}</span></a>'
            '<a href="#rr-video" target="_self">영상 분석 코멘트</a>'
            '<div class="line"></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("피드백 보고서 보기", type="primary", key="go_feedback"):
            st.switch_page("pages/06_피드백보고서.py")
        if st.button("다시 면접하기", key="retry_interview"):
            st.session_state["_session_id_clear_pending"] = True
            state_set("session_id",     None)
            state_set("first_question", None)
            state_set("result",         None)
            state_set("interview_done", False)
            if "iv_messages" in st.session_state:
                del st.session_state["iv_messages"]
            st.switch_page("pages/03_면접_환경설정.py")

with col_main:
    # 01 종합 총평
    _sum_boxes = "".join(
        f'<div class="rr-sb {cls}"><div class="h"><i class="ph-bold {icon}"></i>{label}</div><p>{_esc(text)}</p></div>'
        for label, cls, icon, text in SUMMARY if text
    )
    st.markdown(
        '<div class="rr-sec" id="rr-summary"><div class="sh"><span class="n">01</span>종합 총평</div>'
        f'<p class="d">{html.escape(persona_str)} 면접관의 시선으로 정리했어요</p>'
        + (f'<div class="rr-summary">{_sum_boxes}</div>' if _sum_boxes
           else '<div class="rr-empty" style="height:90px">종합 총평을 불러오지 못했습니다.</div>')
        + '</div><div class="rr-gap"></div>',
        unsafe_allow_html=True,
    )

    # 02 역량 상세 리포트
    _rows = ""
    for cat, score, comment in zip(CATEGORIES, MY_SCORES, COMMENTS):
        color = _grade_color(score)
        _rows += (
            f'<div class="rr-c"><span class="name">{cat}</span>'
            f'<span class="t"><i style="width:{max(0, min(100, score))}%;background:{color}"></i></span>'
            f'<b style="color:{color}">{score}</b>'
            + (f'<span class="cm">{_esc(comment)}</span>' if comment else '')
            + '</div>'
        )
    st.markdown(
        '<div class="rr-sec" id="rr-competency"><div class="sh"><span class="n">02</span>역량 상세 리포트</div>'
        '<p class="d">AI 면접관이 분석한 5가지 역량 · 점수 및 개선 코멘트</p>'
        f'<div class="rr-row2">{_radar_svg(MY_SCORES)}<div>{_rows}</div></div></div><div class="rr-gap"></div>',
        unsafe_allow_html=True,
    )

    # 03 영상 분석 코멘트 — 상태에 따라 아래 중 하나만 보인다
    _VIDEO_HEAD = ('<div class="rr-sec" id="rr-video"><div class="sh"><span class="n">03</span>영상 분석 코멘트</div>'
                   '<p class="d">웹캠으로 면접을 본 경우, 분석이 끝나면 보여요</p>')

    def _video_state(icon, bg, icon_bg, icon_color, title, body, extra=""):
        st.markdown(
            _VIDEO_HEAD
            + f'<div class="rr-state" style="background:{bg}"><span class="ico" style="background:{icon_bg};color:{icon_color}">'
            f'<i class="ph-bold {icon}"></i></span><b>{title}</b><p>{body}</p>{extra}</div></div>',
            unsafe_allow_html=True,
        )

    _video_rendered = False
    if session_id:
        try:
            video_metrics = api.get_video_metrics(session_id)
        except api.SessionExpiredError:
            video_metrics = None
            mark_session_expired()
        except requests.exceptions.HTTPError as e:
            video_metrics = None
            if e.response is not None and e.response.status_code == 404:
                if st.session_state.get("_video_upload_pending_sid") == session_id:
                    video_metrics = {"status": "uploading"}
            else:
                st.warning("영상 분석 결과를 불러오지 못했습니다.")
        except Exception:
            video_metrics = None
            st.warning("영상 분석 결과를 불러오지 못했습니다. 잠시 후 새로고침해 주세요.")

        if video_metrics and video_metrics.get("status") != "uploading":
            if st.session_state.get("_video_upload_pending_sid") == session_id:
                st.session_state.pop("_video_upload_pending_sid", None)

        if video_metrics and video_metrics.get("status") == "uploading":
            _upload_wait_key = f"_video_upload_waits_{session_id}"
            _upload_waits = st.session_state.get(_upload_wait_key, 0)
            if _upload_waits < _VIDEO_RESULT_WAIT_TRIES:
                st.session_state[_upload_wait_key] = _upload_waits + 1
                _video_rendered = True
                _video_state("ph-cloud-arrow-up", "#f5f8ff", "#e3ebff", "#3b6def", "영상을 저장하고 있어요",
                             "면접 영상을 서버에 올리는 중이에요.<br>저장이 끝나면 영상 분석이 자동으로 시작됩니다.",
                             '<span class="prog"><i></i></span>')
                time.sleep(3.0)
                st.rerun()
            else:
                st.session_state.pop("_video_upload_pending_sid", None)
                _video_rendered = True
                _video_state("ph-cloud-arrow-up", "#f5f8ff", "#e3ebff", "#3b6def", "영상 저장이 아직 끝나지 않았어요",
                             "잠시 후 새로고침해 주세요.")

        elif video_metrics and video_metrics.get("status") == "analyzing":
            _video_rendered = True
            st.markdown(
                _VIDEO_HEAD
                + '<div class="rr-vgrid" style="opacity:.55">'
                '<div class="rr-vm"><div class="h"><i class="ph-bold ph-eye"></i>시선 처리</div><div class="rr-sk"></div><div class="rr-sk" style="width:70%"></div></div>'
                '<div class="rr-vm"><div class="h"><i class="ph-bold ph-waveform"></i>발화 속도</div><div class="rr-sk"></div><div class="rr-sk" style="width:60%"></div></div>'
                '</div><p style="margin:12px 0 0;font-size:12.5px;font-weight:700;color:#3b6def;">'
                'AI가 시선 처리와 발화 속도를 분석하고 있어요 · 분석이 끝나면 자동으로 표시돼요</p></div>',
                unsafe_allow_html=True,
            )
            time.sleep(3.0)
            st.rerun()

        elif video_metrics and video_metrics.get("status") == "failed":
            _video_fail_retry_key = f"_video_fail_retries_{session_id}"
            _video_fail_retries = st.session_state.get(_video_fail_retry_key, 0)
            if _video_fail_retries < 2:
                st.session_state[_video_fail_retry_key] = _video_fail_retries + 1
                time.sleep(3.0)
                st.rerun()

            _video_rendered = True
            _video_error_msg = (video_metrics or {}).get("error") or "일시적인 문제로 영상 분석을 완료하지 못했습니다."
            _video_state("ph-warning-circle", "#fdf7fa", "#fbe4ee", "#cf5e96", "영상 분석을 완료하지 못했어요",
                         f'{_esc(_video_error_msg)}<br><b style="font-size:13px">답변 내용과 점수에는 영향이 없어요.</b>')

        elif video_metrics and video_metrics.get("status") == "done":
            WEBCAM_RESULTS = []
            gaze = video_metrics.get("gaze")
            if gaze:
                WEBCAM_RESULTS.append(("ph-eye", "시선 처리", gaze.get("message", "")))
            speech = video_metrics.get("speech")
            if speech:
                WEBCAM_RESULTS.append(("ph-waveform", "발화 속도", speech.get("message", "")))
            if WEBCAM_RESULTS:
                _video_rendered = True
                _cards = "".join(
                    f'<div class="rr-vm"><div class="h"><i class="ph-bold {icon}"></i>{metric}</div><p>{_esc(comment)}</p></div>'
                    for icon, metric, comment in WEBCAM_RESULTS
                )
                st.markdown(_VIDEO_HEAD + f'<div class="rr-vgrid">{_cards}</div></div>', unsafe_allow_html=True)

    if not _video_rendered:
        _video_state("ph-video-camera-slash", "#f8fafc", "#eef0f4", "#6b7280", "영상 분석 결과가 없어요",
                     "웹캠을 켜고 면접하면 시선 처리와 발화 속도를 알려드려요.")

render_session_expired_banner()
