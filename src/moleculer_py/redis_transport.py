import asyncio
import json
from typing import Callable, Dict, Any, Optional, Awaitable, List
import redis.asyncio as aioredis
from redis.asyncio.client import PubSub

MOLECULER_CHANNELS = {
    'INFO': 'MOL.INFO',
    'DISCOVER': 'MOL.DISCOVER',
    'HEARTBEAT': 'MOL.HEARTBEAT',
    'REQ': 'MOL.REQ',
    'RES': 'MOL.RES.{nodeID}',
    'EVENT': 'MOL.EVENT',
    'EVENT_NODE': 'MOL.EVENT.{nodeID}',
}

class RedisTransport:
    """
    Asyncio-based Redis Transport Layer compatible with Moleculer.js Redis transporter.
    Handles connection, (re)subscription, publishing, and packet dispatching.
    """
    def __init__(self, redis_url: str = 'redis://localhost:6379/0', node_id: Optional[str] = None):
        self.redis_url = redis_url
        self.node_id = node_id
        self.pub_client: Optional[aioredis.Redis] = None
        self.sub_client: Optional[aioredis.Redis] = None
        self.pubsub: Optional[PubSub] = None
        self.handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
        self.listen_task: Optional[asyncio.Task] = None
        self._subscribed_channels: set[str] = set()
        self._reconnect_delay = 2
        self._running = False
        self.on_connect: Optional[Callable[[], Awaitable[None]]] = None
        self.on_disconnect: Optional[Callable[[], Awaitable[None]]] = None
        self.on_error: Optional[Callable[[Exception], Awaitable[None]]] = None

    async def connect(self):
        """Connect to Redis and start listening."""
        self.pub_client = aioredis.from_url(self.redis_url, decode_responses=False)
        self.sub_client = aioredis.from_url(self.redis_url, decode_responses=False)
        self.pubsub = self.sub_client.pubsub()
        self._running = True

        if self._subscribed_channels:
            print(f"Resubscribing to channels: {list(self._subscribed_channels)}")
            await self.pubsub.subscribe(*self._subscribed_channels)

        if self.on_connect:
            await self.on_connect()
        print(f"Connected to Redis at {self.redis_url}")
        if self.listen_task is None or self.listen_task.done():
            self.listen_task = asyncio.create_task(self.listen())

    async def disconnect(self):
        """Disconnect from Redis and stop listening."""
        self._running = False
        if self.listen_task and not self.listen_task.done():
            self.listen_task.cancel()
        if self.pubsub:
            await self.pubsub.close()
        if self.pub_client:
            await self.pub_client.close()
        if self.sub_client:
            await self.sub_client.close()
        if self.on_disconnect:
            await self.on_disconnect()
        print("Disconnected from Redis.")

    async def subscribe(self, channels: List[str]):
        """Subscribe to a list of channels."""
        if not self.pubsub:
            raise RuntimeError("Not connected to Redis.")
        await self.pubsub.subscribe(*channels)
        self._subscribed_channels.update(channels)
        print(f"Subscribed to channels: {channels}")

    async def unsubscribe(self, channels: List[str]):
        """Unsubscribe from a list of channels."""
        if not self.pubsub:
            raise RuntimeError("Not connected to Redis.")
        await self.pubsub.unsubscribe(*channels)
        self._subscribed_channels.difference_update(channels)
        print(f"Unsubscribed from channels: {channels}")

    async def publish(self, channel: str, packet: Dict[str, Any]):
        """Publish a packet to a channel (JSON encoded)."""
        if not self.pub_client:
            raise RuntimeError("Not connected to Redis.")
        data = self.encode_packet(packet)
        await self.pub_client.publish(channel, data)
        print(f"Published to {channel}: {data}")

    def register_handler(self, channel: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Register an async handler for a channel."""
        if not asyncio.iscoroutinefunction(handler):
            raise TypeError("Handler must be an async function (coroutine)")
        self.handlers[channel] = handler

    def encode_packet(self, packet: Dict[str, Any]) -> str:
        """Encode a packet as JSON string."""
        return json.dumps(packet)

    def decode_packet(self, data: str) -> Dict[str, Any]:
        """Decode a JSON string to a packet."""
        return json.loads(data)

    async def listen(self):
        """Listen for messages on subscribed channels and dispatch them."""
        while self._running:
            try:
                if not self.pubsub:
                    await asyncio.sleep(self._reconnect_delay)
                    continue
                
                # Using get_message in a loop is more robust against connection drops
                # than `async for`, as it prevents a potential busy-loop if the
                # iterator terminates unexpectedly. A timeout allows the loop to
                # periodically check the `self._running` flag.
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                
                if message is None:
                    continue

                channel = message['channel'].decode('utf-8')
                try:
                    packet = self.decode_packet(message['data'])
                except json.JSONDecodeError as e:
                    print(f"Failed to decode message on channel '{channel}': {e}")
                    if self.on_error:
                        await self.on_error(e)
                    continue
                handler = self.handlers.get(channel)
                if handler:
                    await handler(packet)
                else:
                    await self.dispatch_packet(channel, packet)
            except (aioredis.ConnectionError, aioredis.TimeoutError) as e:
                print(f"Redis connection error: {e}. Reconnecting in {self._reconnect_delay}s...")
                if self.on_error:
                    await self.on_error(e)

                if not self._running:
                    break

                await asyncio.sleep(self._reconnect_delay)

                try:
                    # Previous connection is broken, create a new one.
                    await self.connect()
                    print("Reconnected to Redis successfully.")
                except Exception as recon_e:
                    print(f"Failed to reconnect to Redis: {recon_e}")
                    # The loop will continue and try again after another delay
                    # because of the sleep at the top of the loop.
            except Exception as e:
                print(f"Unexpected error in Redis listen loop: {e}")
                if self.on_error:
                    await self.on_error(e)
                # For unexpected errors, maybe we should stop.
                # For now, we just wait and continue, which might not be ideal.
                await asyncio.sleep(self._reconnect_delay)

    async def dispatch_packet(self, channel: str, packet: Dict[str, Any]):
        """Default packet dispatch if no handler is registered."""
        print(f"Dispatching packet from {channel}: {packet}")

    async def close(self):
        """Gracefully close the transport."""
        await self.disconnect() 