"""
마이페이지 라우터

엔드포인트:
    GET /mypage/videos             - 보관 중인 면접 영상 목록
    GET /mypage/videos/{id}/file   - 영상 파일 (재생용)

면접 기록 목록(GET /interview/sessions)은 아직 없어서 마이페이지의 점수 표는 목업이다.
그건 별도 작업으로 붙인다.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.deps import current_user
from backend.database import get_db
from backend.models.models import User
from backend.schemas.video import MyPageVideoListResponse
from backend.services.video_service import VideoService

router = APIRouter(prefix="/mypage", tags=["MyPage"])


@router.get("/videos", response_model=MyPageVideoListResponse)
def list_videos(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """내 면접 영상 목록 (최신순, 보관 개수만큼)"""
    service = VideoService(db, user)
    return service.my_videos()


@router.get("/videos/{video_id}/file")
def get_video_file(
    video_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """
    영상 파일 응답.

    인증이 걸려 있어 <video src="..."> 로 바로 물릴 수는 없다. 프론트는 토큰을 실어
    받아온 뒤 blob URL 로 만들어 재생해야 한다.
    """
    service = VideoService(db, user)
    return service.file_response(video_id)
