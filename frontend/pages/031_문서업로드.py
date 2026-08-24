import requests
import streamlit as st
import streamlit.components.v1 as components
from components.sidebar import render_sidebar
from utils.state import init_session, get, set as state_set, mark_session_expired, render_session_expired_banner
from utils.ui import show_error
from utils import api

st.set_page_config(
    page_title="문서 업로드 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()
render_sidebar(active="면접 시작")

# ── CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMainBlockContainer"] { padding: 40px 48px 60px !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stHorizontalBlock"] { gap: 0; }

[data-testid="stMainBlockContainer"] {
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
}

[data-testid="stFileUploader"] label { display:none !important; }
[data-testid="stFileUploaderDropzone"] {
    background:#f7f8fc !important;
    border:1.5px dashed #c7d2e8 !important;
    border-radius:10px !important; min-height:140px !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    padding-top: 10px !important;
    padding-bottom: 30px !important;
}
[data-testid="stFileUploaderDropzone"] > div {
    align-items: center !important;
    text-align: center !important;
}

[data-testid="stBaseButton-primary"] {
    font-size: 17px !important;
    padding: 12px 50px !important;
    white-space: nowrap !important;
    width: auto !important;
}
.st-key-start_area {
    display: grid !important;
    grid-template-columns: max-content !important;
    justify-content: center !important;
    row-gap: 8px !important;
    margin-top: var(--space-8) !important;
}
/* 업로드 완료 표시 ↔ 음성안내 체크박스 ↔ 시작 버튼 사이 간격 —
   빈 spacer div는 이 페이지에서 높이가 0으로 collapse되는 경우가 있어
   실제 위젯 컨테이너에 margin을 직접 건다. */
.st-key-voice_guide_default_checkbox { margin-top: var(--space-5) !important; }
.st-key-start_area [data-testid="stAlert"] {
    justify-self: stretch !important;
    box-sizing: border-box !important;
}

[data-testid="stFileUploaderDropzone"] button p {
    white-space: nowrap !important;
}

.upload-done {
    display: flex;
    align-items: center;
    gap: 6px;
    background: #ecfdf3;
    border: 1px solid #86e0ab;
    border-radius: 8px;
    padding: 8px 12px;
    margin-top: 8px;
    font-size: 13px;
    font-weight: 600;
    color: #087443;
}
</style>
""", unsafe_allow_html=True)

# ── 스텝 인디케이터 ────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;justify-content:center;margin-bottom:32px;">
  <div style="width:10px;height:10px;border-radius:50%;background:#93b4f5;flex-shrink:0;"></div>
  <span style="font-size:11px;color:#93b4f5;margin:0 6px 0 4px;">기본 정보</span>
  <div style="width:52px;height:1px;background:#93b4f5;"></div>
  <div style="width:10px;height:10px;border-radius:50%;background:#3b6def;flex-shrink:0;margin-left:4px;"></div>
  <span style="font-size:11px;font-weight:600;color:#3b6def;margin-left:4px;">문서 업로드</span>
</div>
""", unsafe_allow_html=True)

# ── 타이틀 ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:60px;">
  <div style="font-size:24px;font-weight:700;color:#1f1f1f;margin:0 0 6px;">
    직무 기술서와 이력서를 업로드해주세요
  </div>
  <p style="font-size:14px;color:#9ca3af;margin:0;">
    업로드한 문서를 바탕으로 AI가 맞춤형 면접 질문을 준비합니다.
  </p>
</div>
""", unsafe_allow_html=True)

if not get("interviewer_style"):
    st.markdown(
        '<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;'
        'padding:10px 14px;margin-bottom:28px;font-size:13px;color:#92400e;">'
        '아직 면접관 스타일을 선택하지 않았어요. '
        '<a href="/%EB%A9%B4%EC%A0%91_%ED%99%98%EA%B2%BD%EC%84%A4%EC%A0%95" target="_self" '
        'style="color:#3b6def;font-weight:600;">이전 단계로 돌아가기</a>'
        '</div>',
        unsafe_allow_html=True,
    )

# ── 문서 업로드 ─────────────────────────────────────────────────────────
st.markdown('<p style="font-size:14px;font-weight:600;color:#1f1f1f;margin:0 0 20px;">문서 업로드</p>',
            unsafe_allow_html=True)

up1, _gap, up2 = st.columns([15, 1, 15])


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
                return f"[PDF 파싱 불가 — pdfplumber 또는 PyPDF2 설치 필요]\n파일명: {uploaded_file.name}"
    if name.endswith(".docx"):
        try:
            import docx
            from io import BytesIO
            doc = docx.Document(BytesIO(uploaded_file.read()))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            return f"[DOCX 파싱 불가 — python-docx 설치 필요]\n파일명: {uploaded_file.name}"
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


with up1:
    st.markdown('<p style="font-size:13px;font-weight:600;color:#374151;margin:0 0 20px;">직무 기술서 (JD)</p>',
                unsafe_allow_html=True)
    jd_file = st.file_uploader("jd", type=["pdf","docx","hwpx"], key="jd_upload",
                                help="PDF, DOCX, HWPX 지원 (최대 20MB)")
    st.caption("💡 한글 파일은 HWPX만 지원돼요 — 구버전 HWP는 PDF로 저장한 후 업로드해주세요")
    if jd_file:
        state_set("jd_text", read_file_text(jd_file))
        try:
            state_set("jd_id", api.upload_jd(jd_file.getvalue(), jd_file.name))
            st.markdown(f'<div class="upload-done">✅ {jd_file.name} 업로드 완료</div>', unsafe_allow_html=True)
        except api.SessionExpiredError:
            mark_session_expired()
        except Exception as e:
            state_set("jd_id", 0)
            show_error(_upload_error_message(e))

with up2:
    st.markdown('<p style="font-size:13px;font-weight:600;color:#374151;margin:0 0 20px;">이력서</p>',
                unsafe_allow_html=True)
    resume_file = st.file_uploader("resume", type=["pdf","docx","hwpx"], key="resume_upload",
                                    help="PDF, DOCX, HWPX 파일 지원 (최대 20MB)")
    st.caption("💡 한글 파일은 HWPX만 지원돼요 — 구버전 HWP는 PDF로 저장한 후 업로드해주세요")
    if resume_file:
        state_set("resume_text", read_file_text(resume_file))
        try:
            state_set("resume_id", api.upload_resume(resume_file.getvalue(), resume_file.name))
            st.markdown(f'<div class="upload-done">✅ {resume_file.name} 업로드 완료</div>', unsafe_allow_html=True)
        except api.SessionExpiredError:
            mark_session_expired()
        except Exception as e:
            state_set("resume_id", 0)
            show_error(_upload_error_message(e))

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

# ── 음성 안내 기본값 ────────────────────────────────────────────────────
voice_guide_default = st.checkbox(
    "면접 중 음성 안내 기본으로 켜기",
    value=get("voice_guide_default") if get("voice_guide_default") is not None else True,
    key="voice_guide_default_checkbox",
)
state_set("voice_guide_default", voice_guide_default)

st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

# ── 시작 버튼 ────────────────────────────────────────────────────────────
_, center, _ = st.columns([4.3, 2, 4.3])
with center:
    with st.container(key="start_area"):
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
