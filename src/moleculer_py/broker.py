import asyncio
from dataclasses import asdict
import uuid
from typing import Optional, Dict, Any, List

from .packets import PacketInfo

from .type import NodeInfo, Registry, ServiceInfo, ActionInfo, ClientInfo
from .redis_transport import RedisTransport
from .transit import Transit


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
    ):
        self.node_id = node_id
        self.instance_id = instance_id
        self.transport = RedisTransport(redis_url=redis_url, node_id=node_id)
        self.transit = Transit(self, self.transport)
        self.services = {}  # service_name -> service definition (placeholder)
        self._event_loop = asyncio.get_event_loop()
        self.info_seq = 1
        self.cached_serializable_services = []
        self.registry: Registry = Registry({})

    async def start(self):
        """Start the broker: connect transit (which handles transport, subscribe, announce presence, heartbeat)."""
        await self.transit.connect()
        print(f"Broker {self.node_id} started.")

    async def stop(self):
        """Stop the broker: send disconnect, stop heartbeat, disconnect transport."""
        await self.transit.disconnect()
        print(f"Broker {self.node_id} stopped.")

    async def register_service(self, name: str, service_def: Dict[str, Any]):
        """Register a service (actions/events)."""
        self.services[name] = service_def
        self.info_seq += 1
        self._build_serialize_service()
        await self.transit.send_info()

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

    def _update_registry(self, info: PacketInfo):
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
        )

        self.registry.nodes[info.sender] = node_info

    def _build_serialize_service(self):
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
            serializable_services.append(
                {
                    "name": name,
                    "fullName": name,
                    "version": service_def.get("version"),
                    "settings": service_def.get("settings", {}),
                    "metadata": service_def.get("metadata", {}),
                    "actions": actions,
                    "events": events,
                }
            )
        self.cached_serializable_services = serializable_services
