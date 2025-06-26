import json
import os
from typing import Dict, Any
import aioconsole
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import cv2
import numpy as np
import os
import requests
from moleculer_py import Broker, BaseService, action
from helper.log_helper import setup_global_logging
from moleculer_py.loadbalance import RoundRobinStrategy

setup_global_logging(level=logging.INFO)
logger = logging.getLogger("app")
logging.getLogger("broker").setLevel(logging.DEBUG)

OUTPUT_DIR = "opencv_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ThreadPoolExecutor for CPU-bound OpenCV work
executor = ThreadPoolExecutor(max_workers=2)


def download_and_pixelate(url: str, pixel_size: int = 16) -> str:
    # Download image synchronously (in thread)
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        raise ValueError(f"Failed to download image: HTTP {resp.status_code}")
    image_bytes = resp.content
    # Convert bytes to numpy array
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image")
    h, w = img.shape[:2]
    # Resize down and up to pixelate
    temp = cv2.resize(
        img, (w // pixel_size, h // pixel_size), interpolation=cv2.INTER_LINEAR
    )
    pixelated = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
    # Save to disk
    out_path = os.path.join(
        OUTPUT_DIR, f"pixelated_{np.random.randint(0, int(1e8))}.jpg"
    )
    cv2.imwrite(out_path, pixelated)
    return out_path


class OpenCVService(BaseService):
    @action(params={"url": {"type": "string"}})
    async def pixelate(self, params: Dict[str, Any]):
        url = params.get("url")
        if not url:
            raise ValueError("Missing 'url' parameter")
        logger.info(f"Downloading and pixelating image from {url}")
        loop = asyncio.get_running_loop()
        out_path = await loop.run_in_executor(executor, download_and_pixelate, url)
        logger.info(f"Saved pixelated image to {out_path}")
        return out_path


async def main():
    broker = Broker(
        node_id=f"python-opencv-node-{os.getpid()}",
        redis_url="redis://localhost:6379/15",
        strategy=RoundRobinStrategy(),
    )
    logger.info("Starting broker...")
    await broker.start()
    OpenCVService(broker, name="opencv-service")
    logger.info("Broker is running. Press Ctrl+C to stop.")
    try:
        await read_input_async(broker)
    except:
        pass
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
                case "services":
                    await aioconsole.aprint(broker.get_services())
                case _:
                    help_msg = (
                        "Available commands:\n"
                        "  nodes                - Show the current node registry as JSON\n"
                        "  services             - List registered services\n"
                        '  call <action> <params_json> - Call an action with params (e.g. call opencv-service.pixelate {"url": "https://example.com/image.jpg"})\n'
                        "  exit                 - Exit the CLI\n"
                    )
                    await aioconsole.aprint(help_msg)
        except Exception as e:
            logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
