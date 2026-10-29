"""Submit several jobs to Redis/ARQ and observe concurrency, retries, and timeout behavior."""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime

import redis.asyncio as redis
from arq import create_pool

from app.config import REDIS_SETTINGS


async def main() -> None:
    r = await create_pool(REDIS_SETTINGS)
    try:
        for index in range(1, 11):
            payload = {
                "url": f"https://example.com/jobs/{index}",
                "raw_text": "Python developer role. " * 20,
            }
            job = await r.enqueue_job("process_job", **payload)
            print(f"[{datetime.utcnow().isoformat(timespec='seconds')}] queued job {index} -> {job.job_id}")
        print("Waiting for jobs to process...")
        while True:
            pending = await r.llen("arq:jobs")
            if pending == 0:
                break
            await asyncio.sleep(1)
        print("All jobs submitted; broker queue drained.")
    finally:
        await r.close()


if __name__ == "__main__":
    asyncio.run(main())
