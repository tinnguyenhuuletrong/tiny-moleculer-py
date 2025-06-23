import asyncio
import redis.asyncio as redis

REDIS_URL = 'redis://localhost:6379/15'

async def publisher():
    await asyncio.sleep(2)
    print("start publisher")
    client = redis.from_url(REDIS_URL, decode_responses=False)
    await client.publish("my_channel", "Hello from publisher!")
    await client.aclose()

async def subscriber():
    client = redis.from_url(REDIS_URL, decode_responses=False)
    pubsub = client.pubsub()
    await pubsub.subscribe("my_channel")

    print("sub ok")

    print("Subscriber listening for messages...")
    async for message in pubsub.listen():
        if message['type'] == 'message':
            print(f"Received: {message['data'].decode()}")
            break # Exit after receiving one message for demonstration

    await pubsub.unsubscribe("my_channel")
    await client.aclose()

async def main():
    await asyncio.gather(subscriber(), publisher())

if __name__ == "__main__":
    asyncio.run(main())