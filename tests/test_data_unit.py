import pytest
from moleculer_py.data import (
    Registry,
    NodeInfo,
    ServiceInfo,
    ActionInfo,
    ClientInfo,
)
import time
import types
from moleculer_py.broker import Broker
from moleculer_py.packets import PacketHeartbeat, PacketDisconnect
from moleculer_py.utils import now


@pytest.fixture
def sample_registry() -> Registry:
    """Provides a sample registry for testing."""
    node_info = NodeInfo(
        nodeId="test-node-1",
        ipList=["127.0.0.1"],
        hostname="testhost",
        instanceID="instance-1",
        client=ClientInfo(type="python", version="0.1", langVersion="3.9"),
        config={},
        port=5000,
        seq=1,
        metadata={},
        services=[
            ServiceInfo(
                name="greeter",
                fullName="greeter",
                settings={},
                metadata={},
                actions={
                    "hello": ActionInfo(
                        cache=False,
                        tracing=False,
                        rawName="hello",
                        name="greeter.hello",
                        params={},
                    )
                },
                events={},
            )
        ],
        isOnline=True,
        lastPing=10,
    )
    return Registry(nodes={"test-node-1": node_info})


def test_find_remote_action_success(sample_registry: Registry):
    """Test that find_remote_action successfully finds an existing action."""
    result = sample_registry.find_remote_action("greeter.hello")
    assert result is not None
    node_id, action_info = result
    assert node_id == "test-node-1"
    assert action_info.name == "greeter.hello"
    assert isinstance(action_info, ActionInfo)


def test_find_remote_action_not_found(sample_registry: Registry):
    """Test that find_remote_action returns None for a non-existent action."""
    result = sample_registry.find_remote_action("nonexistent.action")
    assert result is None


def test_find_remote_action_offline_node(sample_registry: Registry):
    """Test that find_remote_action ignores actions on offline nodes."""
    # Mark the node as offline
    sample_registry.nodes["test-node-1"].isOnline = False

    result = sample_registry.find_remote_action("greeter.hello")
    assert result is None


def make_node(node_id, last_ping=None, is_online=True):
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
        services=[],
        lastPing=last_ping if last_ping is not None else now(),
        isOnline=is_online,
    )


def test_handle_heart_beat_marks_online_and_offline(monkeypatch):
    broker = Broker(node_id="n1")
    now0 = now()
    # Add two nodes: one will get heartbeat, one will be stale
    broker._registry.nodes["n2"] = make_node(
        "n2", last_ping=now0 - 25000, is_online=True
    )
    broker._registry.nodes["n3"] = make_node(
        "n3", last_ping=now0 - 10000, is_online=False
    )
    broker._registry.nodes["n4"] = make_node(
        "n4", last_ping=now0 - 5000, is_online=True
    )

    # Patch now() to a fixed value for repeatability
    monkeypatch.setattr("moleculer_py.broker.now", lambda: now0)

    # Send heartbeat from n3 (was offline)
    packet = PacketHeartbeat(ver="1", sender="n3")
    broker._handle_heart_beat(packet)
    broker._refresh_node_online_status()

    # n3 should be online and lastPing updated
    assert broker._registry.nodes["n3"].isOnline is True
    assert broker._registry.nodes["n3"].lastPing == now0
    # n2 should be marked offline (lastPing too old)
    assert broker._registry.nodes["n2"].isOnline is False
    # n4 should remain online
    assert broker._registry.nodes["n4"].isOnline is True


def test_handle_disconnect(monkeypatch):
    """Test that _handle_disconnect marks a node as offline."""
    broker = Broker(node_id="n1")
    now0 = now()

    # Add a node that is online
    broker._registry.nodes["n2"] = make_node(
        "n2", is_online=True, last_ping=now0 - 1000
    )

    # Patch now() to a fixed value
    monkeypatch.setattr("moleculer_py.broker.now", lambda: now0)

    # Send disconnect from n2
    packet = PacketDisconnect(ver="4", sender="n2")
    broker._handle_disconnect(packet)

    # n2 should be offline and lastPing updated
    assert broker._registry.nodes["n2"].isOnline is False
    assert broker._registry.nodes["n2"].lastPing == now0
