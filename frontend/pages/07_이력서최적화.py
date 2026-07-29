import streamlit as st
import streamlit.components.v1 as components
from components.sidebar import render_sidebar
from utils.state import init_session

st.set_page_config(
    page_title="이력서 최적화 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
render_sidebar(active="이력서 최적화")

JD_KEYWORDS = ["LangGraph", "FastAPI", "비동기 처리", "RAG", "Pydantic", "상태 관리", "GPT-4o"]

SUGGESTIONS = [
    {
        "section": "경력 요약",
        "original": "Python과 FastAPI를 이용한 백엔드 개발 경험이 있습니다.",
        "improved": "LangGraph·FastAPI 기반 AI 면접 에이전트를 설계·개발하여, 비동기 스트리밍 처리로 첫 응답 대기시간을 3초→0.5초로 단축했습니다.",
    },
    {
        "section": "프로젝트 성과",
        "original": "RAG 파이프라인을 구현하여 검색 정확도를 향상시켰습니다.",
        "improved": "FAISS 벡터 DB 기반 RAG 파이프라인을 구축하고, 청크 사이즈 최적화로 검색 정확도 18% 향상 및 LLM 비용 22% 절감을 달성했습니다.",
    },
    {
        "section": "기술 스택",
        "original": "Python, FastAPI, LangChain을 다룰 수 있습니다.",
        "improved": "Python·FastAPI·LangChain·LangGraph(Cyclic) 기반 상태 중심 AI 에이전트 설계 및 Pydantic을 활용한 타입 안전 상태 관리 구현 경험 보유",
    },
]

if "resume_applied" not in st.session_state:
    st.session_state.resume_applied = [False] * len(SUGGESTIONS)

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
    '<div style="font-size:24px;font-weight:700;color:#1f1f1f;margin:0 0 6px;">이력서 자동 최적화</div>'
    '<p style="font-size:14px;color:#a6a6a6;margin:0;">면접 답변 기반으로 JD에 최적화된 문구를 제안해드립니다.</p>'
    '</div>',
    unsafe_allow_html=True
)

# ── JD 키워드 ─────────────────────────────────────────────────────────────
kw_tags = "".join(
    f'<span style="background:#e0edff;color:#3d78f2;border-radius:14px;'
    f'padding:6px 12px;font-size:12px;font-weight:500;white-space:nowrap;">{kw}</span>'
    for kw in JD_KEYWORDS
)
st.markdown(
    '<div style="padding-bottom:24px;">'
    '<div style="font-size:13px;font-weight:600;color:#1f1f1f;margin-bottom:12px;">매칭된 JD 키워드</div>'
    f'<div style="display:flex;flex-wrap:wrap;gap:10px;">{kw_tags}</div>'
    '</div>'
    '<div style="font-size:14px;font-weight:600;color:#1f1f1f;padding-bottom:24px;">항목별 최적화 제안</div>',
    unsafe_allow_html=True
)

# ── 카드 rows (HTML로 전체 렌더링) ─────────────────────────────────────────
rows_html = ""
for i, s in enumerate(SUGGESTIONS):
    applied    = st.session_state.resume_applied[i]
    spacer     = "" if i == 0 else '<div style="height:24px"></div>'
    btn_bg     = "#eef3ff" if applied else "#3d78f2"
    btn_color  = "#3b6def" if applied else "white"
    btn_border = "1px solid #3b6def" if applied else "none"
    btn_label  = "✓ 적용됨" if applied else "적용"

    rows_html += (
        spacer +
        f'<div style="font-size:12px;font-weight:600;color:#3d78f2;margin-bottom:10px;">{s["section"]}</div>'
        '<div style="display:flex;align-items:center;gap:16px;">'
        f'<div style="flex:1;background:#fcf7f7;border:1px solid #dedede;border-radius:10px;padding:11px;min-height:136px;box-sizing:border-box;">'
        '<span style="background:#ffe0e0;color:#bf2626;font-size:11px;font-weight:500;padding:4px 8px;border-radius:6px;display:inline-block;margin-bottom:10px;">기존</span>'
        f'<p style="font-size:13px;color:#593333;line-height:1.6;margin:0;">{s["original"]}</p>'
        '</div>'
        '<span style="font-size:20px;font-weight:700;color:#3d78f2;flex-shrink:0;">→</span>'
        f'<div style="flex:1;background:#f2fcf5;border:1px solid #dedede;border-radius:10px;padding:11px;min-height:136px;box-sizing:border-box;">'
        '<span style="background:#e0edff;color:#3d78f2;font-size:11px;font-weight:500;padding:4px 8px;border-radius:6px;display:inline-block;margin-bottom:10px;">개선 제안</span>'
        f'<p style="font-size:13px;color:#1a478c;line-height:19px;margin:0;">{s["improved"]}</p>'
        '</div>'
        f'<button data-apply="{i}" style="background:{btn_bg};color:{btn_color};border:{btn_border};'
        f'border-radius:8px;font-size:13px;font-weight:500;padding:9px 14px;cursor:pointer;white-space:nowrap;flex-shrink:0;">{btn_label}</button>'
        '</div>'
    )

st.markdown(rows_html + '<div style="height:28px"></div>', unsafe_allow_html=True)

# ── Hidden Streamlit 버튼 (JS가 클릭 트리거) ─────────────────────────────
hidden_cols = st.columns(len(SUGGESTIONS))
for i, col in enumerate(hidden_cols):
    with col:
        if st.button(f"§apply_{i}§", key=f"apply_{i}"):
            st.session_state.resume_applied[i] = not st.session_state.resume_applied[i]
            st.rerun()

# JS: HTML 적용 버튼 → hidden Streamlit 버튼 연결
components.html("""
<script>
(function () {
    function attach() {
        var doc = window.parent.document;
        var applyBtns = doc.querySelectorAll('[data-apply]');
        if (!applyBtns.length) { setTimeout(attach, 300); return; }

        // hidden 버튼 행 숨기기
        doc.querySelectorAll('button').forEach(function (btn) {
            if (btn.innerText.trim().startsWith('§apply_')) {
                var row = btn.closest('[data-testid="stHorizontalBlock"]');
                if (row) row.style.display = 'none';
            }
        });

        // 적용 버튼
        applyBtns.forEach(function (btn) {
            btn.onclick = function () {
                var idx = btn.getAttribute('data-apply');
                doc.querySelectorAll('button').forEach(function (sb) {
                    if (sb.innerText.trim() === '§apply_' + idx + '§') sb.click();
                });
            };
        });
    }
    attach();
    setTimeout(function () {
        new MutationObserver(function () { attach(); })
            .observe(window.parent.document.body, { childList: true, subtree: true });
    }, 600);
}());
</script>
""", height=0)

# ── 하단 버튼 ─────────────────────────────────────────────────────────────
with st.container(key="bottom_row"):
    if st.button("건너뛰기", key="skip_btn"):
        st.switch_page("pages/08_마이페이지.py")

    if st.button("최적화 이력서 다운로드", key="dl_btn", type="primary"):
        st.toast("이력서 다운로드는 백엔드 연동 후 활성화됩니다.", icon="ℹ️")
