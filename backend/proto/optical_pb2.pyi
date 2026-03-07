from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class RecomputeRequest(_message.Message):
    __slots__ = ("link_ids", "device_ids", "force_full_recompute", "request_id")
    LINK_IDS_FIELD_NUMBER: _ClassVar[int]
    DEVICE_IDS_FIELD_NUMBER: _ClassVar[int]
    FORCE_FULL_RECOMPUTE_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    link_ids: _containers.RepeatedScalarFieldContainer[str]
    device_ids: _containers.RepeatedScalarFieldContainer[str]
    force_full_recompute: bool
    request_id: str
    def __init__(
        self,
        link_ids: _Iterable[str] | None = ...,
        device_ids: _Iterable[str] | None = ...,
        force_full_recompute: bool = ...,
        request_id: str | None = ...,
    ) -> None: ...

class RecomputeResponse(_message.Message):
    __slots__ = ("affected_onts", "ont_ids", "duration_ms", "status", "errors", "request_id")
    AFFECTED_ONTS_FIELD_NUMBER: _ClassVar[int]
    ONT_IDS_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    affected_onts: int
    ont_ids: _containers.RepeatedScalarFieldContainer[str]
    duration_ms: int
    status: str
    errors: _containers.RepeatedScalarFieldContainer[str]
    request_id: str
    def __init__(
        self,
        affected_onts: int | None = ...,
        ont_ids: _Iterable[str] | None = ...,
        duration_ms: int | None = ...,
        status: str | None = ...,
        errors: _Iterable[str] | None = ...,
        request_id: str | None = ...,
    ) -> None: ...

class GetPathRequest(_message.Message):
    __slots__ = ("ont_id", "request_id")
    ONT_ID_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    ont_id: str
    request_id: str
    def __init__(self, ont_id: str | None = ..., request_id: str | None = ...) -> None: ...

class OpticalPath(_message.Message):
    __slots__ = (
        "ont_id",
        "segments",
        "total_attenuation_db",
        "rx_power_dbm",
        "margin_db",
        "status",
        "olt_id",
        "request_id",
    )
    ONT_ID_FIELD_NUMBER: _ClassVar[int]
    SEGMENTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_ATTENUATION_DB_FIELD_NUMBER: _ClassVar[int]
    RX_POWER_DBM_FIELD_NUMBER: _ClassVar[int]
    MARGIN_DB_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    OLT_ID_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    ont_id: str
    segments: _containers.RepeatedCompositeFieldContainer[PathSegment]
    total_attenuation_db: float
    rx_power_dbm: float
    margin_db: float
    status: str
    olt_id: str
    request_id: str
    def __init__(
        self,
        ont_id: str | None = ...,
        segments: _Iterable[PathSegment | _Mapping] | None = ...,
        total_attenuation_db: float | None = ...,
        rx_power_dbm: float | None = ...,
        margin_db: float | None = ...,
        status: str | None = ...,
        olt_id: str | None = ...,
        request_id: str | None = ...,
    ) -> None: ...

class PathSegment(_message.Message):
    __slots__ = (
        "link_id",
        "from_device_id",
        "from_device_type",
        "to_device_id",
        "to_device_type",
        "attenuation_db",
        "cumulative_attenuation_db",
    )
    LINK_ID_FIELD_NUMBER: _ClassVar[int]
    FROM_DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    FROM_DEVICE_TYPE_FIELD_NUMBER: _ClassVar[int]
    TO_DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    TO_DEVICE_TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTENUATION_DB_FIELD_NUMBER: _ClassVar[int]
    CUMULATIVE_ATTENUATION_DB_FIELD_NUMBER: _ClassVar[int]
    link_id: str
    from_device_id: str
    from_device_type: str
    to_device_id: str
    to_device_type: str
    attenuation_db: float
    cumulative_attenuation_db: float
    def __init__(
        self,
        link_id: str | None = ...,
        from_device_id: str | None = ...,
        from_device_type: str | None = ...,
        to_device_id: str | None = ...,
        to_device_type: str | None = ...,
        attenuation_db: float | None = ...,
        cumulative_attenuation_db: float | None = ...,
    ) -> None: ...

class HealthRequest(_message.Message):
    __slots__ = ("component",)
    COMPONENT_FIELD_NUMBER: _ClassVar[int]
    component: str
    def __init__(self, component: str | None = ...) -> None: ...

class HealthResponse(_message.Message):
    __slots__ = (
        "status",
        "version",
        "uptime_seconds",
        "db_status",
        "last_recompute_timestamp",
        "total_onts",
    )
    STATUS_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    UPTIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    DB_STATUS_FIELD_NUMBER: _ClassVar[int]
    LAST_RECOMPUTE_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    TOTAL_ONTS_FIELD_NUMBER: _ClassVar[int]
    status: str
    version: str
    uptime_seconds: int
    db_status: str
    last_recompute_timestamp: int
    total_onts: int
    def __init__(
        self,
        status: str | None = ...,
        version: str | None = ...,
        uptime_seconds: int | None = ...,
        db_status: str | None = ...,
        last_recompute_timestamp: int | None = ...,
        total_onts: int | None = ...,
    ) -> None: ...
