from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

class DataType(Enum):
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
    data: Optional[bytes] = None
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
    services: Optional[str] = None
    config: Optional[str] = None
    ipList: List[str] = field(default_factory=list)
    hostname: Optional[str] = None
    client: Optional[Client] = None
    seq: Optional[int] = None
    instanceID: Optional[str] = None
    metadata: Optional[str] = None

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