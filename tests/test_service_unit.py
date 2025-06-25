from typing import Any
import pytest
import asyncio
from unittest.mock import MagicMock
import json

import sys
import types

# Import BaseService and action from the correct path
from moleculer_py.data import ServiceInfo, Registry, NodeInfo, ActionInfo, ClientInfo
from moleculer_py.service import BaseService, action
from moleculer_py.broker import Broker
from moleculer_py.packets import PacketRequest, DataType, PacketResponse


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
