import unicodedata
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent


def resource(rel: str) -> Path:
    """frontend/ 기준 절대경로 반환. 실행 위치(cwd)와 무관하게 항상 동일한 파일을 찾는다.

    정확히 일치하는 파일이 없으면 파일명을 NFC/NFD 정규화 무시하고 매칭한다.
    (macOS는 한글 파일명을 NFD로 저장하는 경우가 있어, Windows에서 커밋된 NFC 파일명과
    바이트 단위로 다를 수 있음 — 이 차이를 흡수한다.)
    """
    path = FRONTEND_DIR / rel
    if path.exists():
        return path

    target_name = unicodedata.normalize("NFC", path.name)
    parent = path.parent
    if parent.exists():
        for candidate in parent.iterdir():
            if unicodedata.normalize("NFC", candidate.name) == target_name:
                return candidate

    return path
