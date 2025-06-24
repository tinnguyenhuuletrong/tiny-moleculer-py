import aioconsole
import asyncio
from src.moleculer_py.broker import Broker
import logging

logging.basicConfig(level=logging.DEBUG)


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
                        broker.registry.to_json(indent=2, separators=None)
                    )
                case _:
                    continue
        except Exception as e:
            print(e)


async def main():
    # Create a broker instance with a unique node ID
    broker = Broker(node_id="python-node-1", redis_url="redis://localhost:6379/15")

    # Start the broker
    print("Starting broker...")
    await broker.start()

    # Register a dummy service (actions/events are placeholders)
    await broker.register_service(
        "greeter-py",
        {
            "actions": {
                "python.hello": lambda params: f"Hello, {params.get('name', 'World')}!"
            },
            "events": {},
        },
    )

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
