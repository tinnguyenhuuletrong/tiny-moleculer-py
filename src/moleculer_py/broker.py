import asyncio
import json
import socket
import uuid
from typing import List, Optional, Dict, Any, Callable
from .redis_transport import RedisTransport
from .packets import (
    PacketEvent, PacketRequest, PacketResponse, PacketDiscover, PacketInfo, PacketDisconnect, PacketHeartbeat, PacketPing, PacketPong, PacketGossipHello, PacketGossipRequest, PacketGossipResponse, DataType
)
from dataclasses import asdict

class Broker:
    """
    Moleculer-compatible Service Broker (Python).
    Handles node lifecycle, transport, service registry, and action/event routing.
    """
    def __init__(self, node_id: str, redis_url: str = 'redis://localhost:6379/0'):
        self.node_id = node_id
        self.transport = RedisTransport(redis_url=redis_url, node_id=node_id)
        self.services = {}  # service_name -> service definition (placeholder)
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._info_task: Optional[asyncio.Task] = None
        self._event_loop = asyncio.get_event_loop()

    async def start(self):
        """Start the broker: connect transport, subscribe, announce presence, start heartbeat."""
        await self.transport.connect()
        await self.subscribe_channels()
        await self.send_info()
        await self.send_discover()
        self._running = True
        self._heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        print(f"Broker {self.node_id} started.")

    async def stop(self):
        """Stop the broker: send disconnect, stop heartbeat, disconnect transport."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        await self.send_disconnect()
        await self.transport.close()
        print(f"Broker {self.node_id} stopped.")

    async def subscribe_channels(self):
        """Subscribe to Moleculer channels relevant to this node."""
        channels = [
            'MOL.REQ',
            f'MOL.RES.{self.node_id}',
            'MOL.EVENT',
            f'MOL.EVENT.{self.node_id}',
            'MOL.INFO',
            f'MOL.INFO.{self.node_id}',
            'MOL.DISCOVER',
            'MOL.HEARTBEAT',
            'MOL.PING',
            'MOL.PONG'
        ]
        await self.transport.subscribe(channels)
        # Register handlers for incoming packets (placeholders)
        for ch in channels:
            self.transport.register_handler(ch, self.handle_packet)

    async def handle_packet(self, packet: Dict[str, Any]):
        """Handle incoming packets (to be implemented: action/event/heartbeat/etc)."""
        print(f"[Broker] Received packet: {packet}")
        # TODO: Dispatch to action/event/heartbeat handlers

    async def send_info(self):
        """Send node INFO packet to the network."""
        serializable_services = []
        for name, service_def in self.services.items():
            actions = {
                action_name: {"name": action_name}
                for action_name in service_def.get("actions", {})
            }
            events = {
                event_name: {"name": event_name}
                for event_name in service_def.get("events", {})
            }
            serializable_services.append({
                "name": name,
                "version": service_def.get("version"),
                "settings": service_def.get("settings", {}),
                "metadata": service_def.get("metadata", {}),
                "actions": actions,
                "events": events,
                "nodeID": self.node_id
            })


        ip_list = self.get_local_ip_addresses()
        instance_id = str(uuid.uuid4())

        info = PacketInfo(
            ver="4",
            sender=self.node_id,
            services=serializable_services,
            hostname=socket.gethostname(),
            ipList=ip_list,
            instanceID=instance_id,
            client=PacketInfo.Client(
                type="python",
                version="0.14.33",
                langVersion=""
            )
        )
        await self.transport.publish('MOL.INFO', asdict(info))

    async def send_discover(self):
        """Send DISCOVER packet to the network."""
        discover = PacketDiscover(ver="4", sender=self.node_id)
        await self.transport.publish('MOL.DISCOVER', discover.__dict__)

    async def send_disconnect(self):
        """Send DISCONNECT packet to the network."""
        disconnect = PacketDisconnect(ver="4", sender=self.node_id)
        await self.transport.publish('MOL.DISCONNECT', disconnect.__dict__)

    async def heartbeat_loop(self):
        """Periodically send HEARTBEAT packets."""
        while self._running:
            heartbeat = PacketHeartbeat(ver="4", sender=self.node_id, cpu=None)
            await self.transport.publish('MOL.HEARTBEAT', heartbeat.__dict__)
            await asyncio.sleep(5)

    # --- Service registration and action/event call/emit (placeholders) ---
    async def register_service(self, name: str, service_def: Dict[str, Any]):
        """Register a service (actions/events)."""
        self.services[name] = service_def
        await self.send_info()

    async def call(self, action: str, params: Any, meta: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None):
        """Call an action on the network (send REQ packet, await RES)."""
        # TODO: Implement action call logic
        pass

    async def emit(self, event: str, data: Any, groups: Optional[list] = None, broadcast: bool = True):
        """Emit an event to the network (send EVENT packet)."""
        # TODO: Implement event emit logic
        pass 

    
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