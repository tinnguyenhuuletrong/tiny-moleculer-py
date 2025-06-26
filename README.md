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

## Getting Started

### Prerequisites

- Python 3.13+
- A running Redis server (see `examples/compose` for a quick start with Docker Compose)
- Install dev dependencies: `aioconsole`, `colorlog`, and those in `pyproject.toml`
- (optional) Bun for Reference JavaScript Broker

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

#### Reference JavaScript Broker (Dev)

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

## Examples

This project includes two main example scripts to help you get started:

### 1. Simple Usage

A minimal example showing how to define a service, register actions and events, and interact with the broker via a CLI. See [`examples/simple_usage.py`](examples/simple_usage.py).

**Features:**

- Greeter service with a `hello` action
- Event handler for `ev_random_number`
- Interactive CLI for calling actions and listing nodes/services

**Run the example:**

```sh
uv run examples/simple_usage.py
```

**Sample CLI usage:**

```sh
> call greeter-py.hello {"name": "Alice"}
{
  "result": "Hello, Alice!"
}

> call math.add {"a": 100, "b": 999}
{
  "result": 1099
}

> call math.random {}
{
  "receiptId": 650105604722,
  "_note": "ev_random_number will broadcast later with receiptId"
}

> nodes
# Shows the current node registry as JSON

> services
# Lists registered services

> exit
# Exits the CLI
```

**Note:** You can run this alongside the JS broker (see below) to test cross-language action calls and events.

---

### 2. OpenCV Usage

A more advanced example demonstrating how to use a service to download and pixelate an image using OpenCV. See [`examples/opencv_usage.py`](examples/opencv_usage.py).

**Features:**

- `opencv-service.pixelate` action downloads an image from a URL and pixelates it
- Uses OpenCV and requests
- Saves the pixelated image to the `opencv_output/` directory
- Interactive CLI for calling the pixelate action and listing nodes/services

**Prerequisites:**

- Install extra dependencies: `opencv-python`, `requests`, `numpy`
  (These are included in `pyproject.toml` dev dependencies.)

**Run the example:**

```sh
uv run examples/opencv_usage.py
```

**Sample CLI usage:**

```sh
> call opencv-service.pixelate {"url": "https://example.com/image.jpg"}
# Output: path to the saved pixelated image in opencv_output/

> nodes
# Shows the current node registry as JSON

> services
# Lists registered services

> exit
# Exits the CLI
```

---

For more details, see the code in the `examples/` directory. Each example sets up logging with colorlog for better readability.

## Load Balancing

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

### Node Offline Detection & Removal

Nodes that do not send heartbeats within the configured timeout are first marked as offline, and then removed from the registry after two offline cycles. This helps keep the node registry clean and up-to-date.
