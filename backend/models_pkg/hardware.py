from __future__ import annotations

from sqlalchemy import Column as SAColumn
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from .device import DeviceType
from .interface import PortRole


class HardwareModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    catalog_id: str = Field(index=True, unique=True)
    device_type: DeviceType = Field(
        sa_column=SAColumn(SAEnum(DeviceType, native_enum=False), nullable=False)
    )
    vendor: str
    model: str
    version: str
    ports_total: int | None = Field(default=None)
    capacity_gbps: float | None = Field(default=None)
    tx_power_dbm: float | None = Field(default=None)
    sensitivity_min_dbm: float | None = Field(default=None)
    insertion_loss_db: float | None = Field(default=None)
    meta_source: str | None = Field(default=None)
    meta_notes: str | None = Field(default=None)

    __table_args__ = (
        UniqueConstraint("catalog_id", name="uq_hardware_model_catalog_id"),
        Index("ix_hardware_vendor_model", "vendor", "model"),
        Index("ix_hardware_device_type", "device_type"),
    )


class PortProfile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hardware_model_id: int = Field(foreign_key="hardwaremodel.id", index=True)
    name: str
    count: int = 0
    speed_gbps: float | None = Field(default=None)
    role: str | None = Field(default=None)
    media: str | None = Field(default=None)
    port_role: PortRole | None = Field(
        default=None, sa_column=SAColumn(SAEnum(PortRole, native_enum=False), nullable=True)
    )
    max_subscribers: int | None = Field(default=None)

    __table_args__ = (
        UniqueConstraint("hardware_model_id", "name", name="uq_portprofile_model_name"),
        Index("ix_portprofile_port_role", "port_role"),
    )
