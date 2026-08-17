import requests
import streamlit as st
import streamlit.components.v1 as components
import base64
from utils.paths import resource
from components.sidebar import render_sidebar
from utils.state import init_session, get, set as state_set, mark_session_expired, is_session_expired, render_session_expired_inline
from utils import api

st.set_page_config(
    page_title="면접 환경설정 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()

if get("session_id"):
    st.session_state["_session_id_clear_pending"] = True
    state_set("session_id", None)
    state_set("first_question", None)
    state_set("result", None)
    state_set("interview_done", False)
    if "iv_messages" in st.session_state:
        del st.session_state["iv_messages"]

render_sidebar(active="면접 시작")


def img_b64(path: str) -> str:
    return base64.b64encode(resource(path).read_bytes()).decode()


PERSONAS = [
    {"key": "기술 리드",   "desc": "날카롭고 집요한 기술 검증", "img": img_b64("assets/images/기술리드.png")},
    {"key": "인사 담당자", "desc": "공감 중심 인성 면접",        "img": img_b64("assets/images/인사 담당자.png")},
    {"key": "임원 면접관", "desc": "전략적 비즈니스 역량 검증",  "img": img_b64("assets/images/임원 면접관.png")},
]

selected = get("interviewer_style") or "기술 리드"

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

[data-testid="stTextInput"] label p {
    font-size:14px !important; font-weight:600 !important; color:#1f1f1f !important;
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
}
.st-key-start_area [data-testid="stAlert"] {
    justify-self: stretch !important;
    box-sizing: border-box !important;
}

[data-testid="stFileUploaderDropzone"] button p {
    white-space: nowrap !important;
}

[data-persona-card]:hover {
    box-shadow: 0 4px 16px rgba(59,109,239,0.15) !important;
    transform: translateY(-1px) !important;
}

@media (max-width: 900px) {
    [data-persona-card] {
        flex-direction: column !important;
        text-align: center !important;
        padding: 20px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ── 타이틀 ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:60px;">
  <div style="font-size:24px;font-weight:700;color:#1f1f1f;margin:0 0 6px;">
    면접 환경을 설정해주세요
  </div>
  <p style="font-size:14px;color:#9ca3af;margin:0;">
    이력서와 채용공고를 업로드하고 AI 면접관을 설정하세요.
  </p>
</div>
""", unsafe_allow_html=True)

# ── 성함 ────────────────────────────────────────────────────────────────

if st.session_state.get("setup_name"):
    state_set("user_name", st.session_state["setup_name"])

name_col, _ = st.columns([1, 2])
with name_col:
    name = st.text_input("성함", placeholder="홍길동",
                         value=get("user_name") or "", key="setup_name")
if name:
    state_set("user_name", name)

st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)

# ── 면접관 스타일 ────────────────────────────────────────────────────────
st.markdown('<p style="font-size:14px;font-weight:600;color:#1f1f1f;margin:0 0 20px;">면접관 스타일 선택</p>',
            unsafe_allow_html=True)

# 페르소나 카드 
cards_html = '<div style="display:flex;gap:28px;">'
for p in PERSONAS:
    is_active  = selected == p["key"]
    border     = "1.5px solid #3b6def" if is_active else "1px solid #e5e7eb"
    bg         = "#eff6ff"             if is_active else "white"
    name_color = "#3b6def"             if is_active else "#1f1f1f"
    cards_html += f"""
    <div data-persona-card="{p['key']}"
         style="flex:1;min-width:0;border:{border};background:{bg};border-radius:12px;
                padding:20px;display:flex;align-items:center;justify-content:center;gap:24px;
                cursor:pointer;min-height:80px;box-sizing:content-box;
                transition:transform 0.15s,box-shadow 0.15s;">
      <img src="data:image/png;base64,{p['img']}"
           style="width:72px;height:72px;border-radius:50%;
                  object-fit:cover;flex-shrink:0;">
      <div style="min-width:0;">
        <div style="font-size:15px;font-weight:700;color:{name_color};
                    margin-bottom:4px;word-break:keep-all;">{p['key']}</div>
        <div style="font-size:12px;color:#9ca3af;word-break:keep-all;">{p['desc']}</div>
      </div>
    </div>"""
cards_html += '</div>'
st.markdown(cards_html, unsafe_allow_html=True)

st.markdown(
    "<style>.st-key-persona_hidden_row { display:none !important; }</style>",
    unsafe_allow_html=True,
)
with st.container(key="persona_hidden_row"):
    btn_cols = st.columns(3)
    for i, p in enumerate(PERSONAS):
        with btn_cols[i]:
            if st.button(p["key"], key=f"ps_{p['key']}", use_container_width=True):
                state_set("interviewer_style", p["key"])
                st.rerun()

components.html("""
<script>
(function () {
    function attach() {
        var doc = window.parent.document;
        var cards = doc.querySelectorAll('[data-persona-card]');
        if (!cards.length) { setTimeout(attach, 300); return; }

        cards.forEach(function (card) {
            var key = card.getAttribute('data-persona-card');
            card.onclick = function () {
                var btns = doc.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    if (btns[i].innerText.trim() === key) {
                        btns[i].click();
                        return;
                    }
                }
            };
        });
    }

    attach();

    setTimeout(function () {
        new MutationObserver(function () { attach(); })
            .observe(window.parent.document.body, { childList: true, subtree: true });
    }, 800);
}());
</script>
""", height=0)

st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)

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
        status = e.response.status_code if e.response is not None else "?"
        return f"업로드에 실패했습니다. (서버 오류: {status})"
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
            st.caption(f"✅ {jd_file.name} 업로드 완료")
        except api.SessionExpiredError:
            mark_session_expired()
        except Exception as e:
            state_set("jd_id", 0)
            st.error(_upload_error_message(e))

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
            st.caption(f"✅ {resume_file.name} 업로드 완료")
        except api.SessionExpiredError:
            mark_session_expired()
        except Exception as e:
            state_set("resume_id", 0)
            st.error(_upload_error_message(e))

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
    if is_session_expired():
        render_session_expired_inline()
    else:
        with st.container(key="start_area"):
            if st.button("면접 시작하기 →", type="primary", key="btn_start"):
                if not (get("user_name") or name):
                    st.error("성함을 입력해주세요.")
                elif not get("jd_id"):
                    st.error("직무 기술서(JD)를 업로드해주세요.")
                elif not get("resume_id"):
                    st.error("이력서를 업로드해주세요.")
                else:
                    state_set("interviewer_style", selected)
                    st.switch_page("pages/035_웹캠_허용.py")
