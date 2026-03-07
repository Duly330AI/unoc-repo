from __future__ import annotations

from enum import Enum

from sqlalchemy import Column as SAColumn
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, SQLModel


class InterfaceRole(str, Enum):
    MANAGEMENT = "management"
    P2P_UPLINK = "p2p_uplink"
    ACCESS = "access"


class PortRole(str, Enum):
    ACCESS = "ACCESS"
    UPLINK = "UPLINK"
    PON = "PON"
    TRUNK = "TRUNK"


class AdminStatus(str, Enum):
    UP = "up"
    DOWN = "down"


class Interface(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    device_id: str = Field(foreign_key="device.id", index=True)
    name: str
    role: InterfaceRole | None = Field(
        default=None, sa_column=SAColumn(SAEnum(InterfaceRole, native_enum=False), nullable=True)
    )
    admin_status: AdminStatus = Field(
        default=AdminStatus.UP,
        sa_column=SAColumn(SAEnum(AdminStatus, native_enum=False), nullable=False),
    )
    capacity: int | None = None
    port_role: PortRole | None = Field(
        default=None, sa_column=SAColumn(SAEnum(PortRole, native_enum=False), nullable=True)
    )
    bridge_domain_id: int | None = Field(default=None, foreign_key="bridgedomain.id", index=True)
    profile_name: str | None = Field(default=None, index=True)
    mac_address: str | None = Field(default=None, index=True, unique=True)

    __table_args__ = (
        UniqueConstraint("device_id", "name", name="uq_interface_device_name"),
        UniqueConstraint("mac_address", name="uq_interface_mac_address"),
        Index("ix_interface_role", "role"),
        Index("ix_interface_port_role", "port_role"),
    )
