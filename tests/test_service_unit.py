from typing import Any
import pytest
import asyncio
from unittest.mock import MagicMock, patch
import json

import sys
import types

# Import BaseService and action from the correct path
from moleculer_py.data import ServiceInfo, Registry, NodeInfo, ActionInfo, ClientInfo
from moleculer_py.service import BaseService, action, event
from moleculer_py.broker import Broker
from moleculer_py.packets import PacketRequest, DataType, PacketResponse, PacketEvent


async def dummy(target_node_id: str | None = None):
    pass


@pytest.mark.asyncio
async def test_action_decorator_and_registration():
    broker = Broker("")
    broker.transit.send_info = dummy

    class MyService(BaseService):
        @action(params={"name": {"type": "string", "default": "World"}})
        async def hello(self, ctx):
            return {"message": f"Hello, {ctx['params'].get('name', 'World')}!"}

        @action(
            name="math.add",
            cache=True,
            params={"a": {"type": "number"}, "b": {"type": "number"}},
        )
        async def add(self, ctx):
            a = ctx["params"].get("a", 0)
            b = ctx["params"].get("b", 0)
            return {"result": a + b}

    service = MyService(broker, name="test-service")

    print(broker.meta_services)

    # Check that actions are registered
    assert "test-service.hello" in service.actions
    assert "test-service.math.add" in service.actions
    # Check action metadata
    hello_action = service.actions["test-service.hello"]
    add_action = service.actions["test-service.math.add"]
    assert hello_action["params"] == {"name": {"type": "string", "default": "World"}}
    assert add_action["cache"] is True
    assert add_action["params"] == {"a": {"type": "number"}, "b": {"type": "number"}}
    # Check that the broker received the correct service definition
    itm = broker.meta_services.get("test-service")
    assert itm != None
    reg_service_def: Any = itm.to_dict()
    assert reg_service_def["name"] == "test-service"
    assert "actions" in reg_service_def
    assert "test-service.hello" in reg_service_def["actions"]
    assert "test-service.math.add" in reg_service_def["actions"]
    # The handler should not be in the broker's service definition
    assert "handler" not in reg_service_def["actions"]["test-service.hello"]
    # Test that get_action returns the correct coroutine
    hello_fn = service.get_action("test-service.hello")
    add_fn = service.get_action("test-service.math.add")
    assert asyncio.iscoroutinefunction(hello_fn)
    assert asyncio.iscoroutinefunction(add_fn)
    # Test calling the actions
    result_hello = await hello_fn({"params": {"name": "Alice"}})
    assert result_hello == {"message": "Hello, Alice!"}
    result_add = await add_fn({"params": {"a": 2, "b": 3}})
    assert result_add == {"result": 5}


@pytest.mark.asyncio
async def test_broker_handles_multiple_concurrent_requests(monkeypatch):
    broker = Broker("")
    broker.transit.send_info = dummy
    responses = []

    class MyService(BaseService):
        @action()
        async def echo(self, ctx):
            await asyncio.sleep(0.05)  # Simulate work
            return {"echo": ctx["n"]}

    MyService(broker, name="svc")

    # Patch send_response to capture responses
    async def capture_send_response_packet(message_type, packet):
        responses.append((message_type, packet))

    monkeypatch.setattr(broker.transit, "send_response", capture_send_response_packet)

    # Create multiple requests
    reqs = [
        PacketRequest(
            ver="4",
            sender="remote",
            id=f"req{i}",
            action="svc.echo",
            params=json.dumps({"n": i}),
            paramsType=DataType.JSON,
        )
        for i in range(10)
    ]

    # Fire all requests concurrently
    await asyncio.gather(*(broker._handle_incoming_request(req) for req in reqs))

    # Wait a bit for all responses to be processed
    await asyncio.sleep(0.1)

    # Check all responses
    assert len(responses) == 10
    ids = set()
    for message_type, packet in responses:
        assert message_type == "remote"
        assert isinstance(packet, PacketResponse)
        assert packet.success is True
        assert packet.data is not None
        assert "echo" in packet.data
        ids.add(packet.id)
    assert ids == {f"req{i}" for i in range(10)}


