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


# ── 최적화 적용 ────────────────────────────────────────

class ApplyOptimizationRequest(BaseModel):
    """
    적용할 제안을 고른다.

    suggestion_ids 를 비우면 전체 적용이다. 화면에서 제안별로 "적용" 버튼을 누르므로
    일부만 고르는 경우가 기본이다.
    """

    session_id: str
    suggestion_ids: list[str] = []


class ApplyOptimizationResponse(BaseModel):
    # 적용 결과는 새 이력서로 만든다. 원본을 덮어쓰면 되돌릴 수 없고,
    # 마이페이지의 이력서 버전 관리도 원본이 남아 있어야 성립한다.
    resume_id: int
    source_resume_id: int
    applied_count: int
    content: str
