from typing import Dict
from typing import Any
import aioconsole
import asyncio
from src.moleculer_py.broker import Broker
from src.moleculer_py import BaseService, action
import logging

logging.basicConfig(level=logging.INFO)


async def read_input_async(broker: Broker):
    while True:
        try:
            data = await aioconsole.ainput("> ")
            cmd = data.strip()
            if cmd == "exit":
                print("Exiting...")
                break
            print(f"Received command: {cmd}")
            match cmd:
                case "nodes":
                    await aioconsole.aprint(
                        broker.get_registry().to_json(indent=2, separators=None)
                    )
                    pass
                case "services":
                    await aioconsole.aprint(broker.get_services())
                    pass
                case _:
                    continue
        except Exception as e:
            print(e)


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
    print("Starting broker...")
    await broker.start()

    # Register the greeter service (using BaseService)
    GreeterService(broker, name="greeter-py")

    # Run for 15 seconds to demonstrate lifecycle
    print("Broker is running. Press Ctrl+C to stop.")

    try:
        # await asyncio.sleep(15_000_000)
        await read_input_async(broker)
    except:
        pass

    # Stop the broker
    print("Stopping broker...")
    await broker.stop()
    print("Broker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
