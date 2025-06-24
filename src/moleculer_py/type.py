import dataclasses
from dataclasses_json import DataClassJsonMixin
from typing import List, Dict, Any, Optional


@dataclasses.dataclass
class ClientInfo(DataClassJsonMixin):
    """Represents the client information."""

    type: str
    version: str
    langVersion: str


@dataclasses.dataclass
class RuleInfo(DataClassJsonMixin):
    """Represents a validation rule within a parameter."""

    type: str


@dataclasses.dataclass
class ActionInfo(DataClassJsonMixin):
    """Represents a specific action within a service."""

    cache: bool
    tracing: bool
    rawName: str
    name: str
    params: Optional[Dict[str, Any]] = None  # Can be empty


@dataclasses.dataclass
class ServiceInfo(DataClassJsonMixin):
    """Represents a service running on the node."""

    name: str
    fullName: str
    settings: Dict[str, Any]  # Empty dict in example
    metadata: Dict[str, Any]  # Empty dict in example
    actions: Dict[str, ActionInfo]
    events: Dict[str, Any]  # Empty dict in example


@dataclasses.dataclass
class NodeInfo(DataClassJsonMixin):
    """The main dataclass representing the entire node information."""

    nodeId: str
    ipList: List[str]
    hostname: str
    instanceID: str
    client: ClientInfo
    config: Dict[str, Any]  # Empty dict in example
    port: Optional[int]  # Can be null
    seq: int
    metadata: Dict[str, Any]  # Empty dict in example
    services: List[ServiceInfo]


@dataclasses.dataclass
class Registry(DataClassJsonMixin):
    nodes: Dict[str, NodeInfo]
