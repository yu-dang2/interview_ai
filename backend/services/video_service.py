"""
영상 분석 서비스

흐름:
    upload()        업로드 저장 → interview_videos 행 생성(status=processing) → 202 즉시 응답
    analyze()       백그라운드에서 video_assist.analyze_video() 실행 → status=done/failed
    metrics()       프론트가 폴링하는 조회
    my_videos()     마이페이지 영상 목록
    file_response() 영상 재생용 파일 응답

분석을 동기로 처리하지 않는 이유: 30분짜리 영상이면 프레임 수만 5만 장이라 요청 안에서
끝나지 않는다. 그래서 접수만 하고 폴링하게 한다.

※ 여기서 나오는 지표는 면접 점수(5개 역량)에 반영하지 않는다. 보조 코칭 값이므로
   interview_results 를 건드리지 않는다.
"""

import logging
from datetime import datetime, timedelta

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.core.config import (
    VIDEO_ANALYZE_TIMEOUT_MIN,
    VIDEO_MAX_PER_USER,
    VIDEO_MAX_UPLOAD_MB,
    VIDEO_SAMPLE_EVERY,
)
from backend.database import SessionLocal
from backend.models.models import InterviewSession, InterviewVideo, User
from backend.schemas.video import (
    GazeFeedback,
    MyPageVideoItem,
    MyPageVideoListResponse,
    VideoMetricsResponse,
    VideoUploadResponse,
)
from backend.services import video_storage

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 1024 * 1024   # 1MB
_MAX_UPLOAD_BYTES = VIDEO_MAX_UPLOAD_MB * 1024 * 1024


_STALE_ERROR = (
    "분석이 완료되지 않았습니다. 서버가 재시작되었을 수 있으니 다시 업로드해주세요."
)


def mark_if_stale(db: Session, row: InterviewVideo) -> InterviewVideo:
    """
    analyzing 인 채로 너무 오래된 행을 failed 로 바꾼다.

    분석은 백그라운드 스레드에서 도는데, 그 도중 서버가 죽으면 상태를 done/failed 로
    바꿔줄 주체가 사라진다. 그러면 프론트가 영원히 폴링한다. 조회 시점에 경과 시간으로
    끊어주면 별도 정리 작업 없이 해결된다.
    """
    if row.status != "analyzing" or row.created_at is None:
        return row

    elapsed = datetime.now() - row.created_at
    if elapsed < timedelta(minutes=VIDEO_ANALYZE_TIMEOUT_MIN):
        return row

    row.status = "failed"
    row.error_message = _STALE_ERROR
    row.analyzed_at = datetime.now()
    db.commit()
    logger.warning(
        "analyzing 상태로 %s분 초과 — failed 처리 (video_id=%s)",
        VIDEO_ANALYZE_TIMEOUT_MIN, row.video_id,
    )
    return row


def fail_orphaned_analyses() -> int:
    """
    서버 기동 시 호출. 이전 프로세스가 분석 중에 죽어 남긴 analyzing 행을 정리한다.

    조회 시점 정리(mark_if_stale)만으로도 결국 풀리지만, 그건 타임아웃을 기다려야 한다.
    재시작 시점에는 진행 중이던 분석이 확실히 중단된 상태이므로 즉시 정리해도 된다.
    """
    db = SessionLocal()
    try:
        rows = db.query(InterviewVideo).filter(InterviewVideo.status == "analyzing").all()
        for row in rows:
            row.status = "failed"
            row.error_message = _STALE_ERROR
            row.analyzed_at = datetime.now()
        if rows:
            db.commit()
            logger.warning("기동 시 analyzing 상태 %d건을 failed 로 정리했습니다.", len(rows))
        return len(rows)
    finally:
        db.close()


def _video_url(video_id: int) -> str:
    """영상 재생용 경로. S3 로 바꾸면 presigned URL 을 돌려주도록 여기만 고친다."""
    return f"/mypage/videos/{video_id}/file"


def _load_analyze_video():
    """
    video.video_assist.analyze_video 를 지연 import 한다.

    video_assist 는 mediapipe import 에 실패하면 모듈 최상단에서 sys.exit(1) 을 부른다.
    서버 기동 시점에 import 하면 그 자리에서 프로세스가 죽으므로 분석 직전에 import 하고,
    ImportError 뿐 아니라 SystemExit 까지 잡아 "그 영상만 분석 실패"로 격리한다.
    (video/ 는 예진님 담당이라 여기서 우회한다)
    """
    try:
        from video.video_assist import analyze_video
    except (ImportError, SystemExit) as e:
        raise RuntimeError(
            "영상 분석 모듈을 불러올 수 없습니다. "
            "'pip install -r video/requirements.txt' 로 opencv-python·mediapipe 를 설치해주세요."
        ) from e
    return analyze_video