@pytest.mark.asyncio
async def test_broker_call_success(monkeypatch):
    broker = Broker("local")
    # Simulate a remote node with the action
    action_name = "svc.hello"
    remote_node_id = "remote1"
    broker._registry = Registry(
        nodes={
            remote_node_id: NodeInfo(
                nodeId=remote_node_id,
                ipList=["127.0.0.1"],
                hostname="host",
                instanceID="inst",
                client=ClientInfo(type="py", version="1.0", langVersion="3.10"),
                config={},
                port=None,
                seq=1,
                metadata={},
                services=[
                    ServiceInfo(
                        name="svc",
                        fullName="svc",
                        settings={},
                        metadata={},
                        actions={
                            action_name: ActionInfo(
                                rawName=action_name,
                                name=action_name,
                                params={},
                            )
                        },
                        events={},
                    )
                ],
                lastPing=123,
                isOnline=True,
                isLocal=False,
            )
        }
    )

    # Patch send_request to simulate immediate response
    async def fake_send_packet(channel, packet):
        # Simulate network: immediately respond
        resp = PacketResponse(
            ver="4",
            sender=remote_node_id,
            id=packet.id,
            success=True,
            data={"msg": "hi"},
            dataType=DataType.JSON,
        )
        broker._handle_response(resp)

    monkeypatch.setattr(broker.transit, "send_request", fake_send_packet)
    result = await broker.call(action_name, {"foo": "bar"})
    assert result == {"msg": "hi"}


@pytest.mark.asyncio
async def test_broker_call_timeout(monkeypatch):
    broker = Broker("local")
    action_name = "svc.hello"
    remote_node_id = "remote1"
    broker._registry = Registry(
        nodes={
            remote_node_id: NodeInfo(
                nodeId=remote_node_id,
                ipList=["127.0.0.1"],
                hostname="host",
                instanceID="inst",
                client=ClientInfo(type="py", version="1.0", langVersion="3.10"),
                config={},
                port=None,
                seq=1,
                metadata={},
                services=[
                    ServiceInfo(
                        name="svc",
                        fullName="svc",
                        settings={},
                        metadata={},
                        actions={
                            action_name: ActionInfo(
                                rawName=action_name,
                                name=action_name,
                                params={},
                            )
                        },
                        events={},
                    )
                ],
                lastPing=123,
                isOnline=True,
                isLocal=False,
            )
        }
    )

    # Patch send_request to do nothing (simulate no response)
    async def fake_send_packet(channel, packet):
        pass

    monkeypatch.setattr(broker.transit, "send_request", fake_send_packet)
    with pytest.raises(RuntimeError, match="Request timeout"):
        await broker.call(action_name, {"foo": "bar"}, timeout=10)  # 10 ms


@pytest.mark.asyncio
async def test_broker_call_remote_error(monkeypatch):
    broker = Broker("local")
    action_name = "svc.hello"
    remote_node_id = "remote1"
    broker._registry = Registry(
        nodes={
            remote_node_id: NodeInfo(
                nodeId=remote_node_id,
                ipList=["127.0.0.1"],
                hostname="host",
                instanceID="inst",
                client=ClientInfo(type="py", version="1.0", langVersion="3.10"),
                config={},
                port=None,
                seq=1,
                metadata={},
                services=[
                    ServiceInfo(
                        name="svc",
                        fullName="svc",
                        settings={},
                        metadata={},
                        actions={
                            action_name: ActionInfo(
                                rawName=action_name,
                                name=action_name,
                                params={},
                            )
                        },
                        events={},
                    )
                ],
                lastPing=123,
                isOnline=True,
                isLocal=False,
            )
        }
    )

    # Patch send_request to simulate remote error response
    async def fake_send_packet(channel, packet):
        resp = PacketResponse(
            ver="4",
            sender=remote_node_id,
            id=packet.id,
            success=False,
            error="Something went wrong",
            dataType=DataType.JSON,
        )
        broker._handle_response(resp)

    monkeypatch.setattr(broker.transit, "send_request", fake_send_packet)
    with pytest.raises(RuntimeError, match="Something went wrong"):
        await broker.call(action_name, {"foo": "bar"})


