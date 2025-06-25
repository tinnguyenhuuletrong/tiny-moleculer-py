from typing import Dict, Any
import aioconsole
import asyncio
import logging
from moleculer_py.broker import Broker
from moleculer_py import BaseService, action
from helper.log_helper import setup_global_logging

setup_global_logging(level=logging.INFO)
logger = logging.getLogger("app")


async def read_input_async(broker: Broker):
    while True:
        try:
            data = await aioconsole.ainput("\n> \n")
            cmd = data.strip()
            if cmd == "exit":
                logger.info("Exiting...")
                break
            logger.info(f"Received command: {cmd}")
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
            logger.error(e)


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

    # Run for 15 seconds to demonstrate lifecycle
    logger.info("Broker is running. Press Ctrl+C to stop.")

    try:
        # await asyncio.sleep(15_000_000)
        await read_input_async(broker)
    except:
        pass

    # Stop the broker
    logger.info("Stopping broker...")
    await broker.stop()
    logger.info("Broker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
