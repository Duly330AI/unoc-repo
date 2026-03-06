from __future__ import annotations

from enum import Enum

from sqlalchemy import Column as SAColumn
from sqlalchemy import Enum as SAEnum
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from .device import Status


class LinkType(str, Enum):
    FIBER = "FIBER"
    P2P = "P2P"
    MGMT = "MGMT"


class Link(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    a_interface_id: str = Field(foreign_key="interface.id", index=True)
    b_interface_id: str = Field(foreign_key="interface.id", index=True)
    status: Status = Field(
        default=Status.UP, sa_column=SAColumn(SAEnum(Status, native_enum=False), nullable=False)
    )
    kind: LinkType = Field(
        default=LinkType.FIBER,
        sa_column=SAColumn(SAEnum(LinkType, native_enum=False), nullable=False),
    )
    admin_override_status: Status | None = Field(
        default=None, sa_column=SAColumn(SAEnum(Status, native_enum=False), nullable=True)
    )
    protection_mode: str | None = Field(default=None, index=True)
    length_km: float | None = Field(default=None, index=True)
    physical_medium_id: int | None = Field(
        default=None, foreign_key="physicalmedium.id", index=True
    )

    __table_args__ = (
        UniqueConstraint("a_interface_id", "b_interface_id", name="uq_link_endpoints"),
    )
