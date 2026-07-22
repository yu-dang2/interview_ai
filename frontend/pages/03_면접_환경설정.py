import streamlit as st
import streamlit.components.v1 as components
import base64
from utils.paths import resource
from components.sidebar import render_sidebar
from utils.state import init_session, get, set as state_set
from utils import api

st.set_page_config(
    page_title="면접 환경설정 | intro",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session()

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

/* 성함 라벨 폰트 */
[data-testid="stTextInput"] label p {
    font-size:14px !important; font-weight:600 !important; color:#1f1f1f !important;
}

/* 파일 업로더 */
[data-testid="stFileUploader"] label { display:none !important; }
[data-testid="stFileUploaderDropzone"] {
    background:#f7f8fc !important;
    border:1.5px dashed #c7d2e8 !important;
    border-radius:10px !important; min-height:140px !important;
    padding-left: 24% !important;
}

/* 시작 버튼 */
[data-testid="stBaseButton-primary"] {
    font-size: 17px !important;
    padding: 12px 50px !important;
}


/* 카드 호버 */
[data-persona-card]:hover {
    box-shadow: 0 4px 16px rgba(59,109,239,0.15) !important;
    transform: translateY(-1px) !important;
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
# 버튼 클릭(rerun) 시 session_state에 이미 typed 값이 보존되므로 먼저 저장
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

# 페르소나 카드 — 하나의 flex 컨테이너로 gap 보장
cards_html = '<div style="display:flex;gap:28px;">'
for p in PERSONAS:
    is_active  = selected == p["key"]
    border     = "1.5px solid #3b6def" if is_active else "1px solid #e5e7eb"
    bg         = "#eff6ff"             if is_active else "white"
    name_color = "#3b6def"             if is_active else "#1f1f1f"
    cards_html += f"""
    <div data-persona-card="{p['key']}"
         style="flex:1;border:{border};background:{bg};border-radius:12px;
                padding:20px;display:flex;align-items:center;gap:16px;
                cursor:pointer;height:80px;box-sizing:content-box;
                transition:transform 0.15s,box-shadow 0.15s;">
      <img src="data:image/png;base64,{p['img']}"
           style="width:72px;height:72px;border-radius:50%;
                  object-fit:cover;flex-shrink:0;">
      <div>
        <div style="font-size:15px;font-weight:700;color:{name_color};
                    margin-bottom:4px;">{p['key']}</div>
        <div style="font-size:12px;color:#9ca3af;">{p['desc']}</div>
      </div>
    </div>"""
cards_html += '</div>'
st.markdown(cards_html, unsafe_allow_html=True)

# 히든 버튼 행 — JS가 전체 행을 숨기고 카드 클릭에 연결
btn_cols = st.columns(3)
for i, p in enumerate(PERSONAS):
    with btn_cols[i]:
        if st.button(p["key"], key=f"ps_{p['key']}", use_container_width=True):
            state_set("interviewer_style", p["key"])
            st.rerun()

# JS: 카드 클릭 → 해당 히든 버튼 click()
components.html("""
<script>
(function () {
    var PERSONA_KEYS = ['기술 리드', '인사 담당자', '임원 면접관'];

    function attach() {
        var doc = window.parent.document;
        var cards = doc.querySelectorAll('[data-persona-card]');
        if (!cards.length) { setTimeout(attach, 300); return; }

        // 히든 버튼 행 전체 숨기기
        var hiddenRow = null;
        doc.querySelectorAll('button').forEach(function (btn) {
            if (PERSONA_KEYS.indexOf(btn.innerText.trim()) !== -1 && !hiddenRow) {
                hiddenRow = btn.closest('[data-testid="stHorizontalBlock"]');
            }
        });
        if (hiddenRow) hiddenRow.style.display = 'none';

        // 카드 클릭 → 히든 버튼 click()
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
        except Exception:
            state_set("jd_id", 0)
        st.caption(f"✅ {jd_file.name} 업로드 완료")

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
        except Exception:
            state_set("resume_id", 0)
        st.caption(f"✅ {resume_file.name} 업로드 완료")

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

st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)

# ── 시작 버튼 ────────────────────────────────────────────────────────────
_, center, _ = st.columns([4.3, 2, 4.3])
with center:
    if st.button("면접 시작하기 →", type="primary",
                 use_container_width=True, key="btn_start"):
        if not (get("user_name") or name):
            st.error("성함을 입력해주세요.")
        else:
            state_set("interviewer_style", selected)
            st.switch_page("pages/035_웹캠_허용.py")
