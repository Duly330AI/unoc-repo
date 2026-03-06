from __future__ import annotations

from enum import Enum

from sqlalchemy import Column as SAColumn
from sqlalchemy import Enum as SAEnum
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class MacEntryType(str, Enum):
    DYNAMIC = "dynamic"
    STATIC = "static"


class BridgeDomain(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    device_id: str = Field(foreign_key="device.id", index=True)

    __table_args__ = (UniqueConstraint("device_id", "name", name="uq_bd_device_name"),)


class MacAddressEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    mac_address: str = Field(index=True)
    interface_id: str = Field(foreign_key="interface.id", index=True)
    bridge_domain_id: int = Field(foreign_key="bridgedomain.id", index=True)
    type: MacEntryType = Field(
        default=MacEntryType.DYNAMIC,
        sa_column=SAColumn(SAEnum(MacEntryType, native_enum=False), nullable=False),
    )

    __table_args__ = (UniqueConstraint("bridge_domain_id", "mac_address", name="uq_mac_bd_mac"),)
