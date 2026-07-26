"""
음성 입력 라우터

엔드포인트:
    POST /voice/transcribe - 음성 파일 → 텍스트 변환 (STT)

OpenAI GPT-4o-transcribe 사용
"""

import os
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, UploadFile, File, HTTPException
from openai import OpenAI

from backend.core.config import require_openai_key
from backend.schemas.voice import TranscribeResponse

router = APIRouter(prefix="/voice", tags=["Voice"])

# .env 로드와 키 검증은 backend.core.config 가 담당한다.
client = OpenAI(api_key=require_openai_key())


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)):
    """
    음성 파일 → 텍스트(STT)

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

        return TranscribeResponse(
            text=transcript.text
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"STT 변환 실패: {str(e)}"
        )