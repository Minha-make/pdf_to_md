"""Sequential background conversion worker and SSE event broadcaster."""

import asyncio
import json
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from omnipdf.core.models import ConversionConfig, ConversionMode
from omnipdf.core.router import convert_pdf
from omnipdf.storage.db import (
    DEFAULT_DB_PATH,
    sync_update_job_progress,
    update_job_status,
)

logger = logging.getLogger(__name__)


class JobEventBroadcaster:
    """Manages real-time Server-Sent Events (SSE) subscriptions per job."""

    def __init__(self) -> None:
        self._listeners: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        """Register a new listener queue for a specific job."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._listeners[job_id].add(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a listener queue."""
        if job_id in self._listeners:
            self._listeners[job_id].discard(queue)
            if not self._listeners[job_id]:
                del self._listeners[job_id]

    async def publish(self, job_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event to all subscribers listening to this job."""
        payload = {"event": event_type, "data": data}
        if job_id in self._listeners:
            for q in list(self._listeners[job_id]):
                await q.put(payload)

    async def stream_events(
        self, job_id: str, initial_state: dict[str, Any] | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Async generator yielding SSE formatted events for a job."""
        queue = self.subscribe(job_id)

        # Emit initial state if provided
        if initial_state:
            yield {
                "event": "state",
                "data": json.dumps(initial_state),
            }

        try:
            while True:
                item = await queue.get()
                event_name = item.get("event", "message")
                data_obj = item.get("data", {})
                yield {
                    "event": event_name,
                    "data": json.dumps(data_obj),
                }
                # Terminate stream on terminal events
                if event_name in ("complete", "error", "cancelled"):
                    break
        finally:
            self.unsubscribe(job_id, queue)


class ConversionWorker:
    """Consumes conversion jobs sequentially to prevent memory exhaustion."""

    def __init__(
        self,
        db_path: Path = DEFAULT_DB_PATH,
        broadcaster: JobEventBroadcaster | None = None,
    ) -> None:
        self.db_path = db_path
        self.broadcaster = broadcaster or JobEventBroadcaster()
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.running = False
        self._worker_task: asyncio.Task[None] | None = None
        self._cancelled_jobs: set[str] = set()
        self._current_job_id: str | None = None

    async def start(self) -> None:
        """Start the background consumer loop."""
        if not self.running:
            self.running = True
            self._worker_task = asyncio.create_task(self._process_queue())
            logger.info("Sequential conversion worker started.")

    async def stop(self) -> None:
        """Stop the background consumer loop cleanly."""
        self.running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info("Sequential conversion worker stopped.")

    async def enqueue_job(
        self,
        job_id: str,
        input_pdf_path: Path,
        output_dir: Path,
        config_dict: dict[str, Any],
    ) -> None:
        """Add a job to the sequential processing queue."""
        await self.queue.put(
            {
                "job_id": job_id,
                "input_pdf_path": input_pdf_path,
                "output_dir": output_dir,
                "config": config_dict,
            }
        )
        logger.info(f"Enqueued job {job_id} for processing.")

    def cancel_job(self, job_id: str) -> bool:
        """Signal cancellation for a job."""
        self._cancelled_jobs.add(job_id)
        logger.info(f"Cancellation requested for job {job_id}.")
        return True

    async def _process_queue(self) -> None:
        """Main loop pulling jobs from queue one at a time."""
        while self.running:
            try:
                item = await self.queue.get()
            except asyncio.CancelledError:
                break

            job_id = item["job_id"]
            self._current_job_id = job_id

            try:
                if job_id in self._cancelled_jobs:
                    await update_job_status(
                        self.db_path, job_id, "cancelled", error_message="Cancelled by user"
                    )
                    await self.broadcaster.publish(
                        job_id, "cancelled", {"job_id": job_id, "status": "cancelled"}
                    )
                    self.queue.task_done()
                    continue

                await self._execute_conversion(item)
            except Exception as e:
                logger.error(f"Unexpected error executing job {job_id}: {e}", exc_info=True)
                await update_job_status(self.db_path, job_id, "failed", error_message=str(e))
                await self.broadcaster.publish(
                    job_id, "error", {"job_id": job_id, "status": "failed", "error": str(e)}
                )
            finally:
                self._current_job_id = None
                self._cancelled_jobs.discard(job_id)
                self.queue.task_done()

    async def _execute_conversion(self, item: dict[str, Any]) -> None:
        """Run conversion for a single job item."""
        job_id = item["job_id"]
        pdf_path: Path = item["input_pdf_path"]
        output_dir: Path = item["output_dir"]
        cfg_dict: dict[str, Any] = item["config"]

        # Reconstruct ConversionConfig
        mode_str = cfg_dict.get("mode", "auto").lower()
        conv_mode = ConversionMode(mode_str)
        config = ConversionConfig(
            mode=conv_mode,
            password=cfg_dict.get("password"),
            extract_images=cfg_dict.get("extract_images", True),
            output_dir=output_dir,
            ocr_langs=cfg_dict.get("ocr_langs", ["en", "vi"]),
            use_vlm=cfg_dict.get("use_vlm", False),
            include_frontmatter=cfg_dict.get("include_frontmatter", True),
            batch_size=cfg_dict.get("batch_size", 15),
        )

        loop = asyncio.get_running_loop()

        def progress_callback(curr: int, total: int, engine: str) -> None:
            if job_id in self._cancelled_jobs:
                raise InterruptedError(f"Job {job_id} cancelled.")

            # Update database synchronously in this thread
            sync_update_job_progress(self.db_path, job_id, curr, total, engine)

            # Broadcast progress event if loop is running
            if not loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    self.broadcaster.publish(
                        job_id,
                        "progress",
                        {
                            "job_id": job_id,
                            "current_page": curr,
                            "total_pages": total,
                            "engine_used": engine,
                            "status": "processing",
                        },
                    ),
                    loop,
                )

        try:
            # Run heavy conversion in background worker thread
            result = await asyncio.to_thread(
                convert_pdf, pdf_path, config, on_progress=progress_callback
            )

            if job_id in self._cancelled_jobs:
                await update_job_status(
                    self.db_path, job_id, "cancelled", error_message="Cancelled by user"
                )
                await self.broadcaster.publish(
                    job_id, "cancelled", {"job_id": job_id, "status": "cancelled"}
                )
                return

            md_path_str = str(result.output_path) if result.output_path else ""
            await update_job_status(
                self.db_path,
                job_id,
                "completed",
                output_dir=str(output_dir),
                markdown_path=md_path_str,
                total_pages=result.total_pages,
            )

            await self.broadcaster.publish(
                job_id,
                "complete",
                {
                    "job_id": job_id,
                    "status": "completed",
                    "total_pages": result.total_pages,
                    "engines_used": result.engines_used,
                    "markdown_path": md_path_str,
                    "duration_ms": result.total_time_ms,
                },
            )

        except InterruptedError:
            logger.info(f"Job {job_id} was successfully interrupted.")
            await update_job_status(
                self.db_path, job_id, "cancelled", error_message="Cancelled by user"
            )
            await self.broadcaster.publish(
                job_id, "cancelled", {"job_id": job_id, "status": "cancelled"}
            )
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            await update_job_status(self.db_path, job_id, "failed", error_message=str(e))
            await self.broadcaster.publish(
                job_id, "error", {"job_id": job_id, "status": "failed", "error": str(e)}
            )
