"""
마이페이지 라우터

엔드포인트:
    GET /mypage/videos             - 보관 중인 면접 영상 목록
    GET /mypage/videos/{id}/file   - 영상 파일 (재생용)

마이페이지 점수 표는 GET /interview/sessions 가 담당한다. 세션·결과·통계를 한 번에
내려주므로 여기서 다시 만들지 않는다. 이 라우터는 영상만 다룬다.
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
