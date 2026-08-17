import requests
import streamlit as st
from components.sidebar import render_sidebar
from utils.state import init_session, get, mark_session_expired, render_session_expired_banner, ensure_latest_session_id
from utils import api

st.set_page_config(
    page_title="이력서 최적화 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
render_sidebar(active="이력서 최적화")

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

resume_id = (optimization or {}).get("resume_id") or get("resume_id")

MATCHED_KEYWORDS = (optimization or {}).get("matched_keywords") or []
MISSING_KEYWORDS = (optimization or {}).get("missing_keywords") or []
SUGGESTIONS = (optimization or {}).get("suggestions") or []

if "resume_applied_result" not in st.session_state:
    st.session_state.resume_applied_result = None  

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

[class*="st-key-chk_wrap_"] {
    display: flex !important;
    align-items: flex-end !important;
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

if not session_id:
    st.error("면접 세션 정보가 없습니다. 면접을 먼저 진행해주세요.")
elif optimization is None:
    st.error("최적화 제안을 불러오지 못했습니다. 면접을 끝까지 완료한 뒤 다시 시도해주세요.")
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
        '<div style="font-size:13px;font-weight:600;color:#1f1f1f;margin-bottom:12px;">보유 키워드</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:10px;">{_kw_tags(MATCHED_KEYWORDS, "#e0edff", "#3d78f2")}</div>'
        '</div>'
    )
    if MISSING_KEYWORDS:
        kw_html += (
            '<div style="padding-bottom:24px;">'
            '<div style="font-size:13px;font-weight:600;color:#1f1f1f;margin-bottom:12px;">추가 추천 키워드</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:10px;">{_kw_tags(MISSING_KEYWORDS, "#fff3e0", "#d97706")}</div>'
            '</div>'
        )
    kw_html += '<div style="font-size:14px;font-weight:600;color:#1f1f1f;padding-bottom:24px;">항목별 최적화 제안</div>'
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
            f'<div style="font-size:12px;font-weight:600;color:#3d78f2;margin-bottom:10px;">{section}</div>'
            '<div style="display:flex;align-items:stretch;gap:16px;">'
            f'<div style="flex:1 1 0;min-width:0;background:#fcf7f7;border:1px solid #dedede;border-radius:10px;padding:11px;min-height:120px;box-sizing:border-box;">'
            '<span style="background:#ffe0e0;color:#bf2626;font-size:11px;font-weight:500;padding:4px 8px;border-radius:6px;display:inline-block;margin-bottom:10px;">기존</span>'
            f'<p style="font-size:13px;color:#593333;line-height:1.6;margin:0;">{original}</p>'
            '</div>'
            '<span style="font-size:20px;font-weight:700;color:#3d78f2;flex-shrink:0;align-self:center;">→</span>'
            f'<div style="flex:1 1 0;min-width:0;background:#f2fcf5;border:1px solid #dedede;border-radius:10px;padding:11px;min-height:120px;box-sizing:border-box;">'
            '<span style="background:#e0edff;color:#3d78f2;font-size:11px;font-weight:500;padding:4px 8px;border-radius:6px;display:inline-block;margin-bottom:10px;">개선 제안</span>'
            f'<p style="font-size:13px;color:#1a478c;line-height:19px;margin:0;">{improved}</p>'
            f'{reason_html}'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="height:40px"></div>', unsafe_allow_html=True)
        _spacer_col, _chk_col = st.columns([1, 1])
        with _chk_col:
            with st.container(key=f"chk_wrap_{sid}"):
                st.checkbox("이 제안 적용", value=True, key=f"suggest_sel_{sid}")

    st.markdown('<div style="height:36px"></div>', unsafe_allow_html=True)

    applied = st.session_state.resume_applied_result
    if applied:
        st.success(f"{applied['applied_count']}개 제안을 적용해 새 이력서를 만들었습니다.")
        try:
            docx_bytes = api.download_resume(applied["resume_id"])
            st.download_button(
                "최적화 이력서 다운로드 (docx)",
                data=docx_bytes,
                file_name=f"resume_{applied['resume_id']}.docx",
                key="dl_real_btn",
                type="primary",
            )
        except api.SessionExpiredError:
            mark_session_expired()
        except Exception as e:
            st.error(f"다운로드 파일을 만들지 못했습니다: {e}")

    with st.container(key="bottom_row"):
        if st.button("건너뛰기", key="skip_btn"):
            st.switch_page("pages/08_마이페이지.py")

        if st.session_state.get("resume_apply_msg"):
            _level, _text = st.session_state.resume_apply_msg
            getattr(st, _level)(_text)

        if st.button("선택한 제안 적용하기", key="apply_btn", type="primary"):
            selected_ids = [
                s.get("id", i) for i, s in enumerate(SUGGESTIONS)
                if st.session_state.get(f"suggest_sel_{s.get('id', i)}", True)
            ]
            if not selected_ids:
                st.session_state.resume_apply_msg = ("warning", "적용할 제안을 하나 이상 선택해주세요.")
                st.rerun()
            elif not resume_id:
                st.session_state.resume_apply_msg = ("error", "이력서 정보가 없습니다.")
                st.rerun()
            else:
                try:
                    st.session_state.resume_applied_result = api.apply_resume_optimization(
                        resume_id, session_id, suggestion_ids=selected_ids
                    )
                    st.session_state.resume_apply_msg = None
                    st.rerun()
                except api.SessionExpiredError:
                    mark_session_expired()
                except requests.exceptions.HTTPError as e:
                    try:
                        detail = e.response.json().get("detail")
                    except Exception:
                        detail = None
                    st.session_state.resume_apply_msg = (
                        "error", detail or "제안을 적용하지 못했습니다. 잠시 후 다시 시도해주세요."
                    )
                    st.rerun()
                except Exception as e:
                    st.session_state.resume_apply_msg = ("error", f"제안을 적용하지 못했습니다: {e}")
                    st.rerun()

render_session_expired_banner()
