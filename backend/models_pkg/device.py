from __future__ import annotations

from enum import Enum

from sqlalchemy import Column as SAColumn
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class DeviceType(str, Enum):
    BACKBONE_GATEWAY = "BACKBONE_GATEWAY"
    POP = "POP"
    CORE_SITE = "CORE_SITE"
    CORE_ROUTER = "CORE_ROUTER"
    EDGE_ROUTER = "EDGE_ROUTER"
    AON_SWITCH = "AON_SWITCH"
    OLT = "OLT"
    ONT = "ONT"
    AON_CPE = "AON_CPE"
    SPLITTER = "SPLITTER"
    HOP = "HOP"
    NVT = "NVT"
    ODF = "ODF"
    BUSINESS_ONT = "BUSINESS_ONT"


class Status(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    DEGRADED = "DEGRADED"
    BLOCKING = "BLOCKING"


class DeviceRole(str, Enum):
    ACTIVE = "active"
    PASSIVE = "passive"
    ALWAYS_ONLINE = "always_online"


class Device(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    name: str = Field(index=True)
    type: DeviceType = Field(
        sa_column=SAColumn(SAEnum(DeviceType, native_enum=False), nullable=False)
    )
    status: Status = Field(
        default=Status.UP, sa_column=SAColumn(SAEnum(Status, native_enum=False), nullable=False)
    )
    # Provisioning & status fields
    provisioned: bool = False
    admin_override_status: Status | None = Field(
        default=None, sa_column=SAColumn(SAEnum(Status, native_enum=False), nullable=True)
    )
    # Optical placeholders
    tx_power_dbm: float | None = None
    sensitivity_min_dbm: float | None = None
    insertion_loss_db: float | None = None
    # Capacity override in Mbps
    capacity: int | None = None

    class SignalStatus(str, Enum):
        OK = "OK"
        WARNING = "WARNING"
        CRITICAL = "CRITICAL"
        NO_SIGNAL = "NO_SIGNAL"

    signal_power_dbm: float | None = None
    signal_margin_db: float | None = None
    attenuation_db: float | None = None  # Total optical path attenuation
    signal_status: Device.SignalStatus | None = Field(
        default=None, sa_column=SAColumn(SAEnum(SignalStatus, native_enum=False), nullable=True)
    )
    parent_container_id: str | None = Field(default=None, foreign_key="device.id")
    slot_id: str | None = Field(default=None)
    tariff_id: int | None = Field(default=None, foreign_key="tariff.id", index=True)
    vrf_id: int | None = Field(default=None, foreign_key="vrf.id", index=True)
    hardware_model_id: int | None = Field(default=None, foreign_key="hardwaremodel.id", index=True)

    __table_args__ = (Index("ix_device_parent_container_id", "parent_container_id"),)

    def derive_role(self) -> DeviceRole:
        # Passive optical elements (inline path components)
        if self.type in {DeviceType.SPLITTER, DeviceType.HOP, DeviceType.NVT, DeviceType.ODF}:
            return DeviceRole.PASSIVE
        # Always-online restricted: backbone gateway + POP/CORE_SITE only
        if self.type in {DeviceType.BACKBONE_GATEWAY, DeviceType.POP, DeviceType.CORE_SITE}:
            return DeviceRole.ALWAYS_ONLINE
        return DeviceRole.ACTIVE
