"""
이력서 라우터

모든 엔드포인트가 인증을 요구하며, 이력서는 등록한 사용자에게 귀속된다.
남의 이력서는 조회되지 않는다.

엔드포인트:
    POST /resume                           - 이력서 텍스트 직접 등록
    POST /resume/upload                    - 이력서 파일 업로드 (.pdf / .docx / .hwpx)
    GET  /resume/                          - 내 이력서 목록 조회
    GET  /resume/{resume_id}               - 특정 이력서 조회
    GET  /resume/{resume_id}/optimize      - 이력서 최적화 제안 조회 (미구현)
    POST /resume/{resume_id}/apply         - 최적화 제안 적용 (미구현)
    GET  /resume/{resume_id}/download      - 최적화된 이력서 다운로드 (미구현)
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.core.deps import current_user
from backend.database import get_db
from backend.models.models import Resume, User
from backend.routers.uploads import read_document_upload
from backend.schemas.resume import ResumeCreateRequest, ResumeListItem, ResumeResponse

router = APIRouter(prefix="/resume", tags=["Resume"])


def _create(db: Session, content: str, user: User) -> Resume:
    resume = Resume(content=content, users_user_id=user.user_id)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def _get_owned(db: Session, resume_id: int, user: User) -> Resume:
    """내 이력서만 반환. 없거나 남의 것이면 404.

    남의 이력서에 403 을 주면 그 id 가 존재한다는 사실이 새어나가므로 404 로 묶는다.
    """
    resume = db.get(Resume, resume_id)
    if resume is None or resume.users_user_id != user.user_id:
        raise HTTPException(status_code=404, detail=f"이력서를 찾을 수 없습니다: {resume_id}")
    return resume


@router.post("", response_model=ResumeResponse, status_code=201)
def create_resume(
    req: ResumeCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """이력서 텍스트를 직접 등록한다."""
    return _create(db, req.content, user)


@router.post("/upload", response_model=ResumeResponse, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """이력서 파일(.pdf / .docx / .hwpx)을 업로드한다."""
    content = await read_document_upload(file)
    return _create(db, content, user)


@router.get("/", response_model=list[ResumeListItem])
def get_resume_list(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """내 이력서 목록을 조회한다."""
    return (
        db.query(Resume)
        .filter(Resume.users_user_id == user.user_id)
        .order_by(Resume.resume_id.desc())
        .all()
    )


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """특정 이력서를 조회한다."""
    return _get_owned(db, resume_id, user)


# ── 이력서 최적화 (RESUME_OPTIMIZER_SYSTEM_PROMPT 연동 예정, 현재 범위 밖) ──

@router.get("/{resume_id}/optimize")
def optimize_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """이력서 최적화 제안 조회"""
    raise HTTPException(status_code=501, detail="아직 구현되지 않은 기능입니다.")


@router.post("/{resume_id}/apply")
def apply_optimization(
    resume_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """최적화 제안 적용"""
    raise HTTPException(status_code=501, detail="아직 구현되지 않은 기능입니다.")


@router.get("/{resume_id}/download")
def download_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """최적화된 이력서 다운로드"""
    raise HTTPException(status_code=501, detail="아직 구현되지 않은 기능입니다.")
