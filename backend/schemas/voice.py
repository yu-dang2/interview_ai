"""
음성 관련 Pydantic 스키마
"""

from pydantic import BaseModel


class SpeechFeedback(BaseModel):
    """video_assist.speech_feedback() 의 반환 형태 그대로."""

    level: str      # 빠름 / 적정 / 느림
    message: str
    gauge: float    # 분당 글자수


class TranscribeResponse(BaseModel):
    text: str

    # 발화 속도. 프론트가 녹음 시간을 함께 보낸 경우에만 채워진다.
    # 서버는 오디오 파일 길이만 알 뿐 사용자가 언제부터 말했는지 모르므로,
    # 녹음한 쪽이 알려주지 않으면 계산할 수 없다.
    speech_cpm: float | None = None
    speech: SpeechFeedback | None = None
