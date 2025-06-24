import asyncio
import socket
import logging
from dataclasses import asdict
from typing import Any, Dict, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .broker import Broker

from .redis_transport import RedisTransport

from .packets import (
    TypeAllPacket,
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
    DataType,
    build_subscribe_channels,
    parse_packet_by_type,
)

CLIENT_INFO = PacketInfo.Client(type="python", version="0.14.33", langVersion="")
logger = logging.getLogger("Transit")


class Transit:
    """
    Handles all Moleculer network protocol logic: subscribing, publishing, and handling packets.
    Delegates service/action/event logic to the Broker.
    """

    def __init__(self, broker: "Broker", transport: RedisTransport):
        self.broker = broker
        self.transport = transport
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def connect(self):
        await self.transport.connect()
        await self.subscribe_channels()
        await self.send_discover()
        self._running = True
        self._heartbeat_task = asyncio.create_task(self.heartbeat_loop())

    async def disconnect(self):
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        await self.send_disconnect()
        await self.transport.close()

    async def subscribe_channels(self):
        channels = build_subscribe_channels(self.broker.node_id)

        await self.transport.subscribe(channels)
        for ch in channels:
            self.transport.register_handler(ch, self.handle_packet)

    async def handle_packet(self, message_type: str, packet: Dict[str, Any]):
        try:
            parsed = parse_packet_by_type(message_type, packet)
            logger.debug(f"Recv packet ({type(parsed).__name__})")
            match parsed:

                # Discover -> reply broker info
                case PacketDiscover() as discover:
                    if discover.sender != self.broker.node_id:
                        await self.send_discover(discover.sender)
                        await self.send_info(discover.sender)
                    pass

                case PacketPing() as ping:
                    # TODO: Send Pong
                    pass

                case PacketInfo() as info:
                    self.broker._update_registry(info)
                    pass

                case PacketHeartbeat() as heart_beat:
                    pass

                # Add more cases for other packet types as needed
                # TODO: Call into broker for action/event/heartbeat logic
                case _:
                    pass
        except Exception as e:
            logger.error(f"Failed to parse packet: {e}\nRaw: {packet}")

    async def send_packet(self, message_type: str, packet: TypeAllPacket) -> None:
        logger.debug(f"Send packet ({type(packet).__name__})")
        return await self.transport.publish(message_type, asdict(packet))

    async def send_info(self, target_node_id: str | None = None):

        ip_list = self.get_local_ip_addresses()

        info = PacketInfo(
            ver="4",
            sender=self.broker.node_id,
            services=self.broker.cached_serializable_services,
            hostname=socket.gethostname(),
            ipList=ip_list,
            instanceID=self.broker.instance_id,
            client=CLIENT_INFO,
            seq=self.broker.info_seq,
        )

        message_type = "MOL.INFO"
        if target_node_id != None:
            message_type = f"MOL.INFO.{target_node_id}"
        await self.send_packet(message_type, info)

    async def send_discover(self, target_node_id: str | None = None):
        discover = PacketDiscover(ver="4", sender=self.broker.node_id)
        message_type = "MOL.DISCOVER"
        if target_node_id != None:
            message_type = f"MOL.DISCOVER.{target_node_id}"
        await self.send_packet(message_type, discover)

    async def send_disconnect(self):
        disconnect = PacketDisconnect(ver="4", sender=self.broker.node_id)
        await self.send_packet("MOL.DISCONNECT", disconnect)

    async def heartbeat_loop(self):
        while self._running:
            heartbeat = PacketHeartbeat(ver="4", sender=self.broker.node_id, cpu=None)
            await self.send_packet("MOL.HEARTBEAT", heartbeat)
            await asyncio.sleep(10)

    # Collect all local IP addresses
    def get_local_ip_addresses(self) -> List[str]:
        ip_list = set()
        try:
            hostname = socket.gethostname()
            # Try to get all addresses associated with the hostname
            for addr in socket.getaddrinfo(hostname, None):
                ip = addr[4][0]
                ip_str = str(ip)
                # Filter out localhost and duplicates
                if not ip_str.startswith("127.") and not ip_str.startswith("::1"):
                    ip_list.add(ip_str)
        except Exception:
            pass
        # Always add at least one IP (fallback)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_list.add(s.getsockname()[0])
            s.close()
        except Exception:
            pass
        return list(ip_list) if ip_list else ["127.0.0.1"]
