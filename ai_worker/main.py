import asyncio
import json
import logging
import os
from datetime import UTC, datetime, timedelta

import redis.asyncio as redis
from tortoise import Tortoise

from ai_worker.tasks.generate_guide import generate_guide
from app.db.databases import TORTOISE_ORM
from app.models.guides import Guide, GuideStatus


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = (os.getenv("REDIS_URL", "redis://localhost:6379/0") or "").strip()
QUEUE_NAME = (os.getenv("AI_WORKER_QUEUE", "ai_tasks") or "").strip()

GUIDE_GENERATING_TIMEOUT_MINUTES = int(
    (os.getenv("GUIDE_GENERATING_TIMEOUT_MINUTES", "30") or "30").strip()
)
STALE_GUIDE_CHECK_INTERVAL_SECONDS = int(
    (os.getenv("STALE_GUIDE_CHECK_INTERVAL_SECONDS", "60") or "60").strip()
)


# DB 연결 초기화
async def _init_db() -> None:
    logger.info("worker: init db start")
    await Tortoise.init(config=TORTOISE_ORM)
    logger.info("worker: init db done")


# DB 연결 종료
async def _close_db() -> None:
    logger.info("worker: close db start")
    await Tortoise.close_connections()
    logger.info("worker: close db done")


# 30분 이상 GENERATING 상태인 가이드 실패 처리
async def _fail_stale_generating_guides() -> None:
    threshold = datetime.now(UTC) - timedelta(minutes=GUIDE_GENERATING_TIMEOUT_MINUTES)

    stale_guides = await Guide.filter(
        status=GuideStatus.GENERATING,
        created_at__lt=threshold,
    ).all()

    if not stale_guides:
        return

    for guide in stale_guides:
        guide.status = GuideStatus.FAILED
        guide.failure_code = "GUIDE_GENERATION_TIMEOUT"
        guide.failure_message = (
            f"Guide generation exceeded {GUIDE_GENERATING_TIMEOUT_MINUTES} minutes."
        )
        await guide.save(
            update_fields=["status", "failure_code", "failure_message", "updated_at"]
        )

    logger.warning("worker: marked %s stale generating guide(s) as FAILED", len(stale_guides))


# 주기적으로 stale guide 정리
async def _stale_guide_watchdog() -> None:
    logger.info(
        "worker: stale guide watchdog start timeout=%s min interval=%s sec",
        GUIDE_GENERATING_TIMEOUT_MINUTES,
        STALE_GUIDE_CHECK_INTERVAL_SECONDS,
    )

    while True:
        try:
            await _fail_stale_generating_guides()
        except Exception:
            logger.exception("worker: stale guide watchdog failed")

        await asyncio.sleep(STALE_GUIDE_CHECK_INTERVAL_SECONDS)


# worker 메인 루프
async def worker_loop():
    logger.info("worker: loop start")
    logger.info("worker: REDIS_URL=%s", REDIS_URL)
    logger.info("worker: QUEUE_NAME=%s", QUEUE_NAME)

    await _init_db()

    r = redis.from_url(REDIS_URL, decode_responses=True)
    logger.info("worker: redis client created")

    watchdog_task = asyncio.create_task(_stale_guide_watchdog())

    try:
        while True:
            item = await r.brpop(QUEUE_NAME, timeout=5)

            if not item:
                await asyncio.sleep(0.2)
                continue

            logger.info("worker: raw item received = %s", item)

            _, raw = item

            try:
                task = json.loads(raw)
            except Exception:
                logger.exception("worker: invalid task json")
                continue

            task_type = task.get("task")
            logger.info("worker: task_type=%s task=%s", task_type, task)

            if task_type == "generate_guide":
                try:
                    guide_id = int(task["guide_id"])
                    await generate_guide(guide_id)
                    logger.info("worker: generate_guide done")
                except Exception:
                    logger.exception("worker: generate_guide failed")
            else:
                logger.warning("worker: unknown task_type=%s", task_type)

    finally:
        watchdog_task.cancel()
        await r.aclose()
        await _close_db()


def main():
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()