import html as htmlmod
import requests
import streamlit as st
from utils.brand import FAVICON
import streamlit.components.v1 as components
from components.sidebar import render_sidebar
from components.setup_steps import SETUP_CSS, steps_html
from utils.state import init_session, get, set as state_set, mark_session_expired, render_session_expired_banner
from utils.ui import show_error
from utils import api

st.set_page_config(
    page_title="문서 업로드 | intro",
    page_icon=FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
render_sidebar(active="면접 시작")

# ── CSS ─────────────────────────────────────────────────────────────────
# 단계 표시·카드·번호 제목은 면접 환경설정 화면과 같은 규칙(components/setup_steps.py)을 쓴다.
st.markdown(SETUP_CSS, unsafe_allow_html=True)
st.markdown("""
<style>
.up-warn { display: flex; gap: 10px; align-items: center; background: #fffbeb; border: 1px solid #fde68a;
    border-radius: 12px; padding: 12px 16px; font-size: 13.5px; color: #92400e; }
.up-warn i { font-size: 18px; flex-shrink: 0; }
.up-warn a { color: #2f5bd8 !important; font-weight: 700; text-decoration: none !important; margin-left: auto;
    white-space: nowrap; }
[data-testid="stElementContainer"]:has(.up-warn) { margin-bottom: 32px !important; }

.up-lab { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; color: #111827; margin-bottom: 10px; }
.up-lab .tg { font-size: 11px; font-weight: 800; padding: 3px 8px; border-radius: 999px; }
.up-lab .tg.done { background: #eef3ff; color: #2f5bd8; }
.up-lab .tg.need { background: #f3f4f6; color: #6b7280; }

/* 업로드가 끝난 문서: 파일 카드 + 파란 완료 막대 */
.up-file { border: 1px solid #e5e7eb; border-radius: 14px; background: #fff; padding: 18px; margin-bottom: 10px; }
.up-file .row { display: flex; align-items: center; gap: 12px; }
.up-file .fi { position: relative; width: 42px; height: 42px; border-radius: 10px; background: #eef3ff; color: #3b6def;
    display: flex; align-items: center; justify-content: center; font-size: 21px; flex-shrink: 0; }
.up-file .fi .bd { position: absolute; right: -5px; bottom: -5px; width: 18px; height: 18px; border-radius: 50%;
    background: #3b6def; color: #fff; border: 2px solid #fff; display: flex; align-items: center; justify-content: center;
    font-size: 9px; }
.up-file b { display: block; font-size: 14.5px; color: #111827; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.up-file small { font-size: 12px; color: #9ca3af; }
.up-file .prog { height: 4px; border-radius: 4px; background: #3b6def; margin: 18px 0 10px; }
.up-file .ok { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap;
    font-size: 13px; font-weight: 700; color: #2f5bd8; }
.up-file .ok span { font-weight: 500; color: #6b7280; font-size: 12px; }

.up-hint { margin: 8px 0 0; font-size: 12px; color: #9ca3af; display: flex; gap: 5px; align-items: center; }

[data-testid="stFileUploader"] label { display: none !important; }
[data-testid="stFileUploaderDropzone"] {
    background: #fafbfd !important; border: 1.5px dashed #d6dbe5 !important; border-radius: 14px !important;
    min-height: 150px !important; display: flex !important; flex-direction: column !important;
    align-items: center !important; justify-content: center !important; text-align: center !important;
    padding: 18px 16px !important; gap: 10px !important;
}
/* 업로드 아이콘 칸 */
[data-testid="stFileUploaderDropzone"]::before {
    content: ""; width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
    background: #eef3ff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 256 256'%3E%3Cpath fill='none' stroke='%233b6def' stroke-linecap='round' stroke-linejoin='round' stroke-width='20' d='M128 144V32M80 80l48-48 48 48M216 144v64a8 8 0 0 1-8 8H48a8 8 0 0 1-8-8v-64'/%3E%3C/svg%3E") center / 22px no-repeat;
}
[data-testid="stFileUploaderDropzone"] > div { align-items: center !important; text-align: center !important; }
[data-testid="stFileUploaderDropzone"] button { border-radius: 9px !important; font-weight: 700 !important; }
[data-testid="stFileUploaderDropzone"] button p { white-space: nowrap !important; }
/* 업로드가 끝난 칸은 위 파일 카드가 이름을 보여 주므로, 파일 칩을 숨기고 '바꾸기'용 작은 칸만 남긴다. */
[class*="st-key-up_zone_done_"] [data-testid="stFileUploaderDropzone"] { min-height: 0 !important;
    padding: 10px 16px !important; flex-direction: row !important; gap: 10px !important; }
[class*="st-key-up_zone_done_"] [data-testid="stFileUploaderDropzone"]::before { width: 32px; height: 32px;
    border-radius: 9px; background-size: 17px; }
[class*="st-key-up_zone_done_"] [data-testid="stFileUploaderDropzone"]::after { content: "다른 파일로 바꾸기";
    order: 1; font-size: 13px; font-weight: 700; color: #4b5563; }
[class*="st-key-up_zone_done_"] [data-testid="stFileUploaderDropzone"] > * { order: 2; }
[class*="st-key-up_zone_done_"] [data-testid="stFileChips"],
[class*="st-key-up_zone_done_"] .up-limit { display: none !important; }
[class*="st-key-up_zone_done_"] [data-testid="stFileUploaderDropzone"] > div { flex-direction: row !important; }

.st-key-up_docs_card [data-testid="stHorizontalBlock"] { gap: 20px !important; }
.st-key-up_voice_row { background: #fafbfd !important; border: 1px solid #eef0f4 !important; border-radius: 14px !important;
    padding: 16px 20px !important; }
.st-key-up_voice_row [data-testid="stHorizontalBlock"] { align-items: center !important; flex-wrap: nowrap !important; }
.st-key-up_voice_row [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }
.up-opt { display: flex; align-items: center; gap: 14px; }
.up-opt .ic { width: 40px; height: 40px; border-radius: 10px; background: #eef3ff; color: #3b6def; display: flex;
    align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.up-opt b { display: block; font-size: 14.5px; color: #111827; }
.up-opt small { font-size: 12.5px; color: #6b7280; }
.st-key-voice_guide_default_checkbox label { margin: 0 !important; }
.st-key-voice_guide_default_checkbox label > span:first-child { transform: scale(1.25); }

.st-key-btn_back button { background: transparent !important; border: none !important; padding: 8px 0 !important;
    min-height: 0 !important; box-shadow: none !important; }
.st-key-btn_back button p { font-size: 14px !important; font-weight: 700 !important; color: #4b5563 !important; }
.st-key-btn_back button:hover p { color: #111827 !important; }
</style>
""", unsafe_allow_html=True)

# ── 단계 표시 · 타이틀 ────────────────────────────────────────────────────
st.markdown(
    steps_html(2)
    + '<div class="su-head"><div class="t">직무 기술서와 이력서를 업로드해 주세요</div>'
    '<div class="sub">업로드한 문서를 바탕으로 AI가 맞춤형 면접 질문을 준비해요</div></div>',
    unsafe_allow_html=True,
)

if not get("interviewer_style"):
    st.markdown(
        '<div class="up-warn"><i class="ph-bold ph-warning-circle"></i>'
        '아직 면접관 스타일을 선택하지 않았어요.'
        '<a href="/%EB%A9%B4%EC%A0%91_%ED%99%98%EA%B2%BD%EC%84%A4%EC%A0%95" target="_self">'
        '이전 단계로 돌아가기 →</a></div>',
        unsafe_allow_html=True,
    )


def read_file_text(uploaded_file) -> str:
    """업로드된 파일에서 텍스트 추출"""
    name = uploaded_file.name.lower()
    if name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(uploaded_file) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
        except ImportError:
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(uploaded_file)
                return "\n".join(p.extract_text() or "" for p in reader.pages)
            except ImportError:
                return f"[PDF 파싱 불가. pdfplumber 또는 PyPDF2 설치 필요]\n파일명: {uploaded_file.name}"
    if name.endswith(".docx"):
        try:
            import docx
            from io import BytesIO
            doc = docx.Document(BytesIO(uploaded_file.read()))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            return f"[DOCX 파싱 불가. python-docx 설치 필요]\n파일명: {uploaded_file.name}"
    if name.endswith(".hwpx"):
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            from io import BytesIO
            texts = []
            with zipfile.ZipFile(BytesIO(uploaded_file.read())) as z:
                section_files = sorted(
                    n for n in z.namelist()
                    if n.startswith("Contents/section") and n.endswith(".xml")
                )
                for section in section_files:
                    root = ET.fromstring(z.read(section))
                    for el in root.iter():
                        tag = el.tag.rsplit("}", 1)[-1]  # 네임스페이스 제거
                        if tag == "t" and el.text:
                            texts.append(el.text)
            return "\n".join(texts)
        except Exception:
            return f"[HWPX 파싱 불가]\n파일명: {uploaded_file.name}"
    return uploaded_file.read().decode("utf-8", errors="ignore")


def _upload_error_message(e: Exception) -> str:
    if isinstance(e, requests.exceptions.ConnectionError):
        return "서버에 연결할 수 없습니다. 백엔드 서버가 켜져 있는지 확인해주세요."
    if isinstance(e, requests.exceptions.Timeout):
        return "업로드 요청이 시간 초과되었습니다. 다시 시도해주세요."
    if isinstance(e, requests.exceptions.HTTPError):
        return api.error_detail(e, "업로드에 실패했습니다.")
    return f"업로드 중 알 수 없는 오류가 발생했습니다: {e}"


def _reset_interview_for_new_documents():
    """서류를 바꾸면 그 서류로 새 면접을 해야 하므로, 진행 중이던 면접 세션을 비운다."""
    if get("session_id"):
        st.session_state["_session_id_clear_pending"] = True
    state_set("session_id", None)
    state_set("first_question", None)
    state_set("interview_done", False)
    st.session_state.pop("iv_messages", None)


def _handle_document(kind: str, uploaded_file, upload_fn):
    id_key, name_key, sig_key = f"{kind}_id", f"{kind}_file_name", f"_{kind}_file_sig"
    if uploaded_file:
        sig = (uploaded_file.name, uploaded_file.size)
        if get(id_key) and st.session_state.get(sig_key) == sig:
            pass
        else:
            state_set(f"{kind}_text", read_file_text(uploaded_file))
            try:
                new_id = upload_fn(uploaded_file.getvalue(), uploaded_file.name)
            except api.SessionExpiredError:
                mark_session_expired()
                return
            except Exception as e:
                state_set(id_key, 0)
                st.session_state.pop(sig_key, None)
                state_set(name_key, "")
                show_error(_upload_error_message(e))
                return
            if get(id_key) and get(id_key) != new_id:
                _reset_interview_for_new_documents()
            state_set(id_key, new_id)
            state_set(name_key, uploaded_file.name)
            st.session_state[sig_key] = sig


def _size_text(n) -> str:
    if not n:
        return ""
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f}MB"
    return f"{n / 1024:.1f}KB" if n < 10 * 1024 else f"{round(n / 1024)}KB"


