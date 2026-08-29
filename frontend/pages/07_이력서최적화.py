import streamlit as st
from components.sidebar import render_sidebar
from utils.state import init_session, get, set as state_set, mark_session_expired, render_session_expired_banner, ensure_latest_session_id
from utils.ui import show_error, show_error_once
from utils import api

st.set_page_config(
    page_title="이력서 최적화 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
render_sidebar(active="이력서 최적화")

_sid_param = st.query_params.get("sid")
if _sid_param and _sid_param != get("session_id"):
    state_set("session_id", _sid_param)

ensure_latest_session_id()

session_id = get("session_id")

optimization = None
if session_id:
    try:
        optimization = api.get_resume_optimization(session_id)
    except api.SessionExpiredError:
        mark_session_expired()
    except Exception:
        optimization = None

MATCHED_KEYWORDS = (optimization or {}).get("matched_keywords") or []
MISSING_KEYWORDS = (optimization or {}).get("missing_keywords") or []
SUGGESTIONS = (optimization or {}).get("suggestions") or []

# ── CSS ───────────────────────────────────────────────────────────────────
st.markdown("""<style>
[data-testid="stMainBlockContainer"] {
    padding: 36px 40px 80px 40px !important;
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
}
[data-testid="stVerticalBlock"] { gap: 0 !important; }

[data-testid="stBaseButton-primary"] {
    font-size: 13px !important;
    padding: 12px 50px !important;
    width: auto !important;
}
[data-testid="stBaseButton-secondary"] {
    font-size: 14px !important;
    padding: 12px 50px !important;
    height: auto !important;
    width: auto !important;
    border-radius: 10px !important;
    font-family: 'Pretendard', -apple-system, sans-serif !important;
    font-weight: 500 !important;
}
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-secondary"] p {
    white-space: nowrap !important;
}

.st-key-bottom_row,
.st-key-bottom_row > div,
.st-key-bottom_row [data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    justify-content: space-between !important;
    align-items: center !important;
}
.st-key-bottom_row [data-testid="stElementContainer"] {
    width: auto !important;
}
</style>""", unsafe_allow_html=True)

# ── 헤더 ──────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="margin-bottom:28px;">'
    '<div style="font-size:24px;font-weight:700;color:#111827;margin:0 0 6px;">이력서 자동 최적화</div>'
    '<p style="font-size:14px;color:#9ca3af;margin:0;">면접 답변 기반으로 JD에 최적화된 문구를 제안해드립니다.</p>'
    '</div>',
    unsafe_allow_html=True
)

if not session_id:
    show_error_once("면접 세션 정보가 없습니다. 면접을 먼저 진행해주세요.", "resume_opt_no_session")
elif optimization is None:
    show_error_once("최적화 제안을 불러오지 못했습니다. 면접을 끝까지 완료한 뒤 다시 시도해주세요.", "resume_opt_fetch_failed")
elif not SUGGESTIONS:
    st.info("이 면접에서는 아직 생성된 최적화 제안이 없습니다.")
else:
    # ── 키워드 ────────────────────────────────────────────────────────────
    def _kw_tags(keywords, bg, color):
        return "".join(
            f'<span style="background:{bg};color:{color};border-radius:14px;'
            f'padding:6px 12px;font-size:12px;font-weight:500;white-space:nowrap;">{kw}</span>'
            for kw in keywords
        )

    kw_html = (
        '<div style="padding-bottom:20px;">'
        '<div style="font-size:13px;font-weight:600;color:#111827;margin-bottom:12px;">보유 키워드</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:10px;">{_kw_tags(MATCHED_KEYWORDS, "#eef3ff", "#3b6def")}</div>'
        '</div>'
    )
    if MISSING_KEYWORDS:
        kw_html += (
            '<div style="padding-bottom:24px;">'
            '<div style="font-size:13px;font-weight:600;color:#111827;margin-bottom:12px;">추가 추천 키워드</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:10px;">{_kw_tags(MISSING_KEYWORDS, "#fff3e0", "#d97706")}</div>'
            '</div>'
        )
    kw_html += '<div style="font-size:14px;font-weight:600;color:#111827;padding-bottom:24px;">항목별 최적화 제안</div>'
    st.markdown(kw_html, unsafe_allow_html=True)

    # ── 제안 카드 (체크박스로 선택 — 백엔드 적용은 한 번에 배치로 이뤄진다) ──
    for i, s in enumerate(SUGGESTIONS):
        sid       = s.get("id", i)
        section   = s.get("section") or "제안"
        original  = s.get("original") or ""
        improved  = s.get("improved") or ""
        reason    = s.get("reason") or ""

        if i > 0:
            st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

        reason_html = (
            f'<p style="font-size:12px;color:#6b7280;margin:8px 0 0;">💡 {reason}</p>'
            if reason else ""
        )
        st.markdown(
            f'<div style="font-size:12px;font-weight:600;color:#3b6def;margin-bottom:10px;">{section}</div>'
            '<div style="display:flex;align-items:stretch;gap:16px;">'
            f'<div style="flex:1 1 0;min-width:0;background:#fcf7f7;border:1px solid #e5e7eb;border-radius:10px;padding:11px;min-height:120px;box-sizing:border-box;">'
            '<span style="background:#ffe0e0;color:#bf2626;font-size:11px;font-weight:500;padding:4px 8px;border-radius:6px;display:inline-block;margin-bottom:10px;">기존</span>'
            f'<p style="font-size:13px;color:#593333;line-height:1.6;margin:0;">{original}</p>'
            '</div>'
            '<span style="font-size:20px;font-weight:700;color:#3b6def;flex-shrink:0;align-self:center;">→</span>'
            f'<div style="flex:1 1 0;min-width:0;background:#f2fcf5;border:1px solid #e5e7eb;border-radius:10px;padding:11px;min-height:120px;box-sizing:border-box;">'
            '<span style="background:#eef3ff;color:#3b6def;font-size:11px;font-weight:500;padding:4px 8px;border-radius:6px;display:inline-block;margin-bottom:10px;">개선 제안</span>'
            f'<p style="font-size:13px;color:#2563eb;line-height:19px;margin:0;">{improved}</p>'
            f'{reason_html}'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="height:40px"></div>', unsafe_allow_html=True)


render_session_expired_banner()
