# Tiny Moleculer for Python

A lightweight, Moleculer-compatible service broker for Python. This project aims to provide a minimal but functional implementation of the Moleculer microservices framework concepts in Python, using Redis for transport.

## Features

- **Service Broker:** Manages the node lifecycle, service registry, and communication.
- **Redis Transport:** Uses Redis pub/sub for efficient messaging between nodes.
- **Node Discovery:** Nodes can discover each other on the network using `DISCOVER` and `INFO` packets.
- **Actions & Events:** Supports defining and calling actions on services (events are a work in progress).
- **Heartbeating:** Nodes periodically send heartbeat packets to signal their liveness.
- **Interoperability:** Designed to be compatible with the Moleculer protocol (version "4").

## Getting Started

Here's a simple example of how to create a broker, register a service, and run it.

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
uv run -m pytest
```

### Example run

```bash
uv run -m examples.simple_usage
```

### Usage

```python
import asyncio
from src.moleculer_py.broker import Broker

async def main():
    # Create a broker instance with a unique node ID
    broker = Broker(node_id="python-node-1", redis_url="redis://localhost:6379/15")

    # Register a dummy service
    broker.register_service("greeter-py", {
        "actions": {
            "hello": lambda params: f"Hello, {params.get('name', 'World')}!"
        },
        "events": {}
    })

    # Start the broker
    print("Starting broker...")
    await broker.start()

    # Run for a while to demonstrate
    print("Broker is running. Press Ctrl+C to stop.")
    try:
        await asyncio.sleep(60)
    except KeyboardInterrupt:
        pass

    # Stop the broker
    print("Stopping broker...")
    await broker.stop()
    print("Broker stopped.")

if __name__ == "__main__":
    asyncio.run(main())
```

## Project Status

This project is currently in early development. The core functionality for creating a broker and registering services is in place, but many features (like robust action calling, event handling, and service discovery details) are still under construction.
