import json
from typing import Dict, Any
import aioconsole
import asyncio
import logging
from moleculer_py import Broker, BaseService, action, event
from helper.log_helper import setup_global_logging
from moleculer_py.loadbalance import RoundRobinStrategy

setup_global_logging(level=logging.INFO)
logger = logging.getLogger("app")

# Set Debug level in broker module only
logging.getLogger("broker").setLevel(logging.DEBUG)
# logging.getLogger("transit").setLevel(logging.DEBUG)


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
    broker = Broker(
        node_id="python-node-1",
        redis_url="redis://localhost:6379/15",
        strategy=RoundRobinStrategy(),
    )

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


async def read_input_async(broker: Broker):
    while True:
        try:
            data = await aioconsole.ainput("\n> \n")
            cmd = data.strip()
            if cmd == "exit":
                logger.info("Exiting...")
                break
            match cmd:
                case "nodes":
                    await aioconsole.aprint(
                        broker.get_registry().to_json(indent=2, separators=None)
                    )
                    pass
                case "services":
                    await aioconsole.aprint(broker.get_services())
                    pass
                case _ if cmd.startswith("call"):
                    # Parse: call <action_name> <params_json>
                    try:
                        parts = cmd.split(" ", 2)
                        if len(parts) < 2:
                            await aioconsole.aprint(
                                "Usage: call <action_name> <params_json>"
                            )
                            continue
                        event_name = parts[1]
                        params = {}
                        if len(parts) == 3:
                            try:
                                params = json.loads(parts[2])
                            except Exception as e:
                                await aioconsole.aprint(f"Invalid JSON for params: {e}")
                                continue
                        res = await broker.call(event_name, params=params)
                        await aioconsole.aprint(
                            json.dumps(res, indent=2, separators=None)
                        )
                    except Exception as e:
                        await aioconsole.aprint(f"Error: {e}")
                    pass
                case _ if cmd.startswith("emit"):
                    # Parse: emit <event_name> <params_json>
                    try:
                        parts = cmd.split(" ", 2)
                        if len(parts) < 2:
                            await aioconsole.aprint(
                                "Usage: emit <event_name> <params_json>"
                            )
                            continue
                        event_name = parts[1]
                        params = {}
                        if len(parts) == 3:
                            try:
                                params = json.loads(parts[2])
                            except Exception as e:
                                await aioconsole.aprint(f"Invalid JSON for params: {e}")
                                continue
                        await broker.emit(event_name, data=params)
                    except Exception as e:
                        await aioconsole.aprint(f"Error: {e}")
                    pass
                case _ if cmd.startswith("broadcast"):
                    # Parse: emit <event_name> <params_json>
                    try:
                        parts = cmd.split(" ", 2)
                        if len(parts) < 2:
                            await aioconsole.aprint(
                                "Usage: broadcast <event_name> <params_json>"
                            )
                            continue
                        event_name = parts[1]
                        params = {}
                        if len(parts) == 3:
                            try:
                                params = json.loads(parts[2])
                            except Exception as e:
                                await aioconsole.aprint(f"Invalid JSON for params: {e}")
                                continue
                        await broker.broadcast(event_name, data=params)
                    except Exception as e:
                        await aioconsole.aprint(f"Error: {e}")
                    pass
                case _:
                    help_msg = (
                        "Available commands:\n"
                        "  nodes                            - Show the current node registry as JSON\n"
                        "  services                         - List registered services\n"
                        '  call <action> <params_json>      - Call an action with params (e.g. call greeter-py.hello {"name": "Alice"})\n'
                        '  emit <event> <params_json>       - Emit an event with params (e.g. emit ev_something {"from": "some where"})\n'
                        '  broadcast <event> <params_json>  - Broadcast an event with params (e.g. broadcast ev_something {"from": "universal"})\n'
                        "  exit                 - Exit the CLI\n"
                    )
                    await aioconsole.aprint(help_msg)
                    continue
        except Exception as e:
            logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
