from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from enum import IntEnum


class DataType(IntEnum):
    UNDEFINED = 0
    NULL = 1
    JSON = 2
    BUFFER = 3


@dataclass
class PacketEvent:
    ver: str
    sender: str
    id: str
    event: str
    data: Optional[bytes] = None
    dataType: DataType = DataType.UNDEFINED
    groups: List[str] = field(default_factory=list)
    meta: Optional[str] = None
    broadcast: Optional[bool] = None
    level: Optional[int] = None
    tracing: Optional[bool] = None
    parentID: Optional[str] = None
    requestID: Optional[str] = None
    stream: Optional[bool] = None
    seq: Optional[int] = None
    caller: Optional[str] = None
    needAck: Optional[bool] = None


@dataclass
class PacketRequest:
    ver: str
    sender: str
    id: str
    action: str
    params: Optional[bytes] = None
    paramsType: DataType = DataType.UNDEFINED
    meta: Optional[str] = None
    timeout: Optional[float] = None
    level: Optional[int] = None
    tracing: Optional[bool] = None
    parentID: Optional[str] = None
    requestID: Optional[str] = None
    stream: Optional[bool] = None
    seq: Optional[int] = None
    caller: Optional[str] = None


@dataclass
class PacketResponse:
    ver: str
    sender: str
    id: str
    success: bool
    data: Optional[Any] = None
    dataType: DataType = DataType.UNDEFINED
    error: Optional[str] = None
    meta: Optional[str] = None
    stream: Optional[bool] = None
    seq: Optional[int] = None


@dataclass
class PacketDiscover:
    ver: str
    sender: str


@dataclass
class PacketInfo:
    @dataclass
    class Client:
        type: str
        version: str
        langVersion: str

    ver: str
    sender: str
    services: List[Dict[str, Any]] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    ipList: List[str] = field(default_factory=list)
    hostname: Optional[str] = None
    client: Optional["PacketInfo.Client"] = None
    seq: Optional[int] = None
    instanceID: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PacketDisconnect:
    ver: str
    sender: str


@dataclass
class PacketHeartbeat:
    ver: str
    sender: str
    cpu: Optional[float] = None


@dataclass
class PacketPing:
    ver: str
    sender: str
    time: int
    id: Optional[str] = None


@dataclass
class PacketPong:
    ver: str
    sender: str
    time: int
    arrived: int
    id: Optional[str] = None


@dataclass
class PacketGossipHello:
    ver: str
    sender: str
    host: Optional[str] = None
    port: Optional[int] = None


@dataclass
class PacketGossipRequest:
    ver: str
    sender: str
    online: Optional[str] = None
    offline: Optional[str] = None


@dataclass
class PacketGossipResponse:
    ver: str
    sender: str
    online: Optional[str] = None
    offline: Optional[str] = None


PREFIX_MAP = {
    "MOL.EVENT": PacketEvent,
    "MOL.REQ": PacketRequest,
    "MOL.RES": PacketResponse,
    "MOL.DISCOVER": PacketDiscover,
    "MOL.INFO": PacketInfo,
    "MOL.DISCONNECT": PacketDisconnect,
    "MOL.HEARTBEAT": PacketHeartbeat,
    "MOL.PING": PacketPing,
    "MOL.PONG": PacketPong,
    "MOL.GOSSIP_HELLO": PacketGossipHello,
    "MOL.GOSSIP_REQ": PacketGossipRequest,
    "MOL.GOSSIP_RES": PacketGossipResponse,
}

type TypeAllPacket = Union[
    PacketEvent,
    PacketRequest,
    PacketResponse,
    PacketDiscover,
    PacketInfo,
    PacketDisconnect,
    PacketHeartbeat,
    PacketPing,
    PacketPong,
    PacketGossipHello,
    PacketGossipRequest,
    PacketGossipResponse,
]


def parse_packet_by_type(messageType: str, packet: dict) -> TypeAllPacket:

    matched_cls = None
    for prefix, cls in PREFIX_MAP.items():
        if messageType.startswith(prefix):
            matched_cls = cls
            break
    if matched_cls is not None:
        try:
            return matched_cls(**packet)
        except Exception as e:
            raise ValueError(
                f"Failed to parse packet as {matched_cls.__name__}: {e}\nRaw: {packet}"
            )
    else:
        raise ValueError(f"Unknown messageType prefix: {messageType}")


def build_subscribe_channels(node_id: str) -> List[str]:
    return [
        f"MOL.REQ.{node_id}",
        "MOL.REQ",
        f"MOL.RES.{node_id}",
        "MOL.EVENT",
        f"MOL.EVENT.{node_id}",
        "MOL.INFO",
        f"MOL.INFO.{node_id}",
        "MOL.DISCOVER",
        f"MOL.DISCOVER.{node_id}",
        "MOL.HEARTBEAT",
        "MOL.PING",
        f"MOL.PING.{node_id}",
        "MOL.PONG",
        f"MOL.PONG.{node_id}",
    ]
