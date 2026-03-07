from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class CreateLinksRequest(_message.Message):
    __slots__ = ("links", "skip_validation", "skip_recompute", "request_id")
    LINKS_FIELD_NUMBER: _ClassVar[int]
    SKIP_VALIDATION_FIELD_NUMBER: _ClassVar[int]
    SKIP_RECOMPUTE_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    links: _containers.RepeatedCompositeFieldContainer[LinkCreate]
    skip_validation: bool
    skip_recompute: bool
    request_id: str
    def __init__(
        self,
        links: _Iterable[LinkCreate | _Mapping] | None = ...,
        skip_validation: bool = ...,
        skip_recompute: bool = ...,
        request_id: str | None = ...,
    ) -> None: ...

class LinkCreate(_message.Message):
    __slots__ = (
        "a_interface_id",
        "b_interface_id",
        "classification",
        "attenuation_db",
        "label",
        "metadata",
    )
    A_INTERFACE_ID_FIELD_NUMBER: _ClassVar[int]
    B_INTERFACE_ID_FIELD_NUMBER: _ClassVar[int]
    CLASSIFICATION_FIELD_NUMBER: _ClassVar[int]
    ATTENUATION_DB_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    a_interface_id: str
    b_interface_id: str
    classification: str
    attenuation_db: float
    label: str
    metadata: str
    def __init__(
        self,
        a_interface_id: str | None = ...,
        b_interface_id: str | None = ...,
        classification: str | None = ...,
        attenuation_db: float | None = ...,
        label: str | None = ...,
        metadata: str | None = ...,
    ) -> None: ...

class CreateLinksResponse(_message.Message):
    __slots__ = (
        "created",
        "link_ids",
        "failed",
        "duration_ms",
        "recompute_status",
        "recompute_duration_ms",
        "request_id",
    )
    CREATED_FIELD_NUMBER: _ClassVar[int]
    LINK_IDS_FIELD_NUMBER: _ClassVar[int]
    FAILED_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    RECOMPUTE_STATUS_FIELD_NUMBER: _ClassVar[int]
    RECOMPUTE_DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    created: int
    link_ids: _containers.RepeatedScalarFieldContainer[str]
    failed: _containers.RepeatedCompositeFieldContainer[LinkFailure]
    duration_ms: int
    recompute_status: str
    recompute_duration_ms: int
    request_id: str
    def __init__(
        self,
        created: int | None = ...,
        link_ids: _Iterable[str] | None = ...,
        failed: _Iterable[LinkFailure | _Mapping] | None = ...,
        duration_ms: int | None = ...,
        recompute_status: str | None = ...,
        recompute_duration_ms: int | None = ...,
        request_id: str | None = ...,
    ) -> None: ...

class LinkFailure(_message.Message):
    __slots__ = ("a_interface_id", "b_interface_id", "error")
    A_INTERFACE_ID_FIELD_NUMBER: _ClassVar[int]
    B_INTERFACE_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    a_interface_id: str
    b_interface_id: str
    error: str
    def __init__(
        self,
        a_interface_id: str | None = ...,
        b_interface_id: str | None = ...,
        error: str | None = ...,
    ) -> None: ...

class ProvisionDevicesRequest(_message.Message):
    __slots__ = ("devices", "skip_recompute", "request_id")
    DEVICES_FIELD_NUMBER: _ClassVar[int]
    SKIP_RECOMPUTE_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    devices: _containers.RepeatedCompositeFieldContainer[DeviceProvision]
    skip_recompute: bool
    request_id: str
    def __init__(
        self,
        devices: _Iterable[DeviceProvision | _Mapping] | None = ...,
        skip_recompute: bool = ...,
        request_id: str | None = ...,
    ) -> None: ...