def analyze(video_id: int) -> None:
    """
    백그라운드에서 시선 지표를 계산해 저장한다. (BackgroundTasks 가 스레드풀에서 실행)

    동기 함수인 게 중요하다. async 로 두면 cv2 루프가 이벤트 루프를 통째로 막아
    분석하는 동안 다른 요청이 전부 멈춘다.

    DB 세션은 분석 전후로만 잠깐 연다. 분석이 몇 분씩 걸리는데 그동안 커넥션을 붙들고
    있으면 커넥션 풀이 마른다.
    """
    db = SessionLocal()
    try:
        row = db.get(InterviewVideo, video_id)
        if row is None:      # 보관 개수 초과로 이미 지워졌을 수 있다
            return
        storage_key = row.storage_key
    finally:
        db.close()

    # error 에 담는 문구는 그대로 사용자에게 응답된다. 원본 예외 메시지에는 저장소 절대경로가
    # 들어 있어(analyze_video 의 ValueError) 그대로 내보내면 서버 경로가 노출된다.
    # 상세 내용은 로그에만 남기고, 응답에는 사용자가 조치할 수 있는 문구만 넣는다.
    result = None
    error = None
    try:
        analyze_video = _load_analyze_video()
        # with_timeline=False: 시선 이탈 구간 타임라인은 쓰지 않기로 확정됐다.
        result = analyze_video(
            str(video_storage.local_path(storage_key)),
            sample_every=VIDEO_SAMPLE_EVERY,
            with_timeline=False,
        )
    except RuntimeError as e:
        # _load_analyze_video 의 설치 안내. 경로가 들어가지 않으므로 그대로 쓴다.
        error = str(e)
        logger.exception("영상 분석 모듈 로드 실패 (video_id=%s)", video_id)
    except ValueError:
        # analyze_video 가 파일을 못 열었을 때. 깨진 파일이거나 확장자만 영상인 경우다.
        error = "영상 파일을 읽을 수 없습니다. 녹화가 정상적으로 끝났는지 확인해주세요."
        logger.exception("영상 파일 열기 실패 (video_id=%s)", video_id)
    except Exception:
        error = "영상 분석 중 오류가 발생했습니다."
        logger.exception("영상 분석 실패 (video_id=%s)", video_id)

    db = SessionLocal()
    try:
        row = db.get(InterviewVideo, video_id)
        if row is None:
            return
        if error is not None:
            row.status = "failed"
            row.error_message = error
        elif not result.get("frames_analyzed"):
            # 얼굴이 한 프레임도 검출되지 않은 경우. analyze_video 는 이때도 정상 반환하면서
            # gaze_percent=0 → "시선이 자주 아래로 향해요" 라는 엉뚱한 코칭을 만든다.
            # 응시를 못 한 것이 아니라 측정 자체가 안 된 것이므로 실패로 구분한다.
            row.status = "failed"
            row.error_message = (
                "영상에서 얼굴이 검출되지 않았습니다. "
                "카메라에 얼굴이 보이도록 다시 녹화해주세요."
            )
            row.frames_analyzed = 0
        else:
            gaze = result.get("gaze") or {}
            row.status = "done"
            row.gaze_percent = result.get("gaze_percent")
            row.gaze_level = gaze.get("level")
            row.gaze_message = gaze.get("message")
            row.frames_analyzed = result.get("frames_analyzed")
        row.analyzed_at = datetime.now()
        db.commit()
    finally:
        db.close()