def _done_card(kind: str) -> str:
    """업로드가 끝난 문서 카드. 이름은 사용자가 올린 파일명이라 escape 한다."""
    name = get(f"{kind}_file_name") or ""
    ext = name.rsplit(".", 1)[-1].upper() if "." in name else ""
    sig = st.session_state.get(f"_{kind}_file_sig")
    meta = " · ".join(x for x in (ext, _size_text(sig[1] if sig else None)) if x)
    icon = "ph-file-pdf" if ext == "PDF" else "ph-file-doc" if ext == "DOCX" else "ph-file-text"
    return (
        f'<div class="up-file"><div class="row"><span class="fi"><i class="ph-fill {icon}"></i>'
        f'<span class="bd"><i class="ph-bold ph-check"></i></span></span>'
        f'<div style="min-width:0"><b>{htmlmod.escape(name)}</b><small>{htmlmod.escape(meta)}</small></div></div>'
        f'<div class="prog"></div><div class="ok">업로드 완료<span>다른 파일로 바꾸려면 아래 칸에 새로 올려 주세요</span></div></div>'
    )


_HWP_HINT = ('<div class="up-hint"><i class="ph-bold ph-lightbulb" style="flex-shrink:0;"></i>'
             '한글 파일은 HWPX만 지원돼요. 구버전 HWP는 PDF로 저장한 후 업로드해주세요</div>')


