from __future__ import annotations

from enum import Enum

from sqlalchemy import Column as SAColumn
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, SQLModel


class Tariff(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    max_up_mbps: float = Field(default=0.0, ge=0.0)
    max_down_mbps: float = Field(default=0.0, ge=0.0)

    class TariffTechnology(str, Enum):
        GPON = "GPON"
        AON = "AON"

    technology: Tariff.TariffTechnology | None = Field(
        default=None, sa_column=SAColumn(SAEnum(TariffTechnology, native_enum=False), nullable=True)
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_tariff_name"),
        Index("ix_tariff_technology", "technology"),
    )