class DeviceProvision(_message.Message):
    __slots__ = (
        "device_id",
        "parent_id",
        "pon_port",
        "ont_id",
        "tariff_id",
        "mgmt_ip",
        "mgmt_interface",
    )
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    PARENT_ID_FIELD_NUMBER: _ClassVar[int]
    PON_PORT_FIELD_NUMBER: _ClassVar[int]
    ONT_ID_FIELD_NUMBER: _ClassVar[int]
    TARIFF_ID_FIELD_NUMBER: _ClassVar[int]
    MGMT_IP_FIELD_NUMBER: _ClassVar[int]
    MGMT_INTERFACE_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    parent_id: str
    pon_port: int
    ont_id: int
    tariff_id: str
    mgmt_ip: str
    mgmt_interface: str
    def __init__(
        self,
        device_id: str | None = ...,
        parent_id: str | None = ...,
        pon_port: int | None = ...,
        ont_id: int | None = ...,
        tariff_id: str | None = ...,
        mgmt_ip: str | None = ...,
        mgmt_interface: str | None = ...,
    ) -> None: ...

class ProvisionDevicesResponse(_message.Message):
    __slots__ = (
        "provisioned",
        "device_ids",
        "failed",
        "duration_ms",
        "recompute_status",
        "recompute_duration_ms",
        "request_id",
    )
    PROVISIONED_FIELD_NUMBER: _ClassVar[int]
    DEVICE_IDS_FIELD_NUMBER: _ClassVar[int]
    FAILED_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    RECOMPUTE_STATUS_FIELD_NUMBER: _ClassVar[int]
    RECOMPUTE_DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    provisioned: int
    device_ids: _containers.RepeatedScalarFieldContainer[str]
    failed: _containers.RepeatedCompositeFieldContainer[DeviceFailure]
    duration_ms: int
    recompute_status: str
    recompute_duration_ms: int
    request_id: str
    def __init__(
        self,
        provisioned: int | None = ...,
        device_ids: _Iterable[str] | None = ...,
        failed: _Iterable[DeviceFailure | _Mapping] | None = ...,
        duration_ms: int | None = ...,
        recompute_status: str | None = ...,
        recompute_duration_ms: int | None = ...,
        request_id: str | None = ...,
    ) -> None: ...

class DeviceFailure(_message.Message):
    __slots__ = ("device_id", "error")
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    error: str
    def __init__(self, device_id: str | None = ..., error: str | None = ...) -> None: ...

class DeleteLinksRequest(_message.Message):
    __slots__ = ("link_ids", "skip_recompute", "request_id")
    LINK_IDS_FIELD_NUMBER: _ClassVar[int]
    SKIP_RECOMPUTE_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    link_ids: _containers.RepeatedScalarFieldContainer[str]
    skip_recompute: bool
    request_id: str
    def __init__(
        self,
        link_ids: _Iterable[str] | None = ...,
        skip_recompute: bool = ...,
        request_id: str | None = ...,
    ) -> None: ...

class DeleteLinksResponse(_message.Message):
    __slots__ = ("deleted", "link_ids", "failed", "duration_ms", "recompute_status", "request_id")
    DELETED_FIELD_NUMBER: _ClassVar[int]
    LINK_IDS_FIELD_NUMBER: _ClassVar[int]
    FAILED_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    RECOMPUTE_STATUS_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    deleted: int
    link_ids: _containers.RepeatedScalarFieldContainer[str]
    failed: _containers.RepeatedCompositeFieldContainer[DeleteFailure]
    duration_ms: int
    recompute_status: str
    request_id: str
    def __init__(
        self,
        deleted: int | None = ...,
        link_ids: _Iterable[str] | None = ...,
        failed: _Iterable[DeleteFailure | _Mapping] | None = ...,
        duration_ms: int | None = ...,
        recompute_status: str | None = ...,
        request_id: str | None = ...,
    ) -> None: ...

class DeleteFailure(_message.Message):
    __slots__ = ("link_id", "error")
    LINK_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    link_id: str
    error: str
    def __init__(self, link_id: str | None = ..., error: str | None = ...) -> None: ...

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
        "last_operation_timestamp",
        "total_operations",
    )
    STATUS_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    UPTIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    DB_STATUS_FIELD_NUMBER: _ClassVar[int]
    LAST_OPERATION_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    TOTAL_OPERATIONS_FIELD_NUMBER: _ClassVar[int]
    status: str
    version: str
    uptime_seconds: int
    db_status: str
    last_operation_timestamp: int
    total_operations: int
    def __init__(
        self,
        status: str | None = ...,
        version: str | None = ...,
        uptime_seconds: int | None = ...,
        db_status: str | None = ...,
        last_operation_timestamp: int | None = ...,
        total_operations: int | None = ...,
    ) -> None: ...
