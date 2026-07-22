"""
agent.graph 패키지

이 패키지의 하위 모듈(utils, nodes, interview_agent 등)을 import하면
파이썬이 __init__.py를 먼저 실행하므로, 환경변수를 읽는 코드가 동작하기 전에
.env 로딩이 항상 보장된다.

find_dotenv()는 상위 디렉토리로 올라가며 .env를 찾으므로
실행 위치(cwd)가 달라도 프로젝트 루트의 .env를 찾을 수 있다.
"""

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
