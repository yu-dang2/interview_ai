"""
음성 관련 Pydantic 스키마
"""

from pydantic import BaseModel


class TranscribeResponse(BaseModel):
    text: str