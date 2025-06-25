# Tiny Moleculer for Python

A lightweight, Moleculer-compatible service broker for Python. This project provides a minimal but functional implementation of the Moleculer microservices framework concepts in Python, using Redis for transport.

## Features

- **Service Broker:** Manages node lifecycle, service registry, and communication between nodes.
- **Redis Transport:** Uses Redis pub/sub for efficient messaging between nodes.
- **Node Discovery:** Nodes discover each other using `DISCOVER` and `INFO` packets.
- **Actions:** Define and call actions on services using a Pythonic decorator pattern.
- **BaseService & Decorators:** Use `BaseService` and the `@action` decorator to define services and actions in a style similar to Moleculer.js.
- **Heartbeating:** Nodes periodically send heartbeat packets to signal their liveness.
- **Interoperability:** Designed to be compatible with the Moleculer protocol (version "4").
- **Service Registry:** Maintains a registry of local and remote services/actions.
- **Remote Action Calling:** Supports calling actions on remote nodes (via `Broker.call`).
- **Interactive CLI Example:** Example includes an async REPL for interacting with the broker.

### Work in Progress / Planned

- **Action Parameter Validation:** The `ActionInfo.params` validator is not yet implemented.
- **Events:** Event emission and listening are planned but not fully implemented yet (`Broker.emit` is a stub).
- **Advanced Features:** No built-in load balancing, circuit breaking, retries, fallback, or service mixins/middlewares.

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

#### Reference JavaScript Broker Example

To demonstrate interoperability and for testing, a reference Moleculer.js broker is included. This allows you to run a Node.js service alongside the Python broker and test cross-language action calls.

The JS broker is located at `examples/compose/js-service/sample.ts` and can be started with the provided script.

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
  },
});
```

This JS service exposes a `math.add` action that can be called from the Python broker (see the example usage section above for how to call actions across nodes).

### Test

```bash
uv run pytest
```

### Example Usage

Below is an up-to-date example based on `examples/simple_usage.py`:

```python
import json
from typing import Dict, Any
import aioconsole
import asyncio
import logging
from moleculer_py.broker import Broker
from moleculer_py import BaseService, action

# Define the greeter service using BaseService
class GreeterService(BaseService):
    @action(
        params={"name": {"type": "string"}},
    )
    async def hello(self, params: Dict[str, Any]):
        return f"Hello, {params.get('name', 'anonymous-👤')}!"

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

```

## Project Status

This project is in early development. The core functionality for creating a broker, registering services with actions, and remote action calling is in place. Event handling, robust remote action calling, and other advanced features are planned but not yet implemented. See the feature list above for details.

## Limitations & Non-Goals

- Only Redis transport is supported (no NATS, MQTT, AMQP, etc.).
- No built-in load balancing, circuit breaking, retries, or fallback mechanisms.
- No support for service mixins or middlewares.
- No advanced caching or API gateway integration.
- Metrics, tracing, and logging adapters are not included (basic logging only).
- Event emission and remote action invocation are not yet implemented.
