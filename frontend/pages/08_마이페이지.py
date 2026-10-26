import html
import json
from datetime import datetime, timezone

import streamlit as st
from utils.brand import FAVICON
import streamlit.components.v1 as components
from components.sidebar import render_sidebar
from utils.state import init_session, mark_session_expired, render_session_expired_banner
from utils import api

st.set_page_config(
    page_title="마이페이지 | intro",
    page_icon=FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
render_sidebar(active="마이페이지")

try:
    _sessions_data = api.get_my_sessions(limit=20)
except api.SessionExpiredError:
    _sessions_data = None
    mark_session_expired()
except Exception:
    _sessions_data = None

_sessions = _sessions_data.get("sessions", []) if _sessions_data else []
_summary  = _sessions_data.get("summary", {}) if _sessions_data else {}

try:
    _resumes_data = api.get_my_resumes()
except api.SessionExpiredError:
    _resumes_data = []
    mark_session_expired()
except Exception:
    _resumes_data = []

# ── 데이터 (실제 GET /interview/sessions) ──────────────────────────────────
HISTORY = []
for _s in _sessions:
    try:
        _dt = datetime.fromisoformat(_s["created_at"].replace("Z", "+00:00"))
        if _dt.tzinfo is None:
            _dt = _dt.replace(tzinfo=timezone.utc)
    except (ValueError, KeyError, TypeError):
        _dt = None
    HISTORY.append({
        "dt":         _dt,
        "date":       _dt.strftime("%m.%d") if _dt else "-",
        "date_full":  _dt.strftime("%Y.%m.%d") if _dt else "-",
        "date_axis":  f"{_dt.month}/{_dt.day}" if _dt else "-",
        "style":      _s.get("persona") or "-",
        "resume":     _s.get("resume_score"),
        "iv":         _s.get("interview_score"),
        "total":      _s.get("total_score"),
        "has_video":  bool(_s.get("has_video")),
        "video_url":  _s.get("video_url") or "",
        "session_id": _s.get("session_id") or "",
    })

_RESUME_TOTAL = len(_resumes_data)
VERSIONS = []
for _i, _r in enumerate(_resumes_data[:5]):
    try:
        _rdt = datetime.fromisoformat(_r["created_at"].replace("Z", "+00:00"))
        _rdate = _rdt.strftime("%Y.%m.%d")
    except (ValueError, KeyError, TypeError):
        _rdate = "-"
    VERSIONS.append({
        "v": f"v{_RESUME_TOTAL - _i}",
        "date": _rdate,
        "active": _i == 0,
    })

def score_color(s) -> str:
    if s is None: return "#9ca3af"
    if s >= 80: return "#16a34a"   # 우수 — 초록
    if s >= 65: return "#d97706"   # 보통 — 주황
    return "#cf5e96"               # 개선 필요 — 로즈 핑크 (주황과 색상 거리 확보)


def _esc(v) -> str:
    return html.escape(str(v))


def _report_links(session_id: str, items) -> str:
    out = ""
    for path, label, icon in items:
        ic = f'<i class="ph-bold {icon}"></i>' if icon else ""
        out += f'<a class="mp-lk" href="/{path}?sid={_esc(session_id)}" target="_self">{ic}{label}</a>'
    return out


def _play_btn(video_url: str, meta: str = "", label: str = "영상", primary: bool = False) -> str:
    """누르면 아래 영상 창 스크립트가 data-video-url 을 읽어 영상을 연다."""
    full_url = f"{api.PUBLIC_BASE_URL}{video_url}" if video_url else ""
    cls = "mp-play primary" if primary else "mp-play"
    return (
        f'<span class="{cls}" data-video-url="{_esc(full_url)}" data-video-meta="{_esc(meta)}">'
        f'<i class="ph-fill ph-play"></i>{label}</span>'
    )


_PERSONA_DOT = {"기술": "#3b6def", "인사": "#8fa6f5", "임원": "#1f3a8a"}


def _persona_html(name: str) -> str:
    dot = next((c for k, c in _PERSONA_DOT.items() if str(name).startswith(k)), "#9ca3af")
    return f'<span class="mp-persona"><i style="background:{dot}"></i>{_esc(name)}</span>'


def _trend_svg(points) -> str:
    """points: [(x축 라벨, 점수)] — 오래된 순. 결과 리포트와 같은 보통 65 · 우수 80 기준선."""
    W, H, L, R, top, bottom = 700, 250, 40, 690, 30, 215
    lo = 40 if min(v for _, v in points) >= 40 else 0
    def y(v): return bottom - (max(lo, min(100, v)) - lo) / (100 - lo) * (bottom - top)
    n = len(points)
    xs = [L + 70 + (R - L - 110) * (i / (n - 1) if n > 1 else 0.5) for i in range(n)]
    grid = "".join(
        f'<line x1="{L}" y1="{y(v):.1f}" x2="{R}" y2="{y(v):.1f}" stroke="#eef0f4"/>'
        f'<text x="{4 if v == 100 else 10}" y="{y(v) + 4:.1f}" font-size="11" fill="#9ca3af">{v}</text>'
        for v in range(lo, 101, 20)
    )
    guides = (
        f'<line x1="{L}" y1="{y(80):.1f}" x2="{R}" y2="{y(80):.1f}" stroke="#16a34a" stroke-dasharray="4 4" opacity=".6"/>'
        f'<line x1="{L}" y1="{y(65):.1f}" x2="{R}" y2="{y(65):.1f}" stroke="#d97706" stroke-dasharray="4 4" opacity=".7"/>'
    )
    path = " ".join(f'{"M" if i == 0 else "L"} {xs[i]:.1f} {y(v):.1f}' for i, (_, v) in enumerate(points))
    dots = labels = axis = ""
    for i, (lab, v) in enumerate(points):
        c = score_color(v)
        last = i == n - 1
        dots += (f'<circle cx="{xs[i]:.1f}" cy="{y(v):.1f}" r="8" fill="{c}"/>' if last else
                 f'<circle cx="{xs[i]:.1f}" cy="{y(v):.1f}" r="6" fill="#fff" stroke="{c}" stroke-width="3"/>')
        labels += (f'<text x="{xs[i]:.1f}" y="{y(v) - (17 if last else 14):.1f}" text-anchor="middle" '
                   f'font-size="13" font-weight="800" fill="{c}">{v}</text>')
        weight = ' font-weight="700"' if last else ""
        axis += (f'<text x="{xs[i]:.1f}" y="240" text-anchor="middle" font-size="12" '
                 f'fill="{"#111827" if last else "#6b7280"}"{weight}>{_esc(lab)}</text>')
    return (f'<svg width="100%" viewBox="0 0 {W} {H}" style="display:block;height:auto;font-family:inherit">'
            f'{grid}{guides}<path d="{path}" fill="none" stroke="#3b6def" stroke-width="3"/>{dots}{labels}{axis}</svg>')


# ── CSS ──────────────────────────────────────────────────────────────────
# 카드·번호 제목·점수 색은 결과 리포트 3종과 같은 규칙을 쓴다. 제목은 h 태그 대신 div.
st.markdown("""<style>
[data-testid="stMainBlockContainer"] { padding: 36px 40px 80px 40px !important; max-width: 1240px !important;
    word-break: keep-all !important; overflow-wrap: break-word !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stHorizontalBlock"] { gap: 0 !important; }
[data-testid="stColumn"] { padding: 0 !important; }

.mp-head { margin-bottom: 22px; }
.mp-head .t { font-size: 26px; font-weight: 800; letter-spacing: -.02em; color: #111827; margin: 0 0 6px; }
.mp-head .sub { font-size: 14px; color: #6b7280; }

.mp-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 38px; }
.mp-stat { background: #fff; border: 1px solid #e9ecf2; border-radius: 18px; padding: 20px 22px;
    display: flex; gap: 14px; align-items: center; min-width: 0; }
.mp-stat .ic { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center;
    justify-content: center; font-size: 21px; flex-shrink: 0; }
.mp-stat small { display: block; font-size: 12.5px; color: #6b7280; font-weight: 600; }
.mp-stat b { display: block; font-size: 26px; font-weight: 800; margin-top: 2px; letter-spacing: -.02em; white-space: nowrap; }

.mp-card { background: #fff; border: 1px solid #e9ecf2; border-radius: 18px; padding: 26px 28px; }
.mp-sh { display: flex; gap: 10px; align-items: center; font-size: 19px; font-weight: 700; color: #111827; margin: 0 0 4px; }
.mp-sh .n { font-size: 12px; color: #3b6def; background: #eef3ff; border-radius: 7px; padding: 3px 8px; font-weight: 800; }
.mp-sd { margin: 0 0 18px; color: #6b7280; font-size: 13.5px; }
.mp-empty { display: flex; align-items: center; justify-content: center; text-align: center; min-height: 140px;
    font-size: 13.5px; color: #9ca3af; line-height: 1.7; background: #fafbfd; border-radius: 12px; }

.mp-row { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 16px; align-items: start; }
.mp-legend { display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: #6b7280; margin: -6px 0 6px; }
.mp-legend span { display: flex; gap: 6px; align-items: center; }
.mp-ver { display: flex; flex-direction: column; gap: 8px; }
.mp-vr { display: flex; align-items: center; gap: 12px; padding: 13px 16px; border-radius: 12px;
    border: 1px solid #eef0f4; background: #fafbfd; }
.mp-vr b { font-size: 14px; width: 34px; color: #111827; }
.mp-vr span { font-size: 13px; color: #6b7280; flex: 1; }
.mp-vr .tag { flex: none; font-style: normal; font-size: 11px; font-weight: 800; color: #3b6def; background: #eef3ff;
    border-radius: 999px; padding: 3px 9px; }
.mp-vr.on { border: 1.5px solid #3b6def; background: #f5f8ff; }
.mp-vr.on b { color: #2f5bd8; }

.mp-tbl-wrap { overflow-x: auto; }
.mp-tbl { min-width: 760px; }
.mp-tr { display: grid; grid-template-columns: 80px minmax(110px, 1.2fr) 70px 70px 70px 84px minmax(220px, 1.6fr);
    align-items: center; padding: 14px 10px; border-bottom: 1px solid #f1f3f7; font-size: 14px; color: #111827; }
.mp-tr:last-child { border-bottom: 0; }
.mp-tr.h { font-size: 12px; color: #6b7280; font-weight: 700; background: #f7f8fb; border-radius: 10px;
    border-bottom: 0; padding: 10px; }
.mp-tr .c { text-align: center; }
.mp-tr .sc { font-weight: 800; font-variant-numeric: tabular-nums; }
.mp-tr .r { display: flex; gap: 6px; justify-content: flex-end; }
.mp-persona { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; }
.mp-persona i { width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.mp-muted { color: #c4c9d4; }
a.mp-lk { font-size: 12.5px; font-weight: 700; color: #2f5bd8 !important; background: #eef3ff; border-radius: 8px;
    padding: 6px 11px; display: inline-flex; gap: 5px; align-items: center; text-decoration: none !important;
    white-space: nowrap; }
a.mp-lk:hover { background: #e0e9ff; }
.mp-play { font-size: 12.5px; font-weight: 700; color: #4b5563; border: 1px solid #e5e7eb; background: #fff;
    border-radius: 8px; padding: 5px 10px; display: inline-flex; gap: 5px; align-items: center; cursor: pointer;
    white-space: nowrap; }
.mp-play:hover { background: #f7f8fb; }
.mp-play.primary { font-size: 13.5px; color: #fff; background: #3b6def; border-color: #3b6def;
    border-radius: 10px; padding: 10px 16px; gap: 7px; }
.mp-play.primary:hover { background: #2f5bd8; }

.mp-note { display: flex; gap: 8px; align-items: center; font-size: 13px; color: #6b7280; margin: -4px 0 18px; }
.mp-vlist { display: flex; flex-direction: column; gap: 10px; }
.mp-vrow { display: grid; grid-template-columns: 52px minmax(0, 1fr) auto auto auto; align-items: center; gap: 18px;
    border: 1px solid #eef0f4; border-radius: 14px; padding: 14px 18px; background: #fff; }
.mp-vrow .ic { width: 52px; height: 52px; border-radius: 12px; background: #eef3ff; color: #3b6def;
    display: flex; align-items: center; justify-content: center; font-size: 24px; }
.mp-vrow b { font-size: 15px; display: block; color: #111827; }
.mp-vrow small { font-size: 13px; color: #6b7280; }
.mp-vrow .sc { text-align: right; }
.mp-vrow .sc small { display: block; font-size: 11.5px; color: #9ca3af; }
.mp-vrow .sc b { font-size: 20px; font-weight: 800; }
.mp-vrow .lks { display: flex; gap: 6px; }
.mp-vrow a.mp-lk { color: #4b5563 !important; background: #fff; border: 1px solid #e5e7eb; padding: 7px 11px; }
.mp-vrow a.mp-lk:hover { background: #f7f8fb; }

@media (max-width: 1000px) {
    .mp-stats { grid-template-columns: repeat(2, 1fr); }
    .mp-row { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
    [data-testid="stMainBlockContainer"] { padding: 24px 16px 60px !important; }
    .mp-stats { grid-template-columns: 1fr; }
    .mp-card { padding: 20px 18px; }
    .mp-vrow { grid-template-columns: 44px minmax(0, 1fr) auto; gap: 12px; }
    .mp-vrow .ic { width: 44px; height: 44px; font-size: 20px; }
    .mp-vrow .lks, .mp-vrow .mp-play { grid-column: 1 / -1; }
    .mp-vrow .mp-play { justify-content: center; }
}
</style>""", unsafe_allow_html=True)


# ── 헤더 ─────────────────────────────────────────────────────────────────
_HEAD_HTML = (
    '<div class="mp-head"><div class="t">마이페이지</div>'
    '<div class="sub">면접 히스토리, 점수 추이, 이력서 버전을 관리하세요</div></div>'
)


# ── 통계 카드 4개 ─────────────────────────────────────────────────────────
_now = datetime.now(timezone.utc)
_recent_scored = [
    h for h in HISTORY
    if h["iv"] is not None and h["dt"] is not None and (_now - h["dt"]).days <= 30
]
if len(_recent_scored) >= 2:
    _delta = _recent_scored[0]["iv"] - _recent_scored[-1]["iv"]
    _delta_str = f"{_delta:+d}점"
else:
    _delta = None
    _delta_str = "-"

_avg_iv = _summary.get("average_interview_score")
_latest_resume = _summary.get("latest_resume_score")

_NEUTRAL = "#4b5563"
_delta_color = (
    "#16a34a" if _delta is not None and _delta > 0
    else "#cf5e96" if _delta is not None and _delta < 0
    else _NEUTRAL
)


def _tint(color: str) -> str:
    return {"#16a34a": "#f0fdf4", "#d97706": "#fffbeb", "#cf5e96": "#fdf3f8"}.get(color, "#f3f4f6")


STAT_CARDS = [
    ("총 면접 횟수", f"{_summary.get('total_interviews', 0)}회", _NEUTRAL, "ph-users-three"),
    ("평균 면접 점수", f"{_avg_iv}점" if _avg_iv is not None else "-", score_color(_avg_iv), "ph-microphone"),
    ("현재 이력서 점수", f"{_latest_resume}점" if _latest_resume is not None else "-", score_color(_latest_resume), "ph-file-text"),
    ("최근 30일 점수 향상", _delta_str, _delta_color, "ph-trend-up"),
]
st.markdown(
    _HEAD_HTML + '<div class="mp-stats">' + "".join(
        f'<div class="mp-stat"><span class="ic" style="background:{_tint(c)};color:{c}">'
        f'<i class="ph-bold {icon}"></i></span><div><small>{lbl}</small>'
        f'<b style="color:{"#111827" if c == _NEUTRAL else c}">{_esc(v)}</b></div></div>'
        for lbl, v, c, icon in STAT_CARDS
    ) + '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    "<style>.st-key-_mypage_tab_restore { position:absolute; width:0; height:0; "
    "overflow:hidden; clip:rect(0,0,0,0); margin:0; padding:0; }</style>",
    unsafe_allow_html=True,
)
_mypage_tab_restored = st.text_input(
    "_mypage_tab_restore", key="_mypage_tab_restore", label_visibility="collapsed"
)
if st.session_state.get("mypage_tab"):
    _mypage_tab = st.session_state["mypage_tab"]
    components.html(
        f"<script>localStorage.setItem('iv_mypage_tab', {json.dumps(_mypage_tab)});</script>",
        height=0,
    )
elif _mypage_tab_restored:
    st.session_state["mypage_tab"] = _mypage_tab_restored
    st.rerun()
else:
    _mypage_tab = "overview"
    components.html("""
    <script>
    (function() {
      var doc = window.parent.document;
      var tries = 0;
      function attempt() {
        var input = doc.querySelector('.st-key-_mypage_tab_restore input');
        if (!input) {
          tries++;
          if (tries < 20) setTimeout(attempt, 50);
          return;
        }
        var saved = localStorage.getItem('iv_mypage_tab');
        if (!saved) return;
        var setter = Object.getOwnPropertyDescriptor(
          window.parent.HTMLInputElement.prototype, 'value'
        ).set;
        setter.call(input, saved);
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
        input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }));
      }
      attempt();
    })();
    </script>
    """, height=0)

_MYPAGE_TABS = [("overview", "점수 · 이력서"), ("history", "면접 히스토리"), ("video", "영상 확인")]
st.markdown(
    '<style>'
    '.st-key-mypage_tabs_row { width: fit-content !important; max-width: 100% !important; background: #eef0f4 !important; '
    'border-radius: 12px !important; padding: 4px !important; margin-bottom: 18px !important; }'
    '.st-key-mypage_tabs_row [data-testid="stHorizontalBlock"] { gap: 4px !important; flex-wrap: nowrap !important; }'
    '.st-key-mypage_tabs_row [data-testid="stColumn"] { width: auto !important; flex: 0 0 auto !important; min-width: 0 !important; }'
    '.st-key-mypage_tabs_row button { background: transparent !important; border: none !important; border-radius: 9px !important; '
    'padding: 8px 18px !important; min-height: 0 !important; box-shadow: none !important; }'
    '.st-key-mypage_tabs_row button p { font-size: 14px !important; white-space: nowrap !important; }'
    + ''.join(
        f'.st-key-mypage_tab_btn_{key} button {{ background: {"#fff" if key == _mypage_tab else "transparent"} !important; '
        f'{"box-shadow: 0 1px 2px rgba(17,24,39,.06) !important;" if key == _mypage_tab else ""} }}'
        f'.st-key-mypage_tab_btn_{key} button p {{ color: {"#111827" if key == _mypage_tab else "#6b7280"} !important; '
        f'font-weight: {"700" if key == _mypage_tab else "600"} !important; }}'
        for key, _ in _MYPAGE_TABS
    )
    + '</style>',
    unsafe_allow_html=True,
)
with st.container(key="mypage_tabs_row"):
    _tab_cols = st.columns(len(_MYPAGE_TABS))
    for _col, (_key, _label) in zip(_tab_cols, _MYPAGE_TABS):
        with _col:
            if st.button(_label, key=f"mypage_tab_btn_{_key}"):
                st.session_state["mypage_tab"] = _key
                st.rerun()

_REPORT_LINKS = [
    ("결과리포트", "결과", "ph-chart-bar"),
    ("피드백보고서", "피드백", "ph-chat-text"),
    ("이력서최적화", "최적화", "ph-file-text"),
]

if _mypage_tab == "overview":
    # ── 01 면접 점수 변화 + 02 이력서 버전 ─────────────────────────────────────
    _SCORED_HISTORY = [h for h in HISTORY if h["iv"] is not None]

    if not _SCORED_HISTORY:
        chart_body = '<div class="mp-empty">완료된 면접이 아직 없어서 점수 추이를 보여드릴 수 없어요.</div>'
    else:
        _chart_points = [(h["date_axis"], h["iv"]) for h in reversed(_SCORED_HISTORY[:5])]
        chart_body = (
            '<div class="mp-legend">'
            '<span><i style="width:14px;height:3px;background:#3b6def;display:inline-block"></i>면접 점수</span>'
            '<span><i style="width:14px;border-top:2px dashed #d97706;display:inline-block"></i>보통 65</span>'
            '<span><i style="width:14px;border-top:2px dashed #16a34a;display:inline-block"></i>우수 80</span>'
            '</div>' + _trend_svg(_chart_points)
        )

    if not VERSIONS:
        ver_body = '<div class="mp-empty">업로드된 이력서가 없어요</div>'
    else:
        ver_body = '<div class="mp-ver">'
        for v in VERSIONS:
            tag = '<span class="tag">현재</span>' if v["active"] else ""
            ver_body += (f'<div class="mp-vr{" on" if v["active"] else ""}"><b>{_esc(v["v"])}</b>'
                         f'<span>{_esc(v["date"])}</span>{tag}</div>')
        ver_body += '</div>'

    st.markdown(
        '<div class="mp-row">'
        '<div class="mp-card"><div class="mp-sh"><span class="n">01</span>면접 점수 변화</div>'
        '<div class="mp-sd">최근 5회까지 · 결과 리포트의 점수 변화 그래프와 같은 기준이에요</div>'
        + chart_body + '</div>'
        '<div class="mp-card"><div class="mp-sh"><span class="n">02</span>이력서 버전</div>'
        '<div class="mp-sd">가장 최근 이력서로 면접을 봐요</div>'
        + ver_body + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


elif _mypage_tab == "history":
    # ── 01 면접 기록 ───────────────────────────────────────────────────────────
    if not HISTORY:
        table_body = '<div class="mp-empty">아직 면접 기록이 없어요.</div>'
    else:
        rows_html = ""
        for h in HISTORY:
            def _sc(v):
                return (f'<span class="c sc" style="color:{score_color(v)}">{v}</span>' if v is not None
                        else '<span class="c mp-muted">-</span>')
            video_cell = (
                _play_btn(h["video_url"], f'{h["date_full"]} · {h["style"]} 면접관') if h["has_video"]
                else '<span class="mp-muted">–</span>'
            )
            links_cell = (
                _report_links(h["session_id"], _REPORT_LINKS)
                if h["iv"] is not None and h["session_id"] else '<span class="mp-muted">-</span>'
            )
            rows_html += (
                f'<div class="mp-tr"><span>{_esc(h["date"])}</span>{_persona_html(h["style"])}'
                f'{_sc(h["resume"])}{_sc(h["iv"])}{_sc(h["total"])}'
                f'<span class="c">{video_cell}</span><span class="r">{links_cell}</span></div>'
            )
        table_body = (
            '<div class="mp-tbl-wrap"><div class="mp-tbl">'
            '<div class="mp-tr h"><span>날짜</span><span>면접관</span><span class="c">이력서</span>'
            '<span class="c">면접</span><span class="c">종합</span><span class="c">영상</span>'
            '<span style="text-align:right">리포트</span></div>'
            + rows_html + '</div></div>'
        )

    st.markdown(
        '<div class="mp-card"><div class="mp-sh"><span class="n">01</span>면접 기록</div>'
        '<div class="mp-sd">오른쪽 버튼으로 결과 리포트 · 피드백 보고서 · 이력서 최적화를 바로 열 수 있어요</div>'
        + table_body + '</div>',
        unsafe_allow_html=True,
    )


elif _mypage_tab == "video":
    # ── 01 저장된 면접 영상 ────────────────────────────────────────────────────
    _video_items = [h for h in HISTORY if h["has_video"]]
    if not _video_items:
        video_body = ('<div class="mp-empty">저장된 면접 영상이 없어요.<br>'
                      '웹캠을 켜고 면접을 진행하면 여기에서 다시 볼 수 있어요.</div>')
    else:
        video_body = '<div class="mp-vlist">'
        for h in _video_items:
            total_html = (
                f'<div class="sc"><small>종합</small><b style="color:{score_color(h["total"])}">{h["total"]}</b></div>'
                if h["total"] is not None else '<div class="sc"><small>종합</small><b class="mp-muted">-</b></div>'
            )
            links_html = (
                _report_links(h["session_id"], [("결과리포트", "결과 리포트", ""), ("피드백보고서", "피드백", "")])
                if h["iv"] is not None and h["session_id"] else ""
            )
            video_body += (
                '<div class="mp-vrow"><span class="ic"><i class="ph-fill ph-video-camera"></i></span>'
                f'<div><b>{_esc(h["date_full"])}</b><small>{_esc(h["style"])} 면접관</small></div>'
                f'{total_html}<div class="lks">{links_html}</div>'
                + _play_btn(h["video_url"], f'{h["date_full"]} · {h["style"]} 면접관', "영상 보기", primary=True)
                + '</div>'
            )
        video_body += '</div>'

    st.markdown(
        '<div class="mp-card"><div class="mp-sh"><span class="n">01</span>저장된 면접 영상</div>'
        '<div class="mp-sd">웹캠을 켜고 본 면접만 저장돼요</div>'
        '<div class="mp-note"><i class="ph-bold ph-info"></i>'
        '영상은 최근 3개까지 보관돼요. 새로 녹화하면 가장 오래된 영상부터 지워져요.</div>'
        + video_body + '</div>',
        unsafe_allow_html=True,
    )

_access_token = st.session_state.get("access_token", "")

components.html(f"""
<script>
(function () {{
    var doc = window.parent.document;
    var ACCESS_TOKEN = {json.dumps(_access_token)};
    if (doc._videoModalHandler) doc.removeEventListener('click', doc._videoModalHandler);
    doc._videoModalReady = true;
    doc._videoModalToken = ACCESS_TOKEN;

    function closeModal() {{
        var m = doc.getElementById('_video_modal');
        if (m) {{
            var v = m.querySelector('video');
            if (v && v.src && v.src.indexOf('blob:') === 0) URL.revokeObjectURL(v.src);
            m.remove();
        }}
    }}

    function openModal(url, meta) {{
        closeModal();

        var modal = doc.createElement('div');
        modal.id = '_video_modal';
        modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);z-index:99999;display:flex;align-items:center;justify-content:center;';

        var box = doc.createElement('div');
        box.style.cssText = 'background:white;border-radius:18px;padding:22px 24px 24px;max-width:760px;width:90%;position:relative;box-sizing:border-box;font-family:Pretendard,-apple-system,sans-serif;';

        var closeBtn = doc.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = 'position:absolute;top:14px;right:16px;background:none;border:none;font-size:22px;cursor:pointer;color:#9ca3af;line-height:1;';
        closeBtn.addEventListener('click', closeModal);

        var title = doc.createElement('div');
        title.textContent = '면접 영상';
        title.style.cssText = 'font-size:16px;font-weight:800;color:#111827;margin:0;';

        var sub = doc.createElement('div');
        sub.textContent = meta || '';
        sub.style.cssText = 'font-size:13px;color:#6b7280;margin:2px 0 0;';

        var head = doc.createElement('div');
        head.style.cssText = 'margin:0 32px 14px 0;';
        head.appendChild(title);
        if (meta) head.appendChild(sub);

        box.appendChild(closeBtn);
        box.appendChild(head);

        if (url) {{
            var status = doc.createElement('p');
            status.textContent = '영상을 불러오는 중...';
            status.style.cssText = 'font-size:13px;color:#6b7280;text-align:center;padding:40px 0;margin:0;';
            box.appendChild(status);

            fetch(url, {{ headers: {{ 'Authorization': 'Bearer ' + doc._videoModalToken }} }})
                .then(function (res) {{
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    return res.blob();
                }})
                .then(function (blob) {{
                    var video = doc.createElement('video');
                    video.controls = true;
                    video.autoplay = true;
                    video.src = URL.createObjectURL(blob);
                    video.style.cssText = 'width:100%;max-height:70vh;border-radius:12px;background:#000;display:block;';
                    video.addEventListener('loadedmetadata', function () {{
                        if (video.duration === Infinity || isNaN(video.duration)) {{
                            video.currentTime = 1e101;
                            video.addEventListener('timeupdate', function fixDuration() {{
                                video.removeEventListener('timeupdate', fixDuration);
                                video.currentTime = 0;
                            }}, {{ once: true }});
                        }}
                    }});

                    if (status.parentNode) status.replaceWith(video);
                }})
                .catch(function (err) {{
                    status.textContent = '영상을 불러오지 못했습니다: ' + err.message;
                }});
        }} else {{
            var ph = doc.createElement('div');
            ph.style.cssText = 'display:flex;flex-direction:column;align-items:center;justify-content:center;height:200px;color:#9ca3af;gap:12px;';
            ph.innerHTML = '<i class="ph-bold ph-video-camera-slash" style="font-size:40px;color:#e5e7eb;"></i><span style="font-size:14px;">저장된 영상이 없습니다</span>';
            box.appendChild(ph);
        }}

        modal.appendChild(box);
        modal.addEventListener('click', function (e) {{ if (e.target === modal) closeModal(); }});
        doc.body.appendChild(modal);
    }}

    doc._videoModalHandler = function (e) {{
        var btn = e.target.closest('[data-video-url]');
        if (btn) openModal(btn.getAttribute('data-video-url'), btn.getAttribute('data-video-meta'));
    }};
    doc.addEventListener('click', doc._videoModalHandler);
}}());
</script>
""", height=0)

st.markdown('<div style="height:48px"></div>', unsafe_allow_html=True)
render_session_expired_banner()