@pytest.mark.asyncio
async def test_broker_call_multiple_concurrent(monkeypatch):
    broker = Broker("local")
    action_name = "svc.hello"
    remote_node_id = "remote1"
    broker._registry = Registry(
        nodes={
            remote_node_id: NodeInfo(
                nodeId=remote_node_id,
                ipList=["127.0.0.1"],
                hostname="host",
                instanceID="inst",
                client=ClientInfo(type="py", version="1.0", langVersion="3.10"),
                config={},
                port=None,
                seq=1,
                metadata={},
                services=[
                    ServiceInfo(
                        name="svc",
                        fullName="svc",
                        settings={},
                        metadata={},
                        actions={
                            action_name: ActionInfo(
                                rawName=action_name,
                                name=action_name,
                                params={},
                            )
                        },
                        events={},
                    )
                ],
                lastPing=123,
                isOnline=True,
                isLocal=False,
            )
        }
    )

    # Patch send_request to respond to each call with the correct id and data
    async def fake_send_packet(channel, packet):
        # Simulate network: respond after a small delay, with unique data per call
        await asyncio.sleep(0.01)
        resp = PacketResponse(
            ver="4",
            sender=remote_node_id,
            id=packet.id,
            success=True,
            data={"msg": packet.params},
            dataType=DataType.JSON,
        )
        broker._handle_response(resp)

    monkeypatch.setattr(broker.transit, "send_request", fake_send_packet)
    # Fire multiple calls concurrently
    payloads = [{"foo": f"bar{i}"} for i in range(5)]
    results = await asyncio.gather(
        *[broker.call(action_name, payload) for payload in payloads]
    )
    # Each result should match the corresponding payload
    for i, result in enumerate(results):
        assert result["msg"] == payloads[i]


@pytest.mark.asyncio
async def test_broker_handle_incoming_event(monkeypatch):
    broker = Broker("")
    broker.transit.send_info = dummy
    called = {}
    errors = {}

    class MyService(BaseService):
        @action()
        async def dummy_action(self, ctx):
            return "ok"

        @staticmethod
        def reset():
            called.clear()
            errors.clear()

        @event("test.event")
        async def handle_event(self, data):
            called["event"] = data

        @event("test.error")
        async def handle_error(self, data):
            errors["error"] = True
            raise Exception("handler error")

    service = MyService(broker, name="svc")
    MyService.reset()

    # Test normal event
    event_data = {"foo": "bar"}
    packet = PacketEvent(
        ver="4",
        sender="remote",
        id="evt1",
        event="test.event",
        data=json.dumps(event_data),
        dataType=DataType.JSON,
    )
    broker._handle_incoming_event(packet)
    await asyncio.sleep(0.05)  # Let the event handler run
    assert called["event"] == event_data

    # Test error isolation: one handler throws, others still run
    packet2 = PacketEvent(
        ver="4",
        sender="remote",
        id="evt2",
        event="test.error",
        data=json.dumps({"fail": True}),
        dataType=DataType.JSON,
    )
    broker._handle_incoming_event(packet2)
    await asyncio.sleep(0.05)
    assert errors["error"] is True

    # Test event with no data
    packet3 = PacketEvent(
        ver="4",
        sender="remote",
        id="evt3",
        event="test.event",
        data=None,
        dataType=DataType.UNDEFINED,
    )
    broker._handle_incoming_event(packet3)
    await asyncio.sleep(0.05)
    # Should call with None
    assert called["event"] is None


def make_node(node_id, lastPing, isOnline=True):
    from moleculer_py.data import NodeInfo, ClientInfo, ServiceInfo

    return NodeInfo(
        nodeId=node_id,
        ipList=["127.0.0.1"],
        hostname="host",
        instanceID="inst",
        client=ClientInfo(type="py", version="1.0", langVersion="3.10"),
        config={},
        port=None,
        seq=1,
        metadata={},
        services=[
            ServiceInfo(
                name="svc",
                fullName="svc",
                settings={},
                metadata={},
                actions={},
                events={},
            )
        ],
        lastPing=lastPing,
        isOnline=isOnline,
        isLocal=False,
    )


@pytest.mark.asyncio
async def test_status_check_loop_marks_and_removes_offline_nodes(monkeypatch):
    broker = Broker("local", cfg_node_ping_timeout_ms=10)
    fake_now = 1000
    monkeypatch.setattr("moleculer_py.utils.now", lambda: fake_now)
    node_id = "remote1"
    broker._registry.nodes[node_id] = make_node(node_id, lastPing=900, isOnline=True)

    # First check: should mark node offline
    broker._refresh_node_online_status()
    assert node_id in broker._registry.nodes
    assert not broker._registry.nodes[node_id].isOnline

    # Second check: should remove node after another cycle
    fake_now = 2000
    broker._refresh_node_online_status()
    assert node_id not in broker._registry.nodes


