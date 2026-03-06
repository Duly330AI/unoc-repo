from __future__ import annotations

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Route(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    vrf_id: int = Field(foreign_key="vrf.id", index=True)
    prefix: str = Field(index=True)
    next_hop: str | None = Field(default=None, index=True)
    interface_id: str | None = Field(default=None, foreign_key="interface.id", index=True)
    admin_distance: int = Field(default=1, ge=1)
    metric: int = Field(default=0, ge=0)

    __table_args__ = (
        UniqueConstraint(
            "vrf_id", "prefix", "next_hop", "interface_id", name="uq_route_vrf_prefix_nh_if"
        ),
    )


class Neighbor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    interface_id: str = Field(foreign_key="interface.id", index=True)
    ip_address: str = Field(index=True)
    mac_address: str = Field(index=True)

    __table_args__ = (UniqueConstraint("interface_id", "ip_address", name="uq_neighbor_if_ip"),)
