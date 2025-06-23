import pytest
from src.moleculer_py.packets import (
    parse_packet_by_type,
    PacketEvent,
    PacketRequest,
    PacketInfo,
)


def test_parse_packet_by_type_event():
    packet = {
        "ver": "4",
        "sender": "node1",
        "id": "abc",
        "event": "user.created",
    }
    parsed = parse_packet_by_type("MOL.EVENT", packet)
    assert isinstance(parsed, PacketEvent)
    assert parsed.event == "user.created"


def test_parse_packet_by_type_request():
    packet = {
        "ver": "4",
        "sender": "node2",
        "id": "req1",
        "action": "math.add",
    }
    parsed = parse_packet_by_type("MOL.REQ", packet)
    assert isinstance(parsed, PacketRequest)
    assert parsed.action == "math.add"


def test_parse_packet_by_type_info():
    packet = {
        "ver": "4",
        "sender": "node3",
        "services": [],
        "ipList": [],
        "client": {"type": "python", "version": "0.1", "langVersion": ""},
    }
    parsed = parse_packet_by_type("MOL.INFO", packet)
    assert isinstance(parsed, PacketInfo)
    assert parsed.sender == "node3"


def test_parse_packet_by_type_unknown():
    with pytest.raises(ValueError) as exc:
        parse_packet_by_type("MOL.UNKNOWN", {"foo": "bar"})
    assert "Unknown messageType prefix" in str(exc.value)


def test_parse_packet_by_type_malformed():
    # Missing required field 'ver' for PacketEvent
    with pytest.raises(ValueError) as exc:
        parse_packet_by_type("MOL.EVENT", {"sender": "node1"})
    assert "Failed to parse packet as PacketEvent" in str(exc.value)