@pytest.mark.asyncio
async def test_broker_emit(monkeypatch):
    broker = Broker("local")
    broker.transit.send_info = dummy
    sent_events = []

    # Patch send_event to capture calls
    async def fake_send_event(node_id, packet):
        sent_events.append((node_id, packet))

    monkeypatch.setattr(broker.transit, "send_event", fake_send_event)

    # Register a service with an event
    class MyService(BaseService):
        @event("my.event")
        async def handle_event(self, data):
            return data

    MyService(broker, name="svc")

    # Add two remote nodes, both interested in "my.event"
    from moleculer_py.data import NodeInfo, ClientInfo, ServiceInfo

    broker._registry = Registry(
        nodes={
            "remote1": NodeInfo(
                nodeId="remote1",
                ipList=["127.0.0.1"],
                hostname="host1",
                instanceID="inst1",
                client=ClientInfo(type="py", version="1.0", langVersion="3.10"),
                config={},
                port=None,
                seq=1,
                metadata={},
                services=[
                    ServiceInfo(
                        name="svc",
                        fullName="svc",
                        settings={},
                        metadata={},
                        actions={},
                        events={"my.event": {}},
                    )
                ],
                lastPing=123,
                isOnline=True,
                isLocal=False,
            ),
            "remote2": NodeInfo(
                nodeId="remote2",
                ipList=["127.0.0.1"],
                hostname="host2",
                instanceID="inst2",
                client=ClientInfo(type="py", version="1.0", langVersion="3.10"),
                config={},
                port=None,
                seq=1,
                metadata={},
                services=[
                    ServiceInfo(
                        name="svc",
                        fullName="svc",
                        settings={},
                        metadata={},
                        actions={},
                        events={"my.event": {}},
                    )
                ],
                lastPing=124,
                isOnline=True,
                isLocal=False,
            ),
        }
    )

    # Test emit: should send to one of the remote nodes
    sent_events.clear()
    await broker.emit("my.event", {"foo": "bar"})
    assert len(sent_events) == 1
    node_id, packet = sent_events[0]
    assert node_id in ("remote1", "remote2")
    assert packet.event == "my.event"
    assert packet.data == {"foo": "bar"}


@pytest.mark.asyncio
async def test_broker_broadcast(monkeypatch):
    broker = Broker("local")
    broker.transit.send_info = dummy
    sent_events = []

    # Patch send_event to capture calls and simulate error for remote2
    async def fake_send_event(node_id, packet):
        sent_events.append((node_id, packet))
        if node_id == "remote2":
            raise Exception("Simulated send failure")

    monkeypatch.setattr(broker.transit, "send_event", fake_send_event)

    # Register a service with an event
    class MyService(BaseService):
        @event("my.event")
        async def handle_event(self, data):
            return data

    MyService(broker, name="svc")

    # Add two remote nodes, both interested in "my.event"
    from moleculer_py.data import NodeInfo, ClientInfo, ServiceInfo

    broker._registry = Registry(
        nodes={
            "remote1": NodeInfo(
                nodeId="remote1",
                ipList=["127.0.0.1"],
                hostname="host1",
                instanceID="inst1",
                client=ClientInfo(type="py", version="1.0", langVersion="3.10"),
                config={},
                port=None,
                seq=1,
                metadata={},
                services=[
                    ServiceInfo(
                        name="svc",
                        fullName="svc",
                        settings={},
                        metadata={},
                        actions={},
                        events={"my.event": {}},
                    )
                ],
                lastPing=123,
                isOnline=True,
                isLocal=False,
            ),
            "remote2": NodeInfo(
                nodeId="remote2",
                ipList=["127.0.0.1"],
                hostname="host2",
                instanceID="inst2",
                client=ClientInfo(type="py", version="1.0", langVersion="3.10"),
                config={},
                port=None,
                seq=1,
                metadata={},
                services=[
                    ServiceInfo(
                        name="svc",
                        fullName="svc",
                        settings={},
                        metadata={},
                        actions={},
                        events={"my.event": {}},
                    )
                ],
                lastPing=124,
                isOnline=True,
                isLocal=False,
            ),
        }
    )

    # Test broadcast: should send to both nodes, and error in one does not affect the other
    sent_events.clear()
    await broker.broadcast("my.event", {"baz": 123})
    await asyncio.sleep(0.05)
    # Both nodes should be attempted
    sent_node_ids = {node_id for node_id, _ in sent_events}
    assert sent_node_ids == {"remote1", "remote2"}
    for node_id, packet in sent_events:
        assert packet.event == "my.event"
        assert packet.data == {"baz": 123}
    # No exception should be raised by broadcast
    # (errors are logged, not raised)
