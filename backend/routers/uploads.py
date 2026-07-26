"""
업로드 파일 → 텍스트 변환 공통 헬퍼 (JD / 이력서 라우터가 공유)

지원 포맷: .pdf(pypdf) / .docx(python-docx) / .hwpx(표준 zipfile+xml)
hwpx는 ZIP 컨테이너이고 본문이 Contents/section*.xml(OWPML)에 있어 외부
라이브러리 없이 파싱한다(서버에 한글 설치 불필요).
"""

import io
import zipfile
from xml.etree import ElementTree

from fastapi import HTTPException, UploadFile

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".hwpx")


def _extract_pdf(raw: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_docx(raw: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(raw))
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_hwpx(raw: bytes) -> str:
    """hwpx(ZIP+OWPML)에서 문단(p)별 텍스트(t)를 추출한다."""
    texts = []
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        sections = sorted(
            name
            for name in zf.namelist()
            if name.startswith("Contents/section") and name.endswith(".xml")
        )
        for name in sections:
            root = ElementTree.fromstring(zf.read(name))
            for para in root.iter():
                # 네임스페이스(hp:) 포함 태그이므로 로컬 이름으로 판별
                if not para.tag.endswith("}p"):
                    continue
                runs = [
                    node.text
                    for node in para.iter()
                    if node.tag.endswith("}t") and node.text
                ]
                if runs:
                    texts.append("".join(runs))
    return "\n".join(texts)


_EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".hwpx": _extract_hwpx,
}


async def read_document_upload(file: UploadFile) -> str:
    """업로드된 문서 파일(pdf/docx/hwpx)에서 텍스트를 추출한다."""
    filename = (file.filename or "").lower()
    ext = next((e for e in SUPPORTED_EXTENSIONS if filename.endswith(e)), None)
    if ext is None:
        raise HTTPException(
            status_code=415,
            detail=f"지원하지 않는 파일 형식입니다. {', '.join(SUPPORTED_EXTENSIONS)} 파일만 업로드할 수 있습니다.",
        )

    raw = await file.read()
    try:
        text = _EXTRACTORS[ext](raw)
    except HTTPException:
        raise
    except Exception:
        # 손상된 파일/잘못된 구조 등은 500이 아니라 415로 응답한다.
        raise HTTPException(
            status_code=415,
            detail="파일을 읽을 수 없습니다. 손상되었거나 올바르지 않은 형식입니다.",
        )

    if not text.strip():
        raise HTTPException(status_code=400, detail="파일에서 추출된 내용이 비어 있습니다.")

    return text
