from __future__ import annotations

from enum import Enum

from sqlalchemy import Column as SAColumn
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class ProvisioningAction(str, Enum):
    ASSIGN_MGMT_IP = "assign_mgmt_ip"


class ProvisioningRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ts: str
    action: ProvisioningAction = Field(
        default=ProvisioningAction.ASSIGN_MGMT_IP,
        sa_column=SAColumn(SAEnum(ProvisioningAction, native_enum=False), nullable=False),
    )
    device_id: str = Field(foreign_key="device.id", index=True)
    interface_id: str = Field(foreign_key="interface.id", index=True)
    ip: str = Field(index=True)
    vrf_id: int | None = Field(default=None, foreign_key="vrf.id", index=True)
    prefix_id: int | None = Field(default=None, foreign_key="prefix.id", index=True)
    actor: str | None = Field(default=None, index=True)
    correlation_id: str | None = Field(default=None, index=True)

    __table_args__ = (Index("ix_provrec_device_ts", "device_id", "ts"),)
