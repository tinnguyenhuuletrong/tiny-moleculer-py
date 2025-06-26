# Tiny Moleculer for Python

A lightweight, Moleculer-compatible service broker for Python. This project provides a minimal but functional implementation of the Moleculer microservices framework concepts in Python, using Redis for transport.

## Features

- **Service Broker:** Manages node lifecycle, service registry, and communication between nodes.
- **Redis Transport:** Uses Redis pub/sub for efficient messaging between nodes.
- **Node Discovery:** Nodes discover each other using `DISCOVER` and `INFO` packets.
- **Actions:** Define and call actions on services using a Pythonic decorator pattern.
- **BaseService & Decorators:** Use `BaseService` and the `@action` and `@event` decorators to define services, actions, and event handlers in a style similar to Moleculer.js.
- **Heartbeating:** Nodes periodically send heartbeat packets to signal their liveness.
- **Interoperability:** Designed to be compatible with the Moleculer protocol (version "4").
- **Service Registry:** Maintains a registry of local and remote services/actions.
- **Remote Action Calling & Load Balancing:** Supports calling actions on remote nodes (via `Broker.call`). Remote action calls now use a pluggable load balancing strategy (default: round-robin/random among online nodes).
- **Interactive CLI Example:** Example includes an async REPL for interacting with the broker.
- **Events:** Event listening and handler registration are implemented via the `@event` decorator. Services can react to events broadcast from other nodes (including JS Moleculer nodes). Event emission (`Broker.emit`) is interoperable with Moleculer.js, but advanced features are still in progress.

### Work in Progress / Planned

- **Action Parameter Validation:** The `ActionInfo.params` validator is not yet implemented.
- **Events:** Event emission and listening are planned but not fully implemented yet (`Broker.emit` is a stub).
- **Advanced Features:** No circuit breaking, retries, fallback, or service mixins/middlewares. Basic load balancing is now supported (see below).

## Getting Started

### Prerequisites

- Python 3.13+
- A running Redis server (see `examples/compose` for a quick start with Docker Compose)
- Install dev dependencies: `aioconsole`, `colorlog`, and those in `pyproject.toml`
- For Bun

### Installation

