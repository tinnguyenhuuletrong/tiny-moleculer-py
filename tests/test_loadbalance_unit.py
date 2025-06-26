import pytest
from moleculer_py.loadbalance import RoundRobinStrategy
from moleculer_py.data import Registry, NodeInfo, ServiceInfo, ActionInfo, ClientInfo


def make_registry(nodes):
    return Registry(nodes=nodes)


def make_node(node_id, online, actions):
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
                actions=actions,
                events={},
            )
        ],
        lastPing=123,
        isOnline=online,
        isLocal=False,
    )


def test_round_robin_strategy_selects_only_online_nodes():
    action_name = "svc.hello"
    action = ActionInfo(rawName=action_name, name=action_name, params={})
    nodes = {
        "node1": make_node("node1", True, {action_name: action}),
        "node2": make_node("node2", False, {action_name: action}),
        "node3": make_node("node3", True, {}),
        "node4": make_node("node4", True, {action_name: action}),
    }
    registry = make_registry(nodes)
    strategy = RoundRobinStrategy()
    # Run multiple times to check randomness
    selected = set()
    for _ in range(20):
        result = strategy.select_node(registry, action_name)
        assert result is not None
        node_id, act = result
        assert node_id in ("node1", "node4")
        assert act.name == action_name
        selected.add(node_id)
    # Both online nodes should be selected at least once
    assert selected == {"node1", "node4"}


def test_round_robin_strategy_returns_none_if_no_node():
    action_name = "svc.hello"
    nodes = {
        "node1": make_node("node1", True, {}),
        "node2": make_node("node2", False, {}),
    }
    registry = make_registry(nodes)
    strategy = RoundRobinStrategy()
    result = strategy.select_node(registry, action_name)
    assert result is None
