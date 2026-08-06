"""
직무기술서 라우터

모든 엔드포인트가 인증을 요구하며, JD 는 등록한 사용자에게 귀속된다.
남의 JD 는 조회되지 않는다.

엔드포인트:
    POST /jd           - JD 텍스트 직접 등록
    POST /jd/upload    - JD 파일 업로드 (.pdf / .docx / .hwpx)
    GET  /jd/          - 내 JD 목록 조회
    GET  /jd/{jd_id}   - JD 조회
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.core.deps import current_user
from backend.database import get_db
from backend.models.models import JD, User
from backend.routers.uploads import read_document_upload
from backend.schemas.jd import JDCreateRequest, JDListItem, JDResponse

router = APIRouter(prefix="/jd", tags=["JD"])


def _create(db: Session, title: str, content: str, user: User) -> JD:
    jd = JD(title=title, content=content, users_user_id=user.user_id)
    db.add(jd)
    db.commit()
    db.refresh(jd)
    return jd


def _get_owned(db: Session, jd_id: int, user: User) -> JD:
    """내 JD 만 반환. 없거나 남의 것이면 404 (존재 여부를 흘리지 않는다)."""
    jd = db.get(JD, jd_id)
    if jd is None or jd.users_user_id != user.user_id:
        raise HTTPException(status_code=404, detail=f"JD를 찾을 수 없습니다: {jd_id}")
    return jd


@router.post("", response_model=JDResponse, status_code=201)
def create_jd(
    req: JDCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """JD 텍스트를 직접 등록한다."""
    return _create(db, req.title, req.content, user)


@router.post("/upload", response_model=JDResponse, status_code=201)
async def upload_jd(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """JD 파일(.pdf / .docx / .hwpx)을 업로드한다."""
    content = await read_document_upload(file)
    return _create(db, file.filename, content, user)


@router.get("/", response_model=list[JDListItem])
def list_jd(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """내 JD 목록을 조회한다."""
    return (
        db.query(JD)
        .filter(JD.users_user_id == user.user_id)
        .order_by(JD.jd_id.desc())
        .all()
    )


@router.get("/{jd_id}", response_model=JDResponse)
def get_jd(
    jd_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """JD를 조회한다."""
    return _get_owned(db, jd_id, user)
