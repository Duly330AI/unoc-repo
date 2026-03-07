from __future__ import annotations

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class PhysicalMedium(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    kind: str = Field(index=True)
    max_range_km: float | None = Field(default=None)

    __table_args__ = (UniqueConstraint("code", name="uq_physical_medium_code"),)
