import asyncio
import logging
import uuid
import json

from typing import Optional, Dict, Any, List, TYPE_CHECKING


if TYPE_CHECKING:
    from .broker import Broker


from .utils import now
from .packets import (
    PacketDisconnect,
    PacketHeartbeat,
    PacketInfo,
    PacketRequest,
    PacketResponse,
    DataType,
)
from .data import NodeInfo, Registry, ServiceInfo, ActionInfo, ClientInfo
from .redis_transport import RedisTransport
from .transit import Transit
from .service import BaseService

logger = logging.getLogger("broker")


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
        self._pending_responses: Dict[str, asyncio.Future] = {}

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

        asyncio.create_task(self.transit.send_info())

    async def call(
        self,
        action: str,
        params: Any,
        meta: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        node_id: str | None = None,
    ):
        """Call an action on the network (send REQ packet, await RES)."""

        # 1. Find a remote node that has the action
        target_node_id = node_id
        if target_node_id is None:
            found = self._registry.find_remote_action(action)
            if not found:
                raise RuntimeError(f"No remote node found for action '{action}'")
            target_node_id, action_info = found

        # 2. Prepare params
        if isinstance(params, (dict, list, str, int, float, bool, type(None))):
            params_bytes: Any = params
            params_type = DataType.JSON
        else:
            params_bytes = params
            params_type = DataType.BUFFER

        # 3. Create request id and PacketRequest
        req_id = str(uuid.uuid4())
        packet = PacketRequest(
            ver="4",
            sender=self.node_id,
            id=req_id,
            action=action,
            params=params_bytes,
            paramsType=params_type,
            meta=json.dumps(meta) if meta else None,
            timeout=timeout,
        )

        # 4. Register a future for the response
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending_responses[req_id] = fut

        # 5. Send the request
        await self.transit.send_request(target_node_id, packet)

        logger.debug(f"-> {target_node_id}.{action} req_id={req_id}")

        # 6. Wait for the response or timeout
        try:
            if timeout:
                done, pending = await asyncio.wait(
                    [fut], timeout=timeout / 1000, return_when=asyncio.FIRST_COMPLETED
                )
                if not done:
                    self._pending_responses.pop(req_id, None)
                    raise RuntimeError("Request timeout")
                result = fut.result()
            else:
                result = await fut
        finally:
            self._pending_responses.pop(req_id, None)

        if not result.success:
            raise RuntimeError(f"Remote error: {result.error}")
        return result.data

    # Add a handler for incoming PacketResponse
    def _handle_response(self, packet: PacketResponse):
        logger.debug(f"<- req_id={packet.id}")
        fut = self._pending_responses.get(packet.id)
        if fut and not fut.done():
            fut.set_result(packet)

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

    async def _handle_incoming_request(self, packet: PacketRequest) -> None:
        """Handle an incoming action request packet asynchronously and send a response."""

        action_name = packet.action
        handler = None
        for service in self._services.values():
            handler = service.get_action(action_name)
            if handler:
                break
        if not handler:
            response = PacketResponse(
                ver=packet.ver,
                sender=self.node_id,
                id=packet.id,
                success=False,
                error=f"Action '{action_name}' not found on this node.",
            )
            await self.transit.send_response(packet.sender, response)
            return
        params = None
        if packet.params is not None:
            try:
                if packet.paramsType == DataType.JSON and isinstance(
                    packet.params, str
                ):
                    params = json.loads(packet.params)
                elif packet.paramsType == DataType.BUFFER:
                    params = packet.params
                else:
                    params = packet.params
            except Exception as e:
                response = PacketResponse(
                    ver=packet.ver,
                    sender=self.node_id,
                    id=packet.id,
                    success=False,
                    error=f"Failed to decode params: {e}",
                )
                await self.transit.send_response(packet.sender, response)
                return

        async def handle_and_respond():
            try:
                if params is not None:
                    result = await handler(params)
                else:
                    result = await handler()
                if isinstance(result, (dict, list, str, int, float, bool, type(None))):
                    data_type = DataType.JSON
                else:
                    data_type = DataType.BUFFER
                response = PacketResponse(
                    ver=packet.ver,
                    sender=self.node_id,
                    id=packet.id,
                    success=True,
                    data=result,
                    dataType=data_type,
                )
            except Exception as e:
                logger.exception(f"Error while handling action '{action_name}'")
                response = PacketResponse(
                    ver=packet.ver,
                    sender=self.node_id,
                    id=packet.id,
                    success=False,
                    error=str(e),
                )
            await self.transit.send_response(packet.sender, response)

        asyncio.create_task(handle_and_respond())

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
