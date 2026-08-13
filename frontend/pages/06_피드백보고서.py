import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from components.sidebar import render_sidebar
from utils.state import init_session, get, mark_session_expired, render_session_expired_banner, ensure_latest_session_id
from utils import api

st.set_page_config(
    page_title="피드백 보고서 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
render_sidebar(active="피드백 보고서")

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

st.markdown("""
<div style="position:fixed;top:0;right:0;height:60px;
            display:flex;align-items:center;padding:0 24px;z-index:600;">
  <div data-pdf-btn style="background:#3b6def;color:white;font-size:13px;font-weight:500;
              height:36px;padding:0 18px;border-radius:8px;cursor:pointer;
              display:flex;align-items:center;user-select:none;">PDF 다운로드</div>
</div>
""", unsafe_allow_html=True)
components.html("""
<script>
(function () {
    function attach() {
        var doc = window.parent.document;
        var btn = doc.querySelector('[data-pdf-btn]');
        if (!btn) { setTimeout(attach, 300); return; }
        btn.onclick = function () { window.parent.print(); };
    }
    attach();
}());
</script>
""", height=0)

# ── CSS ───────────────────────────────────────────────────────────────────
st.markdown("""<style>
[data-testid="stMainBlockContainer"] {
    padding: 36px 40px 60px 40px !important;
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
}
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stHorizontalBlock"] { gap: 0 !important; }

.st-key-pagination,
.st-key-pagination > div,
.st-key-pagination [data-testid="stVerticalBlockBorderWrapper"],
.st-key-pagination [data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    justify-content: center !important;
    align-items: center !important;
    gap: 20px !important;
}
.st-key-pagination [data-testid="stElementContainer"] {
    width: auto !important;
}
[data-page-number] {
    font-size: 14px !important;
    color: #a6a6a6 !important;
    position: relative !important;
    top: -2px !important;
}
[data-testid="stBaseButton-secondary"] {
    width: auto !important;
}

@media print {
    [data-testid="stSidebar"],
    header, footer,
    [data-testid="stToolbar"],
    [data-testid="stStatusWidget"],
    [data-testid="stDecoration"],
    [data-testid="stHorizontalBlock"],
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

ITEMS_PER_PAGE = 3

if "fb_page" not in st.session_state:
    st.session_state.fb_page = 0

_now         = datetime.now()
today        = f"{_now.month}월 {_now.day}일"

# ── 헤더 ──────────────────────────────────────────────────────────────────
if not ALL_QA:
    st.markdown(
        '<div style="margin-bottom:28px;">'
        '<div style="font-size:24px;font-weight:700;color:#1f1f1f;margin:0 0 6px;">질문별 피드백 보고서</div>'
        '</div>',
        unsafe_allow_html=True
    )
    if not session_id:
        st.error("면접 세션 정보가 없습니다. 면접을 먼저 진행해주세요.")
    else:
        st.info("아직 생성된 피드백이 없습니다. 면접을 끝까지 완료한 뒤 다시 시도해주세요.")
    render_session_expired_banner()
    st.stop()

avg_score    = round(sum(qa["score"] for qa in ALL_QA) / len(ALL_QA))
total_pages  = (len(ALL_QA) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
page_idx     = st.session_state.fb_page
current_qa   = ALL_QA[page_idx * ITEMS_PER_PAGE : (page_idx + 1) * ITEMS_PER_PAGE]

st.markdown(
    '<div style="margin-bottom:28px;">'
    '<div style="font-size:24px;font-weight:700;color:#1f1f1f;margin:0 0 6px;">질문별 피드백 보고서</div>'
    f'<p style="font-size:14px;color:#a6a6a6;margin:0;">총 {len(ALL_QA)}개 질문 &nbsp;|&nbsp; 평균 점수 {avg_score}점 &nbsp;|&nbsp; {today}</p>'
    '</div>',
    unsafe_allow_html=True
)

# ── QA 카드 ───────────────────────────────────────────────────────────────
cards_html = ""
for i, qa in enumerate(current_qa):
    q_num = page_idx * ITEMS_PER_PAGE + i + 1
    score = qa["score"]
    if score >= 70:
        badge_bg, badge_color = "#def7de", "#2ea647"
    else:
        badge_bg, badge_color = "#ffedde", "#eb8c14"

    cards_html += (
        '<div style="background:white;border:1px solid #dedede;border-radius:12px;overflow:hidden;margin-bottom:12px;">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;padding:15px 19px 13px;">'
        f'<div style="font-size:14px;font-weight:600;color:#1f1f1f;flex:1;margin-right:12px;line-height:1.5;">Q{q_num}. {qa["q"]}</div>'
        f'<div style="background:{badge_bg};border-radius:13px;height:26px;min-width:56px;padding:0 10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">'
        f'<span style="font-size:12px;font-weight:500;color:{badge_color};">{score}점</span>'
        '</div>'
        '</div>'
        '<div style="height:1px;background:#dedede;margin:0 19px;"></div>'
        '<div style="padding:13px 19px 13px;">'
        '<div style="font-size:11px;font-weight:500;color:#a6a6a6;margin-bottom:6px;">내 답변</div>'
        f'<div style="font-size:13px;color:#1f1f1f;line-height:1.65;">{qa["my"]}</div>'
        '</div>'
        '<div style="height:1px;background:#e0edff;margin:0 19px;"></div>'
        '<div style="padding:13px 19px 16px;">'
        '<div style="font-size:11px;font-weight:500;color:#3d78f2;margin-bottom:6px;">개선 답변 제안</div>'
        f'<div style="font-size:13px;color:#264db2;line-height:21px;">{qa["better"]}</div>'
        '</div>'
        '</div>'
    )

st.markdown(cards_html + '<div style="height:16px"></div>', unsafe_allow_html=True)

# ── 페이지네이션 ──────────────────────────────────────────────────────────
with st.container(key="pagination"):
    if st.button("＜", disabled=(page_idx == 0)):
        st.session_state.fb_page -= 1
        st.rerun()
    st.markdown(
        f'<span data-page-number>{page_idx + 1} / {total_pages}</span>',
        unsafe_allow_html=True,
    )
    if st.button("＞", disabled=(page_idx >= total_pages - 1)):
        st.session_state.fb_page += 1
        st.rerun()

render_session_expired_banner()
