"""
이력서 스키마
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeCreateRequest(BaseModel):
    content: str


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resume_id: int
    content: str
    created_at: datetime | None = None


class ResumeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resume_id: int
    created_at: datetime | None = None
