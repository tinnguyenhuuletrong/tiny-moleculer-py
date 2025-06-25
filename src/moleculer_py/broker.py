import asyncio
import logging
import uuid

from typing import Optional, Dict, Any, List, TYPE_CHECKING


if TYPE_CHECKING:
    from .broker import Broker


from .utils import now
from .packets import PacketDisconnect, PacketHeartbeat, PacketInfo
from .data import NodeInfo, Registry, ServiceInfo, ActionInfo, ClientInfo
from .redis_transport import RedisTransport
from .transit import Transit
from .service import BaseService

logger = logging.getLogger("Broker")


class Broker:
    """
    Moleculer-compatible Service Broker (Python).
    Handles node lifecycle, service registry, and action/event routing.
    Delegates all network/transport logic to Transit.
    """

    def __init__(
        self,
        node_id: str,
        instance_id: str = str(uuid.uuid4()),
        redis_url: str = "redis://localhost:6379/0",
        cfg_node_ping_timeout_ms: int = 20000,
    ):
        self.node_id = node_id
        self.instance_id = instance_id
        self.transport = RedisTransport(redis_url=redis_url, node_id=node_id)
        self.transit = Transit(self, self.transport)
        self.cfg_node_ping_timeout_ms = cfg_node_ping_timeout_ms
        self.meta_services: Dict[str, ServiceInfo] = {}
        self._services: Dict[str, BaseService] = {}
        self.info_seq = 1
        self.cached_serializable_services = []
        self._registry: Registry = Registry({})

    async def start(self):
        """Start the broker: connect transit (which handles transport, subscribe, announce presence, heartbeat)."""
        await self.transit.connect()
        logger.info(f"Broker {self.node_id} started.")

    async def stop(self):
        """Stop the broker: send disconnect, stop heartbeat, disconnect transport."""
        await self.transit.disconnect()
        logger.info(f"Broker {self.node_id} stopped.")

    def register_service(
        self, name: str, service_ins: BaseService, service_def: Dict[str, Any]
    ):
        """Register a service (actions/events)."""
        tmp = ServiceInfo.from_dict(service_def)
        self.meta_services[name] = tmp
        self._services[name] = service_ins
        self.info_seq += 1
        self._build_serialize_service()

        asyncio.create_task(self.transit._send_info())

    async def call(
        self,
        action: str,
        params: Any,
        meta: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ):
        """Call an action on the network (send REQ packet, await RES)."""
        # TODO: Implement action call logic
        pass

    async def emit(
        self,
        event: str,
        data: Any,
        groups: Optional[list] = None,
        broadcast: bool = True,
    ):
        """Emit an event to the network (send EVENT packet)."""
        # TODO: Implement event emit logic
        pass

    def get_registry(self):
        self._refresh_node_online_status()
        return self._registry

    def get_services(self):
        return self._services

    def _handle_packet_info(self, info: PacketInfo):
        # Convert PacketInfo.services (list of dicts) to List[ServiceInfo]
        services = []
        for svc in info.services:
            # Convert actions dict
            actions = {}
            for act_name, act in svc.get("actions", {}).items():
                # act may be a dict with at least 'name', possibly more
                actions[act_name] = ActionInfo(
                    cache=act.get("cache", False),
                    tracing=act.get("tracing", False),
                    rawName=act.get("rawName", act_name),
                    name=act.get("name", act_name),
                    params=act.get("params", {}),
                )
            # Events can be left as-is (dict)
            events = svc.get("events", {})
            name = svc.get("name") or ""
            fullName = svc.get("fullName") or name
            services.append(
                ServiceInfo(
                    name=name,
                    fullName=fullName,
                    settings=svc.get("settings", {}),
                    metadata=svc.get("metadata", {}),
                    actions=actions,
                    events=events,
                )
            )
        # Convert client
        if info.client:
            tmp: Any = info.client
            client = ClientInfo(
                type=tmp["type"],
                version=tmp["version"],
                langVersion=tmp["langVersion"],
            )
        else:
            client = ClientInfo(type="unknown", version="", langVersion="")
        # Build NodeInfo
        node_info = NodeInfo(
            nodeId=info.sender,
            ipList=info.ipList,
            hostname=info.hostname or "",
            instanceID=info.instanceID or "",
            client=client,
            config=info.config,
            port=None,  # Not present in PacketInfo
            seq=info.seq or 0,
            metadata=info.metadata,
            services=services,
            lastPing=now(),
            isOnline=True,
            isLocal=info.sender == self.node_id,
        )

        if info.sender not in self._registry.nodes:
            logger.info(f"Node '{info.sender}' connected.")
            pass
        self._registry.nodes[info.sender] = node_info

    def _handle_heart_beat(self, packet: PacketHeartbeat):
        now_ms = now()
        sender = packet.sender
        node = self._registry.nodes.get(sender)
        if node:
            node.lastPing = now_ms
            if not node.isOnline:
                logger.info(f"Node '{sender}' is back online.")
            node.isOnline = True

    def _handle_disconnect(self, packet: PacketDisconnect):
        now_ms = now()
        sender = packet.sender
        node = self._registry.nodes.get(sender)
        if node:
            node.lastPing = now_ms
            if not node.isOnline:
                logger.info(f"Node '{sender}' disconnected.")
            node.isOnline = False

    def _refresh_node_online_status(self):
        now_ms = now()
        # Check all nodes for offline status
        for node_id, node in self._registry.nodes.items():
            # Ignore local node
            if node_id == self.node_id:
                continue

            if node.isOnline and (
                now_ms - node.lastPing > self.cfg_node_ping_timeout_ms
            ):
                node.isOnline = False
                logger.info(
                    f"Node '{node_id}' marked as offline (lastPing {node.lastPing}, now {now_ms})."
                )

    def _build_serialize_service(self):
        serializable_services = []
        for name, service_def in self.meta_services.items():
            actions = {
                k: {"name": k, "params": action.params, "rawName": k}
                for [k, action] in service_def.actions.items()
            }
            events = {
                event_name: {"name": event_name} for event_name in service_def.events
            }
            serializable_services.append(
                {
                    "name": name,
                    "fullName": name,
                    "version": service_def.version,
                    "settings": service_def.settings,
                    "metadata": service_def.metadata,
                    "actions": actions,
                    "events": events,
                }
            )
        self.cached_serializable_services = serializable_services
