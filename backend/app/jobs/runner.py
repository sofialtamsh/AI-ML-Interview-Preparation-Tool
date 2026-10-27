"""The job queue and worker.

Jobs are rows in `jobs`. A worker claims the oldest queued job with `FOR UPDATE SKIP LOCKED`, so
several workers never run the same job. Handlers report progress and log lines through a
`JobContext`, which commits as it goes so the console shows live progress and the history survives
a crash. Jobs are only ever created by an explicit admin action; nothing here schedules work.
"""

import logging
import threading
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.errors import UserFacingError
from app.core.security import utcnow
from app.models import Job, JobEvent, JobEventLevel, JobKind, JobStatus

log = logging.getLogger(__name__)

# A running job whose heartbeat is older than this is treated as interrupted (e.g. the server
# restarted mid-run). Handlers beat at least once per record, so this is generous.
STALE_AFTER = timedelta(minutes=10)
POLL_SECONDS = 2.0


class JobCancelled(Exception):
    pass


class JobContext:
    def __init__(self, db: Session, job: Job) -> None:
        self.db = db
        self.job = job
        self.warnings = 0

    def log(self, message: str, level: JobEventLevel = JobEventLevel.INFO) -> None:
        self.db.add(JobEvent(job_id=self.job.id, level=level, message=message[:1000]))
        self.job.heartbeat_at = utcnow()
        self.db.commit()

    def info(self, message: str) -> None:
        self.log(message)

    def warn(self, message: str) -> None:
        self.warnings += 1
        self.log(message, JobEventLevel.WARNING)

    def report(self, *, done: int | None = None, result: dict[str, Any] | None = None) -> None:
        if done is not None:
            self.job.progress_done = done
        if result is not None:
            self.job.result = dict(result)  # a new object, so SQLAlchemy sees the change
        self.job.heartbeat_at = utcnow()
        self.db.commit()

    def check_cancelled(self) -> None:
        if self.db.scalar(select(Job.cancel_requested).where(Job.id == self.job.id)):
            raise JobCancelled


Handler = Callable[[JobContext], None]


def _handlers() -> dict[JobKind, Handler]:
    from app.sources.service import run_source_fetch

    return {JobKind.SOURCE_FETCH: run_source_fetch}


def claim_next_job(db: Session) -> Job | None:
    job = db.scalars(
        select(Job)
        .where(Job.status == JobStatus.QUEUED, Job.kind.in_(list(_handlers())))
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True, of=Job)
    ).first()
    if job is None:
        return None
    if job.cancel_requested:
        job.status = JobStatus.CANCELLED
        job.finished_at = utcnow()
        db.add(
            JobEvent(job_id=job.id, level=JobEventLevel.INFO, message="Stopped before it began.")
        )
        db.commit()
        return claim_next_job(db)
    now = utcnow()
    job.status = JobStatus.RUNNING
    job.started_at = job.heartbeat_at = now
    job.attempts += 1
    db.commit()
    return job


def execute_job(job_id: Any) -> JobStatus:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            raise LookupError(f"Job {job_id} not found")
        ctx = JobContext(db, job)
        error: str | None = None
        try:
            _handlers()[job.kind](ctx)
            status = JobStatus.COMPLETED_WITH_ERRORS if ctx.warnings else JobStatus.SUCCEEDED
        except JobCancelled:
            status = JobStatus.CANCELLED
        except UserFacingError as exc:
            status, error = JobStatus.FAILED, str(exc)
        except Exception as exc:
            log.exception("Job %s (%s) crashed", job_id, job.kind)
            status = JobStatus.FAILED
            error = f"Unexpected error ({type(exc).__name__}). Details are in the server log."

        db.rollback()  # discard anything half-written by a failed handler
        job = db.get(Job, job_id)
        assert job is not None  # noqa: S101 (it was loaded above and jobs are never deleted)
        job.status = status
        job.error = error
        job.finished_at = utcnow()
        message = {
            JobStatus.SUCCEEDED: "Finished.",
            JobStatus.COMPLETED_WITH_ERRORS: "Finished with some problems (see above).",
            JobStatus.CANCELLED: "Stopped by an admin.",
            JobStatus.FAILED: f"Failed: {error}",
        }[status]
        db.add(
            JobEvent(
                job_id=job.id,
                level=JobEventLevel.ERROR if status is JobStatus.FAILED else JobEventLevel.INFO,
                message=message[:1000],
            )
        )
        db.commit()
        return status


def run_pending_jobs(limit: int | None = None) -> int:
    """Run queued jobs until none are left (or `limit` ran). Returns how many ran."""
    ran = 0
    while limit is None or ran < limit:
        with SessionLocal() as db:
            job = claim_next_job(db)
            job_id = job.id if job else None
        if job_id is None:
            return ran
        execute_job(job_id)
        ran += 1
    return ran


def recover_stale_jobs() -> int:
    """Mark jobs whose worker died (no heartbeat for STALE_AFTER) as failed."""
    cutoff = utcnow() - STALE_AFTER
    with SessionLocal() as db:
        stale = db.scalars(
            select(Job)
            .where(
                Job.status == JobStatus.RUNNING,
                or_(Job.heartbeat_at < cutoff, Job.heartbeat_at.is_(None)),
            )
            .with_for_update(skip_locked=True, of=Job)
        ).all()
        for job in stale:
            job.status = JobStatus.FAILED
            job.finished_at = utcnow()
            job.error = (
                "Interrupted: the server stopped while this job was running. Start it again."
            )
            db.add(JobEvent(job_id=job.id, level=JobEventLevel.ERROR, message=job.error))
        db.commit()
        return len(stale)


class Worker:
    """Runs jobs in a background thread. Woken immediately when a job is queued in-process, and
    polls so jobs queued by other processes are picked up too."""

    def __init__(self, poll_seconds: float = POLL_SECONDS) -> None:
        self._poll = poll_seconds
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="ipp-job-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout)

    def notify(self) -> None:
        self._wake.set()

    def _loop(self) -> None:
        last_recovery = None
        while not self._stop.is_set():
            try:
                now = utcnow()
                if last_recovery is None or now - last_recovery > timedelta(minutes=1):
                    if recovered := recover_stale_jobs():
                        log.warning("Marked %d interrupted job(s) as failed", recovered)
                    last_recovery = now
                if run_pending_jobs(limit=1):
                    continue
            except Exception:
                log.exception("Job worker loop error")
            self._wake.wait(self._poll)
            self._wake.clear()


_worker: Worker | None = None


def start_worker() -> Worker:
    global _worker
    _worker = Worker()
    _worker.start()
    return _worker


def stop_worker() -> None:
    global _worker
    if _worker:
        _worker.stop()
        _worker = None


def notify_worker() -> None:
    """Call after committing a new job so an in-process worker starts it right away."""
    if _worker:
        _worker.notify()
