from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DeviceRequest(_message.Message):
    __slots__ = ("device_id",)
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    def __init__(self, device_id: _Optional[str] = ...) -> None: ...

class BulkDeviceRequest(_message.Message):
    __slots__ = ("device_ids",)
    DEVICE_IDS_FIELD_NUMBER: _ClassVar[int]
    device_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, device_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class InterfaceSummary(_message.Message):
    __slots__ = ("id", "name", "port_role", "effective_status", "occupancy", "capacity")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PORT_ROLE_FIELD_NUMBER: _ClassVar[int]
    EFFECTIVE_STATUS_FIELD_NUMBER: _ClassVar[int]
    OCCUPANCY_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    port_role: str
    effective_status: str
    occupancy: int
    capacity: int
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., port_role: _Optional[str] = ..., effective_status: _Optional[str] = ..., occupancy: _Optional[int] = ..., capacity: _Optional[int] = ...) -> None: ...

class PortSummaryResponse(_message.Message):
    __slots__ = ("interfaces",)
    INTERFACES_FIELD_NUMBER: _ClassVar[int]
    interfaces: _containers.RepeatedCompositeFieldContainer[InterfaceSummary]
    def __init__(self, interfaces: _Optional[_Iterable[_Union[InterfaceSummary, _Mapping]]] = ...) -> None: ...

class BulkPortSummaryResponse(_message.Message):
    __slots__ = ("summaries",)
    class SummariesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: PortSummaryResponse
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[PortSummaryResponse, _Mapping]] = ...) -> None: ...
    SUMMARIES_FIELD_NUMBER: _ClassVar[int]
    summaries: _containers.MessageMap[str, PortSummaryResponse]
    def __init__(self, summaries: _Optional[_Mapping[str, PortSummaryResponse]] = ...) -> None: ...

class InvalidateCacheRequest(_message.Message):
    __slots__ = ("device_id",)
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    def __init__(self, device_id: _Optional[str] = ...) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("healthy", "cached_devices", "cached_interfaces", "cached_links", "version")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    CACHED_DEVICES_FIELD_NUMBER: _ClassVar[int]
    CACHED_INTERFACES_FIELD_NUMBER: _ClassVar[int]
    CACHED_LINKS_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    cached_devices: int
    cached_interfaces: int
    cached_links: int
    version: str
    def __init__(self, healthy: bool = ..., cached_devices: _Optional[int] = ..., cached_interfaces: _Optional[int] = ..., cached_links: _Optional[int] = ..., version: _Optional[str] = ...) -> None: ...
