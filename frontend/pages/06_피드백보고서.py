import html
import streamlit as st
from utils.brand import FAVICON
from datetime import datetime
from components.sidebar import render_sidebar
from components.report_cover import COVER_CSS, cover_html, score_bottom, stats_bottom
from utils.state import init_session, get, set as state_set, mark_session_expired, render_session_expired_banner, ensure_latest_session_id
from utils.ui import show_error_once
from utils import api

st.set_page_config(
    page_title="피드백 보고서 | intro",
    page_icon=FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
render_sidebar(active="피드백 보고서")


_sid_param = st.query_params.get("sid")
if _sid_param and _sid_param != get("session_id"):
    state_set("session_id", _sid_param)

ensure_latest_session_id()

# ── 피드백 데이터 조회 ────────────────────────────────────────────────────────
session_id    = get("session_id")
feedback_data = None

if session_id:
    try:
        feedback_data = api.get_feedback(session_id)
    except api.SessionExpiredError:
        mark_session_expired()
    except Exception:
        feedback_data = None

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

.fb-hero { display: grid; grid-template-columns: 360px 1fr; gap: 20px; margin-bottom: 24px; }
.fb-card { background: #fff; border: 1px solid #e9ecf2; border-radius: 18px; padding: 22px 24px; }
.fb-card .tt { margin: 0 0 4px; font-size: 16px; color: #111827; padding: 0; }
.fb-card .d { margin: 0 0 18px; font-size: 13px; color: #6b7280; }
.fb-bars { display: grid; grid-template-columns: 1fr; row-gap: 12px; }
.fb-bars.two { grid-template-columns: 1fr 1fr; grid-auto-flow: column; column-gap: 28px; }
.fb-bar { display: grid; grid-template-columns: 34px 1fr 54px; gap: 10px; align-items: center; font-size: 13px; }
.fb-bar em { font-style: normal; font-weight: 700; color: #6b7280; }
.fb-bar .t { height: 9px; border-radius: 5px; background: #eef0f4; overflow: hidden; }
.fb-bar .t i { display: block; height: 100%; border-radius: 5px; }
.fb-bar b { text-align: right; font-variant-numeric: tabular-nums; }

/* 왼쪽 질문 목록 (버튼) */
.st-key-fb_toc { background: #fff; border: 1px solid #e9ecf2; border-radius: 16px; padding: 14px 10px; }
.fb-toc-title { display: block; line-height: 1.4; padding: 4px 0 6px 10px; margin: 0; font-size: 11px; letter-spacing: .1em; color: #9ca3af; font-weight: 700; }
.st-key-fb_toc [data-testid="stButton"] button {
    width: 100% !important; justify-content: flex-start !important; text-align: left !important;
    border: 0 !important; background: transparent !important; box-shadow: none !important;
    border-radius: 10px !important; padding: 11px 10px !important; min-height: 0 !important; height: auto !important;
}
.st-key-fb_toc [data-testid="stButton"] button:hover { background: #f5f7fb !important; }
.st-key-fb_toc [data-testid="stButton"] button[kind="primary"] { background: #eef3ff !important; }
.st-key-fb_toc [data-testid="stButton"] button p {
    font-size: 13px !important; line-height: 1.55 !important; color: #4b5563 !important;
    text-align: left !important; white-space: normal !important;
}
.st-key-fb_toc [data-testid="stButton"] button[kind="primary"] p { color: #111827 !important; font-weight: 600 !important; }

.fb-detail { background: #fff; border: 1px solid #e9ecf2; border-radius: 18px; padding: 28px 30px; }
.fb-dh { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; margin-bottom: 22px; }
.fb-dh small { font-size: 13px; font-weight: 800; color: #3b6def; }
.fb-dh .qt { margin: 6px 0 0; font-size: 21px; line-height: 1.55; letter-spacing: -.01em; color: #111827; padding: 0; }
.fb-dh .s { text-align: right; flex-shrink: 0; }
.fb-dh .s b { display: block; font-size: 36px; font-weight: 800; line-height: 1; }
.fb-pill { display: inline-block; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 999px; margin-top: 8px; }
.fb-cmp { display: grid; grid-template-columns: 1fr 1fr; border: 1px solid #eef0f4; border-radius: 16px; overflow: hidden; }
.fb-cmp > div { padding: 22px 24px; }
.fb-cmp > div + div { border-left: 1px solid #eef0f4; background: #f7f9ff; }
.fb-lbl { font-size: 12.5px; font-weight: 700; color: #6b7280; margin: 0 0 12px; display: flex; gap: 6px; align-items: center; }
.fb-cmp > div + div .fb-lbl { color: #3b6def; }
.fb-cmp p.t { margin: 0; font-size: 14.5px; line-height: 1.9; color: #374151; }
.fb-cmp > div + div p.t { color: #111827; }

/* 이전 · 다음 */
.st-key-fb_nav { margin-top: 16px; }
.st-key-fb_nav [data-testid="stHorizontalBlock"] { align-items: center !important; }
.st-key-fb_nav [data-testid="stButton"] button { border-radius: 10px !important; min-height: 42px !important; padding: 0 18px !important; }
.st-key-fb_nav [data-testid="stButton"] p { white-space: nowrap !important; font-weight: 700 !important; font-size: 13.5px !important; }
.st-key-fb_next [data-testid="stButton"] { display: flex; justify-content: flex-end; }
.fb-pos { text-align: center; font-size: 13px; color: #9ca3af; }

.fb-card .tt, .fb-dh .qt { font-weight: 700; }

[data-testid="stElementContainer"]:has(.fb-hero) { margin-bottom: 22px !important; }
.fb-lbl { font-size: 12.5px !important; }

[data-testid="stElementContainer"]:has(.fb-toc-title) { min-height: 26px !important; margin-bottom: 2px !important; overflow: visible !important; }
[data-testid="stElementContainer"]:has(.fb-detail) { margin-bottom: 16px !important; }
.st-key-fb_next, .st-key-fb_next [data-testid="stElementContainer"], .st-key-fb_next [data-testid="stButton"] { width: 100% !important; }
.st-key-fb_next [data-testid="stButton"] { display: flex !important; justify-content: flex-end !important; }
.st-key-fb_nav [data-testid="stButton"] button { width: auto !important; }

@media (max-width: 900px) {
    .fb-hero, .fb-cmp { grid-template-columns: 1fr; }
    .fb-bars.two { grid-template-columns: 1fr; grid-auto-flow: row; }
    .fb-cmp > div + div { border-left: 0; border-top: 1px solid #eef0f4; }
}

@media print {
    [data-testid="stSidebar"],
    header, footer,
    [data-testid="stToolbar"],
    [data-testid="stStatusWidget"],
    [data-testid="stDecoration"],
    .st-key-fb_nav,
    [data-pdf-btn] { display: none !important; }
    [data-testid="stMain"] { margin-left: 0 !important; }
    [data-testid="stMainBlockContainer"] { padding: 24px 32px !important; }
    body, [data-testid="stAppViewContainer"] { background: white !important; }
}
</style>""", unsafe_allow_html=True)

# ── 데이터 (실제 GET .../feedback) ──────────────────────────────────────
ALL_QA = [
    {
        "q":      fb["question"],
        "score":  fb["score"],
        "my":     fb["my_answer"],
        "better": fb["improved_answer"],
    }
    for fb in (feedback_data.get("feedbacks") if feedback_data else None) or []
]

_now  = datetime.now()
today = f"{_now.month}월 {_now.day}일"

# ── 데이터가 없을 때 ───────────────────────────────────────────────────────
if not ALL_QA:
    st.markdown(
        '<div style="margin-bottom:28px;">'
        '<div style="font-size:24px;font-weight:700;color:#111827;margin:0 0 6px;">질문별 피드백 보고서</div>'
        '</div>',
        unsafe_allow_html=True
    )
    if not session_id:
        show_error_once("면접 세션 정보가 없습니다. 면접을 먼저 진행해주세요.", "feedback_no_session")
    else:
        show_error_once("아직 생성된 피드백이 없습니다. 면접을 끝까지 완료한 뒤 다시 시도해주세요.", "feedback_not_ready")
    render_session_expired_banner()
    st.stop()


def _esc(text) -> str:
    return html.escape(str(text or "")).replace("\r\n", "\n").replace("\n", "<br>")


def _grade(score: int) -> tuple[str, str, str]:
    if score >= 80:
        return "우수", "#16a34a", "#f0fdf4"
    if score >= 65:
        return "보통", "#d97706", "#fffbeb"
    return "개선 필요", "#cf5e96", "#fdf3f8"


def _toc_color(score: int) -> str:
    if score >= 80:
        return "green"
    if score >= 65:
        return "orange"
    return "red"


total = len(ALL_QA)
avg_score = round(sum(qa["score"] for qa in ALL_QA) / total)
_avg_name, _avg_color, _ = _grade(avg_score)

# 보고 있는 질문 번호 — 다른 면접으로 바뀌면 처음 질문부터
if st.session_state.get("fb_sid") != session_id:
    st.session_state.fb_sid = session_id
    st.session_state.fb_idx = 0
idx = min(max(st.session_state.get("fb_idx", 0), 0), total - 1)
st.session_state.fb_idx = idx

# ── 표지 + 질문별 점수 ─────────────────────────────────────────────────────
_bars = "".join(
    f'<div class="fb-bar"><em>Q{n}</em>'
    f'<span class="t"><i style="width:{max(2, min(100, qa["score"]))}%;background:{_grade(qa["score"])[1]};"></i></span>'
    f'<b style="color:{_grade(qa["score"])[1]};">{qa["score"]}점</b></div>'
    for n, qa in enumerate(ALL_QA, start=1)
)
_two = total > 4
st.markdown(
    '<div class="fb-hero">'
    + cover_html("FEEDBACK REPORT", f"{today} · 총 {total}개 질문", ["질문별", "피드백 보고서"],
                 score_bottom(["질문 평균 점수"], avg_score, _avg_name, _avg_color))
    + '<div class="fb-card"><div class="tt">질문별 점수</div>'
    '<p class="d">80점 이상 우수 · 65점 이상 보통 · 왼쪽 목록에서 질문을 고르면 자세히 볼 수 있어요</p>'
    f'<div class="fb-bars{" two" if _two else ""}" '
    f'style="grid-template-rows:repeat({(total + 1) // 2 if _two else total},auto);">{_bars}</div></div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── 목록 + 상세 ───────────────────────────────────────────────────────────
col_toc, col_main = st.columns([300, 860])

with col_toc:
    with st.container(key="fb_toc"):
        st.markdown('<div class="fb-toc-title">질문 목록</div>', unsafe_allow_html=True)
        for n, qa in enumerate(ALL_QA):
            q_short = qa["q"].replace("\n", " ").strip()
            if len(q_short) > 40:
                q_short = q_short[:40] + "…"
            q_short = q_short.replace("[", "［").replace("]", "］").replace("*", "＊").replace("_", "＿")
            label = f"**Q{n + 1}** · {q_short} · :{_toc_color(qa['score'])}[**{qa['score']}**]"
            if st.button(label, key=f"fb_q_{n}", type="primary" if n == idx else "secondary"):
                st.session_state.fb_idx = n
                st.rerun()

with col_main:
    qa = ALL_QA[idx]
    g_name, g_color, g_bg = _grade(qa["score"])
    st.markdown(
        '<div class="fb-detail">'
        '<div class="fb-dh"><div>'
        f'<small>Q{idx + 1} / {total}</small><div class="qt">{_esc(qa["q"])}</div></div>'
        f'<div class="s"><b style="color:{g_color}">{qa["score"]}</b>'
        f'<span class="fb-pill" style="color:{g_color};background:{g_bg};">{g_name}</span></div></div>'
        '<div class="fb-cmp">'
        '<div><div class="fb-lbl"><i class="ph-bold ph-user"></i>내 답변</div>'
        f'<p class="t">{_esc(qa["my"])}</p></div>'
        '<div><div class="fb-lbl"><i class="ph-bold ph-lightbulb"></i>이렇게 답해 보세요</div>'
        f'<p class="t">{_esc(qa["better"])}</p></div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    with st.container(key="fb_nav"):
        c_prev, c_pos, c_next = st.columns([1, 1, 1])
        with c_prev:
            if st.button(f"＜ Q{idx} 이전 질문" if idx > 0 else "＜ 이전 질문", key="fb_prev", disabled=(idx == 0)):
                st.session_state.fb_idx = idx - 1
                st.rerun()
        with c_pos:
            st.markdown(f'<div class="fb-pos">{idx + 1} / {total}</div>', unsafe_allow_html=True)
        with c_next:
            with st.container(key="fb_next"):
                if st.button(f"Q{idx + 2} 다음 질문 ＞" if idx < total - 1 else "다음 질문 ＞", key="fb_next_btn",
                             type="primary", disabled=(idx >= total - 1)):
                    st.session_state.fb_idx = idx + 1
                    st.rerun()

render_session_expired_banner()
