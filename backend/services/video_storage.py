"""
면접 영상 저장소

지금은 로컬 디스크에 두지만 배포 시 S3 로 바꾼다. 그래서 저장·조회·삭제를 이 세 함수로
격리해두고, 나머지 코드(video_service, 라우터)는 storage_key 문자열만 들고 다닌다.
S3 전환 시 고칠 곳은 이 파일뿐이다.

    open_for_write() → 임시 파일에 쓰고, 정상 종료 시 upload_fileobj
    local_path()     → 임시 디렉터리로 download_file 후 그 경로 반환
                       (cv2.VideoCapture 가 로컬 파일 경로를 요구하므로 다운로드는 불가피하다)
    delete()         → boto3 delete_object

파일명 규칙: {session_id}_{uuid}{확장자}. 업로드된 원본 파일명을 쓰지 않는 이유는
경로 조작(../) 차단과 한글 파일명 회피 두 가지다. OpenCV 는 Windows 에서 비ASCII
경로를 열지 못한다.
"""

import uuid
from contextlib import contextmanager
from pathlib import Path

from backend.core.config import VIDEO_STORAGE_DIR

# 웹캠 녹화는 webm 으로 나오고, 나머지는 재업로드/테스트용이다.
SUPPORTED_EXTENSIONS = (".webm", ".mp4", ".mov", ".mkv", ".avi")

_BASE_DIR = Path(VIDEO_STORAGE_DIR).resolve()


def build_key(session_id: str, extension: str) -> str:
    """저장 키를 만든다. 확장자는 SUPPORTED_EXTENSIONS 중 하나여야 한다."""
    return f"{session_id}_{uuid.uuid4().hex}{extension}"


@contextmanager
def open_for_write(key: str):
    """
    쓰기용 파일 객체를 연다. 영상은 수백 MB 라 통째로 메모리에 올리지 않고 청크로 흘려 넣는다.

        with video_storage.open_for_write(key) as f:
            f.write(chunk)

    블록 안에서 예외가 나면(크기 초과·연결 끊김) 반쪽짜리 파일을 지우고 예외를 그대로 올린다.
    """
    _BASE_DIR.mkdir(parents=True, exist_ok=True)
    path = _BASE_DIR / key
    try:
        with path.open("wb") as f:
            yield f
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def local_path(key: str) -> Path:
    """
    분석기(cv2)와 파일 응답이 읽을 실제 경로.

    S3 로 바꾸면 여기서 임시 파일로 내려받아 그 경로를 돌려주면 된다.
    """
    return _BASE_DIR / key


def delete(key: str) -> None:
    """저장된 영상을 지운다. 이미 없으면 조용히 넘어간다."""
    local_path(key).unlink(missing_ok=True)