def _document_column(kind: str, label: str, upload_fn, help_text: str):
    """라벨(완료/필요) · 완료 카드 · 업로드 칸 · 안내 순서로 그린다.
    업로드 처리는 업로드 칸을 만든 뒤에 돌지만, 라벨과 완료 카드는 그 결과를 보여 줘야 해서
    자리(st.empty)를 먼저 잡아 두고 처리 후에 채운다."""
    label_slot = st.empty()
    card_slot = st.empty()
    # 방금 파일을 고른 경우(위젯 값이 이미 있음)도 '끝난 칸'으로 그려, 업로드 직후 큰 칸이 한 번 깜빡이지 않게 한다.
    done_before = bool(get(f"{kind}_id") and get(f"{kind}_file_name")) or bool(st.session_state.get(f"{kind}_upload"))
    with st.container(key=f"up_zone_{'done_' if done_before else ''}{kind}"):
        uploaded = st.file_uploader(kind, type=["pdf", "docx", "hwpx"], key=f"{kind}_upload", help=help_text)
    st.markdown(_HWP_HINT, unsafe_allow_html=True)
    _handle_document(kind, uploaded, upload_fn)

    done = bool(get(f"{kind}_id") and get(f"{kind}_file_name"))
    tag = '<span class="tg done">완료</span>' if done else '<span class="tg need">필요</span>'
    label_slot.markdown(f'<div class="up-lab">{label}{tag}</div>', unsafe_allow_html=True)
    if done:
        card_slot.markdown(_done_card(kind), unsafe_allow_html=True)


