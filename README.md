# Tiny Moleculer for Python

A lightweight, Moleculer-compatible service broker for Python. This project aims to provide a minimal but functional implementation of the Moleculer microservices framework concepts in Python, using Redis for transport.

## Features

- **Service Broker:** Manages node lifecycle, service registry, and communication.
- **Redis Transport:** Uses Redis pub/sub for efficient messaging between nodes.
- **Node Discovery:** Nodes can discover each other on the network using `DISCOVER` and `INFO` packets.
- **Actions:** Define and call actions on services using a Pythonic decorator pattern.
- **BaseService & Decorators:** Use `BaseService` and the `@action` decorator to define services and actions in a style similar to Moleculer.js.
- **Heartbeating:** Nodes periodically send heartbeat packets to signal their liveness.
- **Interoperability:** Designed to be compatible with the Moleculer protocol (version "4").
- **Service Registry:** Maintains a registry of local and remote services/actions.

### Work in Progress / Planned

- **Action Calling:** Not yet implement the `ActionInfo.params` validator.
- **Events:** Event emission and listening are planned but not fully implemented yet.
- **Remote Action Calling:** The `Broker.call` method is a stub; remote action invocation is not yet implemented.
- **Event Emission:** The `Broker.emit` method is a stub; event emission is not yet implemented.

### Out of Scope / Not Implemented

- Other transporters (NATS, MQTT, AMQP, etc.)
- Built-in load balancing, circuit breaking, retries, fallback
- Service mixins/middlewares
- Advanced caching
- API Gateway integration
- Dedicated metrics/tracing adapters

## Getting Started

Here's a simple example of how to create a broker, register a service using the decorator pattern, and run it.

### Prerequisites

- Python 3.13+
- A running Redis server

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

### Test

```bash
uv run pytest
```

### Example run

```bash
cd examples/compose && sh ./run-dev.sh

uv run ./examples/simple_usage.py
```

### Usage

```python
import asyncio
from src.moleculer_py.broker import Broker
from src.moleculer_py.service import BaseService, action

class GreeterService(BaseService):
    def __init__(self, broker):
        super().__init__(broker, name="greeter-py")

    @action(params={"name": {"type": "string", "default": "World"}})
    async def hello(self, params):
        return f"Hello, {params.get('name', 'World')}!"

async def main():
    broker = Broker(node_id="python-node-1", redis_url="redis://localhost:6379/15")
    GreeterService(broker)  # Registers the service with the broker

    print("Starting broker...")
    await broker.start()

    print("Broker is running. Press Ctrl+C to stop.")
    try:
        await asyncio.sleep(60)
    except KeyboardInterrupt:
        pass

    print("Stopping broker...")
    await broker.stop()
    print("Broker stopped.")

if __name__ == "__main__":
    asyncio.run(main())
```

## Project Status

This project is in early development. The core functionality for creating a broker and registering services with actions is in place. Event handling, robust remote action calling, and other advanced features are planned but not yet implemented. See the feature list above for details.

## Limitations & Non-Goals

- Only Redis transport is supported (no NATS, MQTT, AMQP, etc.).
- No built-in load balancing, circuit breaking, retries, or fallback mechanisms.
- No support for service mixins or middlewares.
- No advanced caching or API gateway integration.
- Metrics, tracing, and logging adapters are not included (basic logging only).
- Event emission and remote action invocation are not yet implemented.
