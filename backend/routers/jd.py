"""
직무기술서 라우터

엔드포인트:
    POST /jd           - JD 텍스트 직접 등록
    POST /jd/upload    - JD 파일 업로드 (.pdf / .docx / .hwpx)
    GET  /jd/          - JD 목록 조회
    GET  /jd/{jd_id}   - JD 조회
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import JD
from backend.routers.uploads import read_document_upload
from backend.schemas.jd import JDCreateRequest, JDListItem, JDResponse

router = APIRouter(prefix="/jd", tags=["JD"])


def _create(db: Session, title: str, content: str) -> JD:
    jd = JD(title=title, content=content)
    db.add(jd)
    db.commit()
    db.refresh(jd)
    return jd


@router.post("", response_model=JDResponse, status_code=201)
def create_jd(req: JDCreateRequest, db: Session = Depends(get_db)):
    """JD 텍스트를 직접 등록한다."""
    return _create(db, req.title, req.content)


@router.post("/upload", response_model=JDResponse, status_code=201)
async def upload_jd(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """JD 파일(.pdf / .docx / .hwpx)을 업로드한다."""
    content = await read_document_upload(file)
    return _create(db, file.filename, content)


@router.get("/", response_model=list[JDListItem])
def list_jd(db: Session = Depends(get_db)):
    """JD 목록을 조회한다."""
    return db.query(JD).order_by(JD.jd_id.desc()).all()


@router.get("/{jd_id}", response_model=JDResponse)
def get_jd(jd_id: int, db: Session = Depends(get_db)):
    """JD를 조회한다."""
    jd = db.get(JD, jd_id)
    if jd is None:
        raise HTTPException(status_code=404, detail=f"JD를 찾을 수 없습니다: {jd_id}")
    return jd