# ── 01 문서 업로드 ───────────────────────────────────────────────────────
with st.container(key="up_docs_card"):
    st.markdown(
        '<div class="su-sh"><span class="n">01</span>문서 업로드</div>'
        '<div class="su-sd">두 문서 모두 있어야 면접을 시작할 수 있어요</div>',
        unsafe_allow_html=True,
    )
    up1, up2 = st.columns(2, gap="medium")
    with up1:
        _document_column("jd", "직무 기술서 (JD)", api.upload_jd, "PDF, DOCX, HWPX 지원 (최대 20MB)")
    with up2:
        _document_column("resume", "이력서", api.upload_resume, "PDF, DOCX, HWPX 파일 지원 (최대 20MB)")

components.html("""
<script>
(function () {
    function findLimitEl(dz) {
        var els = dz.querySelectorAll('*');
        for (var i = 0; i < els.length; i++) {
            var el = els[i];
            if (el.textContent.indexOf('MB') !== -1 && el.children.length === 0)
                return el;
        }
        return null;
    }

    function moveUploadBtns() {
        var doc = window.parent.document;
        var dropzones = doc.querySelectorAll('[data-testid="stFileUploaderDropzone"]');
        if (!dropzones.length) { setTimeout(moveUploadBtns, 200); return; }
        var pending = 0;
        dropzones.forEach(function(dz) {
            if (dz.dataset.btnMoved) return;
            var btn      = dz.querySelector('button');
            var limitEl  = findLimitEl(dz);
            if (!btn || !limitEl) { pending++; return; }
            limitEl.classList.add('up-limit');
            var wrap = doc.createElement('div');
            wrap.style.cssText = 'display:flex;align-items:center;justify-content:center;gap:10px;margin-top:6px;';
            limitEl.parentNode.insertBefore(wrap, limitEl);
            wrap.appendChild(limitEl);
            wrap.appendChild(btn);
            dz.dataset.btnMoved = '1';
        });
        if (pending) setTimeout(moveUploadBtns, 200);
    }

    moveUploadBtns();

    new MutationObserver(function(mutations) {
        var needsRun = false;
        mutations.forEach(function(m) {
            if (m.addedNodes.length) needsRun = true;
        });
        if (needsRun) moveUploadBtns();
    }).observe(window.parent.document.body, { childList: true, subtree: true });
}());
</script>
""", height=0)

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)


# ── 02 면접 옵션 (음성 안내 기본값) ──────────────────────────────────────
with st.container(key="up_option_card"):
    st.markdown(
        '<div class="su-sh"><span class="n">02</span>면접 옵션</div>'
        '<div class="su-sd">면접 중에도 바꿀 수 있어요</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="up_voice_row"):
        _opt_text, _opt_box = st.columns([1, 0.08], vertical_alignment="center")
        with _opt_text:
            st.markdown(
                '<div class="up-opt"><span class="ic"><i class="ph-bold ph-speaker-high"></i></span>'
                '<div><b>면접 중 음성 안내 기본으로 켜기</b><small>면접관 질문을 소리로 읽어 줘요</small></div></div>',
                unsafe_allow_html=True,
            )
        with _opt_box:
            voice_guide_default = st.checkbox(
                "면접 중 음성 안내 기본으로 켜기",
                value=get("voice_guide_default") if get("voice_guide_default") is not None else True,
                key="voice_guide_default_checkbox",
                label_visibility="collapsed",
            )
    state_set("voice_guide_default", voice_guide_default)

# ── 이전 단계 · 시작 버튼 ────────────────────────────────────────────────
with st.container(key="next_area"):
    _back_col, _start_col = st.columns([3, 1], vertical_alignment="center")
    with _back_col:
        if st.button("← 이전 단계", key="btn_back"):
            st.switch_page("pages/03_면접_환경설정.py")
    with _start_col:
        if st.button("면접 시작하기 →", type="primary", key="btn_start"):
            if not get("user_name"):
                show_error("성함을 입력해주세요. 이전 단계로 돌아가주세요.")
            elif not get("jd_id"):
                show_error("직무 기술서(JD)를 업로드해주세요.")
            elif not get("resume_id"):
                show_error("이력서를 업로드해주세요.")
            else:
                st.switch_page("pages/035_웹캠_허용.py")

render_session_expired_banner()
