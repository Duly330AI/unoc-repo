from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class PropagateRequest(_message.Message):
    __slots__ = ("changed_device_ids", "changed_link_ids", "force_full_propagation", "request_id")
    CHANGED_DEVICE_IDS_FIELD_NUMBER: _ClassVar[int]
    CHANGED_LINK_IDS_FIELD_NUMBER: _ClassVar[int]
    FORCE_FULL_PROPAGATION_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    changed_device_ids: _containers.RepeatedScalarFieldContainer[str]
    changed_link_ids: _containers.RepeatedScalarFieldContainer[str]
    force_full_propagation: bool
    request_id: str
    def __init__(
        self,
        changed_device_ids: _Iterable[str] | None = ...,
        changed_link_ids: _Iterable[str] | None = ...,
        force_full_propagation: bool = ...,
        request_id: str | None = ...,
    ) -> None: ...

class PropagateResponse(_message.Message):
    __slots__ = ("affected_devices", "device_ids", "duration_ms", "status", "errors", "request_id")
    AFFECTED_DEVICES_FIELD_NUMBER: _ClassVar[int]
    DEVICE_IDS_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    affected_devices: int
    device_ids: _containers.RepeatedScalarFieldContainer[str]
    duration_ms: int
    status: str
    errors: _containers.RepeatedScalarFieldContainer[str]
    request_id: str
    def __init__(
        self,
        affected_devices: int | None = ...,
        device_ids: _Iterable[str] | None = ...,
        duration_ms: int | None = ...,
        status: str | None = ...,
        errors: _Iterable[str] | None = ...,
        request_id: str | None = ...,
    ) -> None: ...

class GetDepsRequest(_message.Message):
    __slots__ = ("device_id", "max_depth", "request_id")
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    MAX_DEPTH_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    max_depth: int
    request_id: str
    def __init__(
        self, device_id: str | None = ..., max_depth: int | None = ..., request_id: str | None = ...
    ) -> None: ...

class DependencyTree(_message.Message):
    __slots__ = ("device_id", "dependencies", "max_depth", "request_id")
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    DEPENDENCIES_FIELD_NUMBER: _ClassVar[int]
    MAX_DEPTH_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    dependencies: _containers.RepeatedCompositeFieldContainer[Dependency]
    max_depth: int
    request_id: str
    def __init__(
        self,
        device_id: str | None = ...,
        dependencies: _Iterable[Dependency | _Mapping] | None = ...,
        max_depth: int | None = ...,
        request_id: str | None = ...,
    ) -> None: ...

class Dependency(_message.Message):
    __slots__ = ("device_id", "device_type", "link_id", "depth", "status", "children")
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    DEVICE_TYPE_FIELD_NUMBER: _ClassVar[int]
    LINK_ID_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CHILDREN_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    device_type: str
    link_id: str
    depth: int
    status: str
    children: _containers.RepeatedCompositeFieldContainer[Dependency]
    def __init__(
        self,
        device_id: str | None = ...,
        device_type: str | None = ...,
        link_id: str | None = ...,
        depth: int | None = ...,
        status: str | None = ...,
        children: _Iterable[Dependency | _Mapping] | None = ...,
    ) -> None: ...

class BulkStatusRequest(_message.Message):
    __slots__ = ("updates", "skip_propagation", "request_id")
    UPDATES_FIELD_NUMBER: _ClassVar[int]
    SKIP_PROPAGATION_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    updates: _containers.RepeatedCompositeFieldContainer[StatusUpdate]
    skip_propagation: bool
    request_id: str
    def __init__(
        self,
        updates: _Iterable[StatusUpdate | _Mapping] | None = ...,
        skip_propagation: bool = ...,
        request_id: str | None = ...,
    ) -> None: ...

class StatusUpdate(_message.Message):
    __slots__ = ("device_id", "status", "reason")
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    status: str
    reason: str
    def __init__(
        self, device_id: str | None = ..., status: str | None = ..., reason: str | None = ...
    ) -> None: ...

class BulkStatusResponse(_message.Message):
    __slots__ = (
        "updated",
        "device_ids",
        "failed",
        "duration_ms",
        "propagation_status",
        "propagation_duration_ms",
        "request_id",
    )
    UPDATED_FIELD_NUMBER: _ClassVar[int]
    DEVICE_IDS_FIELD_NUMBER: _ClassVar[int]
    FAILED_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    PROPAGATION_STATUS_FIELD_NUMBER: _ClassVar[int]
    PROPAGATION_DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    updated: int
    device_ids: _containers.RepeatedScalarFieldContainer[str]
    failed: _containers.RepeatedCompositeFieldContainer[StatusFailure]
    duration_ms: int
    propagation_status: str
    propagation_duration_ms: int
    request_id: str
    def __init__(
        self,
        updated: int | None = ...,
        device_ids: _Iterable[str] | None = ...,
        failed: _Iterable[StatusFailure | _Mapping] | None = ...,
        duration_ms: int | None = ...,
        propagation_status: str | None = ...,
        propagation_duration_ms: int | None = ...,
        request_id: str | None = ...,
    ) -> None: ...

class StatusFailure(_message.Message):
    __slots__ = ("device_id", "error")
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    error: str
    def __init__(self, device_id: str | None = ..., error: str | None = ...) -> None: ...

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
        "last_propagation_timestamp",
        "total_devices",
    )
    STATUS_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    UPTIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    DB_STATUS_FIELD_NUMBER: _ClassVar[int]
    LAST_PROPAGATION_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    TOTAL_DEVICES_FIELD_NUMBER: _ClassVar[int]
    status: str
    version: str
    uptime_seconds: int
    db_status: str
    last_propagation_timestamp: int
    total_devices: int
    def __init__(
        self,
        status: str | None = ...,
        version: str | None = ...,
        uptime_seconds: int | None = ...,
        db_status: str | None = ...,
        last_propagation_timestamp: int | None = ...,
        total_devices: int | None = ...,
    ) -> None: ...
