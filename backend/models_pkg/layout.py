from __future__ import annotations

from sqlmodel import Field, SQLModel


class LayoutPositionRecord(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    x: float
    y: float
    user_pinned: bool | None = None
    system_pinned: bool | None = None