class VideoService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    # ── 내부 헬퍼 ──────────────────────────────────────

    def _get_session(self, session_id: str) -> InterviewSession:
        """내 세션만 반환. 없거나 남의 것이면 404."""
        session = self.db.get(InterviewSession, session_id)
        if session is None or session.users_user_id != self.user.user_id:
            raise HTTPException(status_code=404, detail=f"세션을 찾을 수 없습니다: {session_id}")
        return session

    def _my_videos_query(self):
        """내 영상만, 최신순."""
        return (
            self.db.query(InterviewVideo)
            .join(InterviewSession)
            .filter(InterviewSession.users_user_id == self.user.user_id)
            # created_at 이 같은 초에 몰릴 수 있어 video_id 로 한 번 더 정렬한다.
            .order_by(InterviewVideo.created_at.desc(), InterviewVideo.video_id.desc())
        )

    def _enforce_retention(self) -> list[str]:
        """
        보관 개수를 넘긴 오래된 영상 행을 지우고, 지워야 할 저장소 키를 돌려준다.

        파일은 여기서 지우지 않는다. 커밋이 실패하면 행은 남았는데 파일만 사라진
        (조회는 되지만 재생·재분석이 안 되는) 상태가 되기 때문이다. 커밋 후에 지운다.
        """
        stale = self._my_videos_query().offset(VIDEO_MAX_PER_USER).all()
        keys = [old.storage_key for old in stale]   # 삭제 후에는 속성 접근이 안전하지 않다
        for old in stale:
            self.db.delete(old)
        return keys

    # ── 업로드 ─────────────────────────────────────────

    async def upload(self, session_id: str, video: UploadFile) -> VideoUploadResponse:
        """
        영상을 저장하고 분석 대기 상태로 만든다. 실제 분석은 라우터가 BackgroundTasks 로 건다.
        """
        self._get_session(session_id)

        filename = (video.filename or "").lower()
        extension = next(
            (e for e in video_storage.SUPPORTED_EXTENSIONS if filename.endswith(e)), None
        )
        if extension is None:
            raise HTTPException(
                status_code=415,
                detail=(
                    "지원하지 않는 영상 형식입니다. "
                    f"{', '.join(video_storage.SUPPORTED_EXTENSIONS)} 파일만 업로드할 수 있습니다."
                ),
            )

        key = video_storage.build_key(session_id, extension)
        size = 0
        try:
            with video_storage.open_for_write(key) as f:
                while chunk := await video.read(_CHUNK_SIZE):
                    size += len(chunk)
                    if size > _MAX_UPLOAD_BYTES:
                        # open_for_write 가 예외를 받으면 쓰다 만 파일을 지운다.
                        raise HTTPException(
                            status_code=413,
                            detail=f"영상이 너무 큽니다. {VIDEO_MAX_UPLOAD_MB}MB 이하만 업로드할 수 있습니다.",
                        )
                    f.write(chunk)
        except HTTPException:
            raise
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"영상을 저장하지 못했습니다: {e}")

        if size == 0:
            video_storage.delete(key)
            raise HTTPException(status_code=400, detail="영상 파일이 비어 있습니다.")

        row = InterviewVideo(
            storage_key=key,
            content_type=video.content_type,
            size_bytes=size,
            status="analyzing",
            interview_sessions_session_id=session_id,
        )
        self.db.add(row)
        self.db.flush()   # video_id 를 받아야 백그라운드 작업을 걸 수 있다
        stale_keys = self._enforce_retention()   # 방금 넣은 것이 최신이라 지워지지 않는다
        self.db.commit()

        for key in stale_keys:
            video_storage.delete(key)

        return VideoUploadResponse(
            video_id=row.video_id, session_id=session_id, status="analyzing"
        )

    # ── 조회 ───────────────────────────────────────────

    def metrics(self, session_id: str) -> VideoMetricsResponse:
        """해당 세션의 최신 영상 분석 상태/결과. 프론트가 이걸 폴링한다."""
        self._get_session(session_id)

        row = (
            self._my_videos_query()
            .filter(InterviewVideo.interview_sessions_session_id == session_id)
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=404, detail="이 세션에 업로드된 영상이 없습니다."
            )

        # 폴링 진입점이라 여기서 오래된 analyzing 을 끊어준다.
        row = mark_if_stale(self.db, row)

        gaze = None
        if row.status == "done" and row.gaze_percent is not None:
            gaze = GazeFeedback(
                level=row.gaze_level or "",
                message=row.gaze_message or "",
                gauge=row.gaze_percent,
            )

        return VideoMetricsResponse(
            video_id=row.video_id,
            session_id=session_id,
            status=row.status,
            created_at=row.created_at,
            video_url=_video_url(row.video_id),
            gaze_percent=row.gaze_percent,
            gaze=gaze,
            frames_analyzed=row.frames_analyzed,
            error=row.error_message,
        )

    def my_videos(self) -> MyPageVideoListResponse:
        """마이페이지 영상 목록. 보관 개수만큼만 나온다."""
        rows = self._my_videos_query().all()
        return MyPageVideoListResponse(
            total=len(rows),
            videos=[
                MyPageVideoItem(
                    video_id=row.video_id,
                    interview_id=row.interview_sessions_session_id,
                    date=row.created_at,
                    status=row.status,
                    persona=row.session.persona if row.session else None,
                    gaze_percent=row.gaze_percent,
                    video_url=_video_url(row.video_id),
                )
                for row in rows
            ],
        )

    def file_response(self, video_id: int) -> FileResponse:
        """영상 파일 자체를 내려준다. S3 로 바꾸면 presigned URL 리다이렉트로 교체할 자리."""
        row = self._my_videos_query().filter(InterviewVideo.video_id == video_id).first()
        if row is None:
            raise HTTPException(status_code=404, detail=f"영상을 찾을 수 없습니다: {video_id}")

        path = video_storage.local_path(row.storage_key)
        if not path.exists():
            raise HTTPException(status_code=404, detail="영상 파일이 저장소에 없습니다.")

        # filename= 을 주면 Content-Disposition: attachment 가 붙어 브라우저가 재생 대신
        # 다운로드한다. <video src> 로 재생해야 하므로 넘기지 않는다.
        return FileResponse(path, media_type=row.content_type or "video/webm")
