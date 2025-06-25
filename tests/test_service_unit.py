from typing import Any
import pytest
import asyncio
from unittest.mock import MagicMock

import sys
import types

# Import BaseService and action from the correct path
from src.moleculer_py.data import ServiceInfo
from src.moleculer_py.service import BaseService, action
from src.moleculer_py.broker import Broker


async def dummy(target_node_id: str | None = None):
    pass


@pytest.mark.asyncio
async def test_action_decorator_and_registration():
    broker = Broker("")
    broker.transit._send_info = dummy

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
