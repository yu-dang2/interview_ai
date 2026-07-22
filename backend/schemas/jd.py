"""
직무기술서(JD) 스키마
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JDCreateRequest(BaseModel):
    title: str
    content: str


class JDResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    jd_id: int
    title: str | None = None
    content: str
    created_at: datetime | None = None


class JDListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    jd_id: int
    title: str | None = None
    created_at: datetime | None = None
