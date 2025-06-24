import dataclasses
from dataclasses_json import DataClassJsonMixin
from typing import List, Dict, Any, Optional, Tuple


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

    lastPing: int
    isOnline: bool = True
    isLocal: bool = False  # Indicates if this node is the current node


@dataclasses.dataclass
class Registry(DataClassJsonMixin):
    nodes: Dict[str, NodeInfo]

    def find_remote_action(self, action_name: str) -> Optional[Tuple[str, ActionInfo]]:
        for node_id, node in self.nodes.items():
            if not node.isOnline:
                continue
            for service in node.services:
                for action in service.actions.values():
                    if action.name == action_name:
                        return node_id, action
        return None
