"""패키지를 import하면 하위 모듈보다 먼저 프로젝트 루트의 .env를 로딩한다."""

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
