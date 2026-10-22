import difflib
import html
import re
import streamlit as st
import streamlit.components.v1 as components
from utils.brand import FAVICON
from components.sidebar import render_sidebar
from components.report_cover import COVER_CSS, cover_html, score_bottom, stats_bottom
from utils.state import init_session, get, set as state_set, mark_session_expired, render_session_expired_banner, ensure_latest_session_id
from utils.ui import show_error_once
from utils import api

st.set_page_config(
    page_title="이력서 최적화 | intro",
    page_icon=FAVICON,
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
st.markdown(COVER_CSS, unsafe_allow_html=True)
st.markdown("""<style>
[data-testid="stMainBlockContainer"] {
    padding: 32px 40px 80px 40px !important;
    max-width: 1240px !important;
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
}
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stHorizontalBlock"] { gap: 22px !important; align-items: flex-start !important; }

.ro-hero { display: grid; grid-template-columns: 360px 1fr; gap: 20px; margin-bottom: 24px; }
.ro-card { background: #fff; border: 1px solid #e9ecf2; border-radius: 18px; padding: 22px 24px; }
.ro-card .tt { margin: 0 0 4px; font-size: 16px; color: #111827; padding: 0; }
.ro-card .d { margin: 0 0 16px; font-size: 13px; color: #6b7280; }
.ro-meter { display: flex; height: 12px; border-radius: 6px; overflow: hidden; margin-bottom: 8px; background: #fde7c4; }
.ro-meter i { display: block; background: #3b6def; }
.ro-ml { display: flex; justify-content: space-between; font-size: 12.5px; color: #6b7280; margin-bottom: 16px; }
.ro-krow { display: grid; grid-template-columns: 112px 1fr; gap: 12px; align-items: start; margin-bottom: 10px; }
.ro-krow b { font-size: 13px; padding-top: 6px; color: #111827; }
.ro-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.ro-chips span { font-size: 12.5px; font-weight: 600; padding: 5px 10px; border-radius: 8px; }
.ro-chips.have span { background: #eef3ff; color: #2453c9; }
.ro-chips.need span { background: #fff; border: 1px dashed #f5c27a; color: #b45309; }

.ro-toc { background: #fff; border: 1px solid #e9ecf2; border-radius: 16px; padding: 14px 10px; }
.ro-toc .th { margin: 4px 0 8px 10px; font-size: 11px; letter-spacing: .1em; color: #9ca3af; padding: 0; }
.ro-toc a { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 11px 10px; border-radius: 10px;
    font-size: 13.5px; color: #4b5563 !important; text-decoration: none !important; }
.ro-toc a:hover { background: #eef3ff; color: #111827 !important; }
.ro-toc a span.n { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ro-t { flex-shrink: 0; font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 999px; }
.ro-t.e { background: #eef3ff; color: #2453c9; } .ro-t.n { background: #ecfdf5; color: #047857; }

.ro-doc { background: #fff; border: 1px solid #e9ecf2; border-radius: 18px; padding: 30px 34px 10px; }
.ro-dh { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 6px; flex-wrap: wrap; }
.ro-dh .tt { margin: 0; font-size: 19px; color: #111827; padding: 0; }
.ro-legend { display: flex; gap: 12px; font-size: 12px; }
.ro-dd { margin: 0 0 22px; font-size: 13px; color: #6b7280; }
.ro-item { border-left: 3px solid #e5e7eb; padding: 4px 0 4px 18px; margin-bottom: 26px; scroll-margin-top: 20px; }
.ro-item:target { border-left-color: #3b6def; }
.ro-ih { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.ro-ih b { font-size: 14.5px; color: #111827; }
.ro-copy { margin-left: auto; display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 700; color: #3b6def;
    background: white; border: 1px solid #d6e1fd; border-radius: 8px; padding: 4px 9px; cursor: pointer; font-family: inherit; }
.ro-copy:hover { border-color: #3b6def; }
.ro-copy.done { color: #16a34a; border-color: #bbf7d0; }
.ro-track { font-size: 15px; line-height: 1.95; color: #111827; margin: 0; }
.ro-del { color: #9ca3af; text-decoration: line-through; text-decoration-color: #cf5e96; background: #fdf3f8; border-radius: 3px; padding: 0 3px; }
.ro-ins { background: #e3ebff; color: #1e3a8a; border-radius: 3px; padding: 0 3px; font-weight: 600; }
.ro-add { background: #dcfce7; color: #14532d; border-radius: 3px; padding: 0 3px; font-weight: 600; }
.ro-why { margin-top: 10px; font-size: 13px; color: #4b5563; display: flex; gap: 7px; line-height: 1.7; }
.ro-why i { color: #d97706; margin-top: 3px; flex-shrink: 0; }

.ro-card .tt, .ro-toc .th, .ro-dh .tt { font-weight: 700; }

[data-testid="stElementContainer"]:has(.ro-hero) { margin-bottom: 22px !important; }

/* 하단 안내 */
[data-testid="stElementContainer"]:has(.ro-notice) { margin-top: 38px !important; }   /* 마크다운 블록의 -16px 여백을 상쇄 */
.ro-notice { display: flex; align-items: center; gap: 12px; background: #f0f4ff; border: 1px solid #c7d7fb;
    border-radius: 14px; padding: 16px 22px; font-size: 14px; line-height: 1.6; color: #374151; }
.ro-notice b { color: #111827; }
.ro-notice .ico { width: 24px; height: 24px; border-radius: 50%; background: #3b6def; color: #fff; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; font-size: 14px; }

@media (max-width: 900px) {
    .ro-hero { grid-template-columns: 1fr; }
    .ro-krow { grid-template-columns: 1fr; }
}
</style>""", unsafe_allow_html=True)


def _esc(text) -> str:
    return html.escape(str(text or "")).replace("\r\n", "\n").replace("\n", "<br>")


def _tokens(text: str) -> list[str]:
    return re.findall(r"\s+|[^\s]+", text)


def _tracked_html(original: str, improved: str) -> str:
    a, b = _tokens(original), _tokens(improved)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if sm.ratio() < 0.35:
        return (f'<span class="ro-del">{_esc(original)}</span> '
                f'<span class="ro-ins">{_esc(improved)}</span>')
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        old, new = "".join(a[i1:i2]), "".join(b[j1:j2])
        if op == "equal":
            out.append(html.escape(old))
            continue
        if old.strip():
            out.append(f'<span class="ro-del">{html.escape(old)}</span>')
        elif old:
            out.append(html.escape(old))
        if new.strip():
            out.append(f'<span class="ro-ins">{html.escape(new)}</span>')
        elif new:
            out.append(html.escape(new))
    return "".join(out).replace("\r\n", "\n").replace("\n", "<br>")


if not session_id or optimization is None or not SUGGESTIONS:
    # ── 데이터가 없을 때: 기존 안내 그대로 ─────────────────────────────────
    st.markdown(
        '<div style="margin-bottom:28px;">'
        '<div style="font-size:24px;font-weight:700;color:#111827;margin:0 0 6px;">이력서 자동 최적화</div>'
        '<p style="font-size:14px;color:#6b7280;margin:0;">면접 답변 기반으로 JD에 최적화된 문구를 제안해드립니다.</p>'
        '</div>',
        unsafe_allow_html=True
    )
    if not session_id:
        show_error_once("면접 세션 정보가 없습니다. 면접을 먼저 진행해주세요.", "resume_opt_no_session")
    elif optimization is None:
        show_error_once("최적화 제안을 불러오지 못했습니다. 면접을 끝까지 완료한 뒤 다시 시도해주세요.", "resume_opt_fetch_failed")
    else:
        st.info("이 면접에서는 아직 생성된 최적화 제안이 없습니다.")
else:
    # ── 표지 + JD 키워드 ───────────────────────────────────────────────────
    def _chips(keywords):
        return "".join(f"<span>{html.escape(str(kw))}</span>" for kw in keywords)

    n_have, n_need = len(MATCHED_KEYWORDS), len(MISSING_KEYWORDS)
    n_all = n_have + n_need
    pct = round(n_have / n_all * 100) if n_all else 0
    kw_html = (
        '<div class="ro-card"><div class="tt">JD 키워드</div>'
        + (f'<p class="d">채용공고(JD)가 찾는 키워드 {n_all}개 중 {n_have}개가 이력서·답변에 드러나 있어요</p>'
           f'<div class="ro-meter"><i style="width:{pct}%"></i></div>'
           f'<div class="ro-ml"><span>보유 {n_have}개 · {pct}%</span>'
           + (f'<span>추가하면 {n_all}개 모두</span>' if n_need else '<span>모두 드러나 있어요</span>') + '</div>'
           if n_all else '<p class="d">이번 면접에서 확인된 JD 키워드가 없어요</p>')
        + (f'<div class="ro-krow"><b>보유 키워드</b><div class="ro-chips have">{_chips(MATCHED_KEYWORDS)}</div></div>'
           if MATCHED_KEYWORDS else '')
        + (f'<div class="ro-krow"><b style="color:#b45309">추가하면 좋은<br>키워드</b><div class="ro-chips need">{_chips(MISSING_KEYWORDS)}</div></div>'
           if MISSING_KEYWORDS else '')
        + '</div>'
    )
    st.markdown(
        '<div class="ro-hero">'
        + cover_html("RESUME OPTIMIZATION", "면접 답변 기반 · JD 맞춤 문구 제안", ["이력서", "자동 최적화"],
                     stats_bottom([("제안", len(SUGGESTIONS)), ("보유 키워드", n_have), ("추가 추천", n_need)]))
        + kw_html + '</div>',
        unsafe_allow_html=True,
    )

    # ── 목차 + 고친 내용 ──────────────────────────────────────────────────
    # 기존 문장이 비어 있으면 서버가 "없음"을 보내므로, 그 경우는 '새 항목 제안'으로 보여준다.
    items = []
    for i, s in enumerate(SUGGESTIONS):
        section  = s.get("section") or "제안"
        original = (s.get("original") or "").strip()
        improved = (s.get("improved") or "").strip()
        reason   = (s.get("reason") or "").strip()
        items.append({
            "anchor": f"ro-item-{i + 1}",
            "section": section,
            "original": original,
            "improved": improved,
            "reason": reason,
            "is_new": original in ("", "없음"),
        })

    col_toc, col_main = st.columns([260, 900])

    with col_toc:
        toc = "".join(
            f'<a href="#{it["anchor"]}" target="_self"><span class="n">{html.escape(it["section"])}</span>'
            + ('<span class="ro-t n">새 항목</span>' if it["is_new"] else '<span class="ro-t e">수정</span>')
            + '</a>'
            for it in items
        )
        st.markdown(f'<div class="ro-toc"><div class="th">항목별 최적화 제안</div>{toc}</div>', unsafe_allow_html=True)

    with col_main:
        body = ""
        for it in items:
            track = (f'<span class="ro-add">{_esc(it["improved"])}</span>' if it["is_new"]
                     else _tracked_html(it["original"], it["improved"]))
            body += (
                f'<div class="ro-item" id="{it["anchor"]}"><div class="ro-ih"><b>{html.escape(it["section"])}</b>'
                + ('<span class="ro-t n">새 항목 제안</span>' if it["is_new"] else '<span class="ro-t e">문장 수정 제안</span>')
                + f'<button type="button" class="ro-copy" data-copy="{html.escape(it["improved"], quote=True)}">'
                '<i class="ph-bold ph-copy"></i><span>복사</span></button></div>'
                f'<p class="ro-track">{track}</p>'
                + (f'<div class="ro-why"><i class="ph-fill ph-lightbulb"></i><span>{_esc(it["reason"])}</span></div>'
                   if it["reason"] else '')
                + '</div>'
            )
        st.markdown(
            '<div class="ro-doc"><div class="ro-dh"><div class="tt">내 이력서에 고친 내용</div>'
            '<div class="ro-legend"><span class="ro-del">빼기</span><span class="ro-ins">바꾸기</span>'
            '<span class="ro-add">새로 추가</span></div></div>'
            '<div class="ro-dd">고친 부분을 이력서 문장 안에서 바로 보여 줘요 · 복사하면 고친 문장만 복사돼요</div>'
            f'{body}</div>',
            unsafe_allow_html=True,
        )

    # 제안 문구를 그대로 붙여 넣지 않도록 안내한다
    st.markdown(
        '<div class="ro-notice"><span class="ico"><i class="ph-bold ph-info"></i></span>'
        '<span>제안은 <b>수정 방향 안내</b>입니다. 문구를 그대로 쓰기보다, 본인 경험에 맞게 숫자와 맥락을 바꿔 직접 반영해 주세요.</span></div>',
        unsafe_allow_html=True,
    )

    components.html("""
    <script>
    (function () {
      var pw = window.parent, doc = pw.document;
      var gen = String(Date.now()) + Math.random();
      pw.__roCopyGen = gen;
      function markDone(btn) {
        var label = btn.querySelector('span');
        btn.classList.add('done'); if (label) label.textContent = '복사됨';
        setTimeout(function () { btn.classList.remove('done'); if (label) label.textContent = '복사'; }, 1500);
      }
      function fallbackCopy(text, btn) {
        var ta = doc.createElement('textarea');
        ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
        doc.body.appendChild(ta); ta.select();
        try { doc.execCommand('copy'); markDone(btn); } catch (e) {}
        doc.body.removeChild(ta);
      }
      function bind() {
        if (pw.__roCopyGen !== gen) return;
        doc.querySelectorAll('.ro-copy').forEach(function (btn) {
          if (btn.getAttribute('data-gen') === gen) return;
          btn.setAttribute('data-gen', gen);
          btn.onclick = function () {
            var text = btn.getAttribute('data-copy') || '';
            if (pw.navigator.clipboard && pw.isSecureContext) {
              pw.navigator.clipboard.writeText(text).then(function () { markDone(btn); })
                .catch(function () { fallbackCopy(text, btn); });
            } else { fallbackCopy(text, btn); }
          };
        });
      }
      bind();
      var n = 0, iv = setInterval(function () { bind(); if (++n > 40) clearInterval(iv); }, 300);
    })();
    </script>
    """, height=0)


render_session_expired_banner()
