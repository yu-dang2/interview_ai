"""
영상 분석 관련 Pydantic 스키마

분석은 업로드 응답에서 끝나지 않는다. 업로드는 202 로 접수만 하고, 프론트가
/video-metrics 를 폴링해 status 가 analyzing → done(또는 failed) 로 바뀌는 것을 본다.

필드 이름과 status 값은 video/README.md 의 "전체 인터페이스" 절에 맞춘다.
지원님 클라이언트가 그 문서를 보고 붙이므로 백엔드가 문서를 따라간다.

시선 지표는 면접 점수(5개 역량)에 반영하지 않는 보조 코칭 값이라
ResultResponse 와 완전히 분리해 둔다.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# "analyzing" 은 README 표기다. 내부적으로 "처리 중"을 뜻한다.
VideoStatus = Literal["analyzing", "done", "failed"]


class GazeFeedback(BaseModel):
    """video_assist.gaze_feedback() 의 반환 형태 그대로."""

    level: str      # 좋음 / 보통 / 개선 필요
    message: str
    gauge: float    # 정면 응시 비율(%)


class VideoUploadResponse(BaseModel):
    video_id: int
    session_id: str
    status: VideoStatus


class VideoMetricsResponse(BaseModel):
    video_id: int
    session_id: str
    status: VideoStatus
    created_at: datetime

    # 영상 재생용 경로. 인증이 필요하므로 <video src> 에 바로 넣을 수 없다.
    video_url: str

    # status 가 done 일 때만 채워진다.
    gaze_percent: float | None = None
    gaze: GazeFeedback | None = None
    frames_analyzed: int | None = None

    # status 가 failed 일 때만 채워진다.
    error: str | None = None

    # 영상 분석 경로에서는 항상 None 이다. 발화 속도는 녹음 시간이 있어야 하는데
    # 영상에서는 사용자가 언제부터 말했는지 알 수 없다.
    # 발화 속도는 POST /voice/transcribe 응답으로 나간다 (프론트가 duration 전달).
    speech_cpm: float | None = None
    speech: GazeFeedback | None = None


class MyPageVideoItem(BaseModel):
    """필드 이름은 video/README.md 의 마이페이지 목록 계약을 따른다."""

    video_id: int
    # README 표기. 값은 면접 세션 UUID 다.
    interview_id: str
    date: datetime
    status: VideoStatus
    persona: str | None = None
    gaze_percent: float | None = None
    # 영상 재생용 경로. 배포 시 S3 presigned URL 로 바뀔 수 있다.
    video_url: str
    # 아직 생성하지 않는다. 만들려면 업로드 시 첫 프레임을 뽑아 따로 저장해야 한다.
    thumbnail: str | None = None


class MyPageVideoListResponse(BaseModel):
    # 사용자당 VIDEO_MAX_PER_USER 개까지만 보관하므로 페이지네이션은 두지 않았다.
    total: int
    videos: list[MyPageVideoItem]
