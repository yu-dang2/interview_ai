"""브랜드 로고·파비콘 (말풍선 속 따옴표 + intro).

로고는 글자를 도형 경로로 바꾼 SVG라 글꼴 설치 여부와 상관없이 똑같이 보인다.
st.markdown HTML 안에 바로 넣을 수 있게 data URL <img>로 만든다.
"""
import base64
from functools import lru_cache

from utils.paths import resource

FAVICON = str(resource("assets/images/logo/favicon.png"))


@lru_cache(maxsize=None)
def _b64(name: str) -> str:
    return base64.b64encode(resource(f"assets/images/logo/{name}").read_bytes()).decode()


def logo_img(height: int = 28, white: bool = False) -> str:
    """로고 <img> HTML. white=True는 파란 배경용(흰 말풍선 + 흰 글자)."""
    name = "intro_logo_white.svg" if white else "intro_logo.svg"
    return (
        f'<img src="data:image/svg+xml;base64,{_b64(name)}" alt="intro" '
        f'style="height:{height}px;width:auto;display:block;">'
    )
