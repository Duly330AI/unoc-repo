from __future__ import annotations

import ipaddress

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class IPPool(SQLModel, table=True):
    pool_key: str = Field(primary_key=True)
    cidr: str
    next_index: int = 1

    def allocate(self) -> str:
        net = ipaddress.ip_network(self.cidr)
        hosts = list(net.hosts())
        idx = self.next_index - 1
        if idx >= len(hosts):
            raise RuntimeError("POOL_EXHAUSTED")
        ip_obj = hosts[idx]
        self.next_index += 1
        return str(ip_obj)


class InterfaceAddress(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    interface_id: str = Field(index=True)
    ip: str
    prefix_len: int
    vrf_id: int | None = Field(default=None, foreign_key="vrf.id", index=True)
    prefix_id: int | None = Field(default=None, foreign_key="prefix.id", index=True)

    __table_args__ = (
        UniqueConstraint("prefix_id", "ip", name="uq_interface_address_prefix_ip"),
        UniqueConstraint("vrf_id", "ip", name="uq_interface_address_vrf_ip"),
    )


class VRF(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)


class Prefix(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    prefix: str = Field(index=True)
    vrf_id: int = Field(foreign_key="vrf.id", index=True)
    description: str | None = Field(default=None)

    __table_args__ = (UniqueConstraint("vrf_id", "prefix", name="uq_prefix_vrf_prefix"),)