This project uses [uv](https://github.com/astral-sh/uv) for project and dependency management.

1.  **Install `uv`**

    Follow the official installation guide to install `uv` on your system. For example, on macOS or Linux, you can run:

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Install Dependencies**

    Once `uv` is installed, sync the dependencies from `pyproject.toml`:

    ```bash
    uv sync
    ```

### Running Redis (Dev)

You can quickly start a local Redis instance using Docker Compose:

```bash
cd examples/compose

# Start redis
sh ./run-dev.sh

```

#### Reference JavaScript Broker Example (with Events)

To demonstrate interoperability and for testing, a reference Moleculer.js broker is included. This allows you to run a Node.js service alongside the Python broker and test cross-language action calls.

The JS broker is located at `examples/compose/js-service/sample.ts` and can be started with the provided script. It now includes an `add` action and a `random` action that emits an event after a delay.

**Run the JS broker:**

```sh
# Require [Bun](https://bun.sh/) to run

cd examples/compose
sh ./run-js-node.sh
```

**sample.ts:**

```ts
// Define a service
broker.createService({
  name: "math",
  actions: {
    add(ctx) {
      return {
        result: Number(ctx.params.a) + Number(ctx.params.b),
      };
    },
    async random(ctx) {
      const afterMs = ctx.params["afterMs"] || 1000;
      const receiptId = Math.round(Math.random() * Date.now());
      setTimeout(async () => {
        await broker.emit("ev_random_number", {
          receiptId,
          value: Math.random(),
        });
      }, afterMs);
      return {
        receiptId: receiptId,
        _note: "ev_random_number will broadcast later with receiptId",
      };
    },
  },
});
```

This JS service exposes a `math.add` action and a `math.random` action. The `random` action emits an `ev_random_number` event after a delay, which can be handled by Python services using the event system.

### Test

```bash
uv run pytest
```

### Example Usage

Below is an up-to-date example based on `examples/simple_usage.py`, now showing event handling:

```python
import json
from typing import Dict, Any
import aioconsole
import asyncio
import logging
from moleculer_py.broker import Broker
from moleculer_py import BaseService, action
from moleculer_py.service import event

# Define the greeter service using BaseService
class GreeterService(BaseService):
    @action(
        params={"name": {"type": "string"}},
    )
    async def hello(self, params: Dict[str, Any]):
        return f"Hello, {params.get('name', 'anonymous-👤')}!"

    @event()
    async def ev_random_number(self, params: Dict[str, Any]):
        logger.info(f"on ev_random_number {params}")
        pass

async def main():
    # Create a broker instance with a unique node ID
    broker = Broker(node_id="python-node-1", redis_url="redis://localhost:6379/15")

    # Start the broker
    logger.info("Starting broker...")
    await broker.start()

    # Register the greeter service (using BaseService)
    GreeterService(broker, name="greeter-py")

    logger.info("Broker is running. Press Ctrl+C to stop.")
    try:
        await read_input_async(broker)
    except:
        pass

    logger.info("Stopping broker...")
    await broker.stop()
    logger.info("Broker stopped.")

if __name__ == "__main__":
    asyncio.run(main())
```

```sh

# Start example
uv run examples/simple_usage.py
[2025-06-25 17:28:23,939] INFO   app      - Starting broker...
[2025-06-25 17:28:23,940] INFO   trans    - Connected to Redis at redis://localhost:6379/15
[2025-06-25 17:28:23,955] INFO   broker   - Broker python-node-1 started.
[2025-06-25 17:28:23,957] INFO   app      - Broker is running. Press Ctrl+C to stop.

>
[2025-06-25 17:28:24,944] INFO   broker   - Node 'pc.local-98221' connected.
[2025-06-25 17:28:24,953] INFO   broker   - Node 'python-node-1' connected.

Available commands:
  nodes                - Show the current node registry as JSON
  services             - List registered services
  call <action> <params_json> - Call an action with params (e.g. call greeter-py.hello {"name": "Alice"})
  exit                 - Exit the CLI


>
call math.add {"a":100, "b": 999}
[2025-06-25 17:28:44,981] DEBUG  broker   - -> pc.local-98221.math.add req_id=7482fb66-86f2-4842-a83d-92e5645ef96c
[2025-06-25 17:28:44,986] DEBUG  broker   - <- req_id=7482fb66-86f2-4842-a83d-92e5645ef96c
{
  "result": 1099
}

>
call math.random {}
[2025-06-25 10:49:59,219] DEBUG  broker   - -> tinnhlt-macbook-pro.local-58153.math.random req_id=6ed5fd49-72e5-49e1-bd97-2a26ec6caf91
[2025-06-25 10:49:59,223] DEBUG  broker   - <- req_id=6ed5fd49-72e5-49e1-bd97-2a26ec6caf91
{
  "receiptId": 650105604722,
  "_note": "ev_random_number will broadcast later with receiptId"
}

>
[2025-06-25 10:50:00,229] INFO   app      - on ev_random_number {'receiptId': 650105604722, 'value': 0.9705537015886184}

```

## Project Status

This project is in early development, but now supports:

- Creating a broker, registering services with actions, and remote action calling
- Event handling and event handler registration via the `@event` decorator (including cross-language events with Moleculer.js)

Robust remote action calling and other advanced features are planned but not yet implemented. See the feature list above for details.

## Limitations & Non-Goals

- Only Redis transport is supported (no NATS, MQTT, AMQP, etc.).
- No circuit breaking, retries, or fallback mechanisms (basic load balancing only).
- No support for service mixins or middlewares.
- No advanced caching or API gateway integration.
- Metrics, tracing, and logging adapters are not included (basic logging only).
- Event emission (`Broker.emit`) is interoperable with Moleculer.js, but advanced event features (e.g., groups, broadcast options) are not yet implemented.

### Load Balancing

Remote action calls (e.g., `Broker.call`) now use a pluggable load balancing strategy to select among available online nodes that provide the requested action. By default, the `RoundRobinStrategy` (which randomly selects an online node) is used. You can provide your own strategy by passing it to the `Broker` constructor:

```python
from moleculer_py.broker import Broker
from moleculer_py.loadbalance import RoundRobinStrategy

broker = Broker(
    node_id="python-node-1",
    redis_url="redis://localhost:6379/15",
    strategy=RoundRobinStrategy(),  # Optional: customize load balancing
)
```

To implement your own strategy, subclass `LoadBalanceStrategy` and implement the `select_node` method.

#### Node Offline Detection & Removal

Nodes that do not send heartbeats within the configured timeout are first marked as offline, and then removed from the registry after two offline cycles. This helps keep the node registry clean and up-to-date.
