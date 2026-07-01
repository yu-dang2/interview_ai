"""
직무기술서 라우터

엔드포인트:
    POST /jd/upload    - JD 파일 업로드
    GET  /jd/{jd_id}   - JD 조회
"""

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from backend.database import get_db

router = APIRouter(prefix="/jd", tags=["JD"])


@router.post("/upload")
async def upload_jd(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """JD 파일 업로드"""
    # TODO: JD 업로드 로직 구현
    pass


@router.get("/{jd_id}")
def get_jd(jd_id: int, db: Session = Depends(get_db)):
    """JD 조회"""
    # TODO: JD 조회 로직 구현
    pass