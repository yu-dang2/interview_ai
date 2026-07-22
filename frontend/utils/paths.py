"""
cwd에 의존하지 않는 리소스 절대경로 헬퍼.

streamlit을 frontend/ 밖(프로젝트 루트 등)에서 실행하거나 어떤 페이지로 직접 진입해도
assets/styles를 항상 찾도록, 모든 리소스 경로를 이 파일 위치(frontend/) 기준
절대경로로 고정한다.

추가로, 한글 파일명의 유니코드 정규화 불일치(NFC/NFD)도 흡수한다.
  - macOS는 파일명을 NFD(분해형)로 저장 → git에도 NFD로 커밋된다.
  - 소스 코드의 문자열 리터럴은 보통 NFC(결합형)다.
  - Windows에서 NFC 리터럴로 NFD 파일을 찾으면 FileNotFoundError가 난다.
정확 경로가 없으면 같은 디렉터리에서 NFC 기준으로 같은 이름을 찾아 반환한다.

사용:
    from utils.paths import resource
    css = resource("styles/global.css").read_text(encoding="utf-8")
    img = resource("assets/images/기술리드.png").read_bytes()
"""

import unicodedata
from pathlib import Path

# utils/paths.py → utils/ → frontend/
FRONTEND_DIR = Path(__file__).resolve().parent.parent


def resource(rel_path: str) -> Path:
    """frontend/ 기준 상대경로를 절대 Path로 변환한다.

    정확 경로가 없으면 한글 파일명 정규화(NFC/NFD) 불일치를 흡수해 실제 파일을 찾는다.
    """
    target = FRONTEND_DIR / rel_path
    if target.exists():
        return target

    # 정규화 무시 매칭: 부모 디렉터리에서 NFC 기준으로 같은 이름을 찾는다.
    parent = target.parent
    if parent.is_dir():
        want = unicodedata.normalize("NFC", target.name)
        for entry in parent.iterdir():
            if unicodedata.normalize("NFC", entry.name) == want:
                return entry

    # 못 찾으면 원래 경로를 반환한다(호출부에서 명확한 에러가 나도록).
    return target
