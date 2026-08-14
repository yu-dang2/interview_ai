"""
음성 입력 라우터

호출할 때마다 OpenAI STT 비용이 나가므로 인증을 요구한다.

엔드포인트:
    POST /voice/transcribe - 음성 파일 → 텍스트 변환 (STT) + 발화 속도

OpenAI GPT-4o-transcribe 사용
"""

import logging
import os
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from openai import OpenAI

from backend.core.config import require_openai_key
from backend.core.deps import current_user
from backend.models.models import User
from backend.schemas.voice import TranscribeResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice"])

# .env 로드와 키 검증은 backend.core.config 가 담당한다.
client = OpenAI(api_key=require_openai_key())


def _speech_rate(text: str, duration_sec: float) -> dict | None:
    """
    발화 속도(분당 글자수)를 계산한다. 계산할 수 없으면 None.

    video.video_assist 를 지연 import 하는 이유: 이 모듈은 mediapipe import 에
    실패하면 최상단에서 sys.exit(1) 을 부른다. 서버 기동 시점에 import 하면 그
    자리에서 프로세스가 죽으므로, 필요할 때 부르고 SystemExit 까지 잡는다.
    (video/ 는 예진님 담당이라 여기서 우회한다)

    발화 속도는 부가 지표라, 계산에 실패해도 STT 결과는 그대로 내보낸다.
    """
    if duration_sec <= 0 or not text.strip():
        return None

    try:
        from video.video_assist import speech_rate
    except (ImportError, SystemExit) as e:
        logger.warning("발화 속도 모듈을 불러올 수 없어 건너뜁니다: %s", e)
        return None

    try:
        return speech_rate(text, duration_sec)
    except Exception as e:
        logger.warning("발화 속도 계산 실패: %s: %s", type(e).__name__, e)
        return None


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    audio: UploadFile = File(...),
    duration: float = Form(0.0),
    user: User = Depends(current_user),
):
    """
    음성 파일 → 텍스트(STT)

    duration 은 프론트가 잰 녹음 시간(초)이다. 선택 항목이라 보내지 않아도 되고,
    보내면 발화 속도(speech_cpm)를 함께 돌려준다. 서버는 사용자가 언제부터
    말했는지 알 수 없어 녹음한 쪽에서만 얻을 수 있는 값이다.

    지원 형식:
    - webm
    - wav
    - mp3
    - m4a
    - mp4
    """

    try:
        # 업로드 파일 임시 저장
        suffix = "." + audio.filename.split(".")[-1]

        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(await audio.read())
            temp_path = temp_file.name

        # OpenAI STT 호출
        with open(temp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=f,
            )

        # 임시파일 삭제
        os.remove(temp_path)

        rate = _speech_rate(transcript.text, duration)

        return TranscribeResponse(
            text=transcript.text,
            speech_cpm=(rate or {}).get("speech_cpm"),
            speech=(rate or {}).get("speech"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"STT 변환 실패: {str(e)}"
        )
