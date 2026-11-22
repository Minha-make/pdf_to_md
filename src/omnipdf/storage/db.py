"""Asynchronous SQLite database access and job persistence using aiosqlite."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

DEFAULT_DB_PATH = Path("data/omnipdf.db")


async def get_db_connection(db_path: Path = DEFAULT_DB_PATH) -> aiosqlite.Connection:
    """Create and configure an aiosqlite connection with WAL mode."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode = WAL;")
    await db.execute("PRAGMA foreign_keys = ON;")
    return db


async def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Initialize SQLite database tables and indexes."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                mode TEXT NOT NULL,
                current_page INTEGER DEFAULT 0,
                total_pages INTEGER DEFAULT 0,
                engine_used TEXT DEFAULT '',
                output_dir TEXT DEFAULT '',
                markdown_path TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                config_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT DEFAULT ''
            );
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_sha256 ON jobs (sha256, status, mode);"
        )
        await db.commit()


async def create_job(
    db_path: Path,
    job_id: str,
    filename: str,
    sha256: str,
    mode: str,
    config: dict[str, Any],
    total_pages: int = 0,
) -> dict[str, Any]:
    """Insert a new job record in PENDING status."""
    now_iso = datetime.now(UTC).isoformat()
    config_str = json.dumps(config, default=str)

    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO jobs (
                id, filename, sha256, status, mode, current_page,
                total_pages, config_json, created_at
            ) VALUES (?, ?, ?, 'pending', ?, 0, ?, ?, ?)
            """,
            (job_id, filename, sha256, mode, total_pages, config_str, now_iso),
        )
        await db.commit()

    return {
        "id": job_id,
        "filename": filename,
        "sha256": sha256,
        "status": "pending",
        "mode": mode,
        "current_page": 0,
        "total_pages": total_pages,
        "engine_used": "",
        "output_dir": "",
        "markdown_path": "",
        "error_message": "",
        "config": config,
        "created_at": now_iso,
        "completed_at": "",
    }


async def find_cached_job(db_path: Path, sha256: str, mode: str) -> dict[str, Any] | None:
    """Find a previously completed job with identical SHA-256 and mode whose output exists."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM jobs
            WHERE sha256 = ? AND mode = ? AND status = 'completed'
            ORDER BY completed_at DESC LIMIT 1
            """,
            (sha256, mode),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        job_dict = dict(row)
        md_path_str = job_dict.get("markdown_path")
        if md_path_str and Path(md_path_str).exists():
            try:
                job_dict["config"] = json.loads(job_dict.get("config_json", "{}"))
            except Exception:
                job_dict["config"] = {}
            return job_dict
        return None


async def get_job(db_path: Path, job_id: str) -> dict[str, Any] | None:
    """Fetch a single job record by ID."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        job_dict = dict(row)
        try:
            job_dict["config"] = json.loads(job_dict.get("config_json", "{}"))
        except Exception:
            job_dict["config"] = {}
        return job_dict


async def list_jobs(db_path: Path, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """List recent jobs with pagination."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        jobs: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            try:
                d["config"] = json.loads(d.get("config_json", "{}"))
            except Exception:
                d["config"] = {}
            jobs.append(d)
        return jobs


async def update_job_progress(
    db_path: Path,
    job_id: str,
    current_page: int,
    total_pages: int,
    engine_used: str,
) -> None:
    """Update ongoing progress for a job asynchronously."""
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            """
            UPDATE jobs
            SET status = 'processing',
                current_page = ?,
                total_pages = ?,
                engine_used = ?
            WHERE id = ?
            """,
            (current_page, total_pages, engine_used, job_id),
        )
        await db.commit()


def sync_update_job_progress(
    db_path: Path,
    job_id: str,
    current_page: int,
    total_pages: int,
    engine_used: str,
) -> None:
    """Update ongoing progress synchronously from inside worker threads."""
    import sqlite3

    with sqlite3.connect(str(db_path), timeout=15.0) as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = 'processing',
                current_page = ?,
                total_pages = ?,
                engine_used = ?
            WHERE id = ?
            """,
            (current_page, total_pages, engine_used, job_id),
        )


async def update_job_status(
    db_path: Path,
    job_id: str,
    status: str,
    output_dir: str = "",
    markdown_path: str = "",
    error_message: str = "",
    total_pages: int | None = None,
) -> None:
    """Update job terminal status ('completed', 'failed', 'cancelled')."""
    now_iso = (
        datetime.now(UTC).isoformat() if status in ("completed", "failed", "cancelled") else ""
    )
    async with aiosqlite.connect(str(db_path)) as db:
        if total_pages is not None:
            await db.execute(
                """
                UPDATE jobs
                SET status = ?,
                    output_dir = CASE WHEN ? != '' THEN ? ELSE output_dir END,
                    markdown_path = CASE WHEN ? != '' THEN ? ELSE markdown_path END,
                    error_message = ?,
                    completed_at = ?,
                    total_pages = ?
                WHERE id = ?
                """,
                (
                    status,
                    output_dir,
                    output_dir,
                    markdown_path,
                    markdown_path,
                    error_message,
                    now_iso,
                    total_pages,
                    job_id,
                ),
            )
        else:
            await db.execute(
                """
                UPDATE jobs
                SET status = ?,
                    output_dir = CASE WHEN ? != '' THEN ? ELSE output_dir END,
                    markdown_path = CASE WHEN ? != '' THEN ? ELSE markdown_path END,
                    error_message = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    output_dir,
                    output_dir,
                    markdown_path,
                    markdown_path,
                    error_message,
                    now_iso,
                    job_id,
                ),
            )
        await db.commit()


async def delete_job(db_path: Path, job_id: str) -> None:
    """Delete a job record from the database."""
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        await db.commit()
