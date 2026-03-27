"""Pytest plugin hooks for ErrorLens reporting."""
import logging
import time

from .client import ELClient
from .context import StepData, TestContext, clear_current, get_current, set_current

logger = logging.getLogger(__name__)

BATCH_SIZE = 5

_buffer: list[dict] = []
_client: ELClient | None = None
_launch_id: str = ""
_total_collected: int = 0
_started: bool = False


def pytest_collection_modifyitems(session, config, items):
    """After collection is done, start streaming launch."""
    global _client, _launch_id, _started
    _client = ELClient.from_env()
    if not _client:
        return
    _launch_id = _client.start_launch(len(items))
    _started = bool(_launch_id)
    if _started:
        logger.info(f"errorlens: launch started {_launch_id} ({len(items)} tests)")


def pytest_runtest_setup(item):
    """Initialize test context before each test."""
    ctx = TestContext(
        name=item.name,
        full_name=f"{item.module.__name__}::{item.name}",
        _start_ms=time.perf_counter() * 1000,
    )
    ctx.markers = [m.name for m in item.iter_markers()]
    if hasattr(item, "callspec"):
        ctx.parameters = [
            {"name": k, "value": str(v)} for k, v in item.callspec.params.items()
        ]
    fn = item.function
    cls = item.cls
    ctx.feature = getattr(fn, "_el_feature", "") or getattr(cls, "_el_feature", "")
    ctx.story = getattr(fn, "_el_story", "") or getattr(cls, "_el_story", "")
    ctx.severity = getattr(fn, "_el_severity", "") or getattr(cls, "_el_severity", "normal")
    ctx.links = getattr(fn, "_el_links", []) or getattr(cls, "_el_links", [])
    set_current(ctx)


def pytest_runtest_logreport(report):
    """Collect test result and flush buffer every BATCH_SIZE tests."""
    ctx = get_current()
    if not ctx:
        return
    if report.when == "call":
        if report.failed:
            ctx.status = "failed"
            ctx.status_details = {
                "message": str(report.longrepr) if report.longrepr else "",
                "trace": "",
            }
        elif report.skipped:
            ctx.status = "skipped"
    if report.when == "teardown":
        ctx.duration_ms = int(time.perf_counter() * 1000 - ctx._start_ms)
        _buffer.append(_ctx_to_dict(ctx))
        clear_current()

        global _total_collected
        _total_collected += 1

        if len(_buffer) >= BATCH_SIZE:
            _flush_buffer()


def pytest_sessionfinish(session, exitstatus):
    """Flush remaining buffer and finalize launch."""
    _flush_buffer()
    if _client and _launch_id:
        _client.finish_launch(_launch_id)
        logger.info(f"errorlens: launch finished {_launch_id}")


def _flush_buffer():
    """Send buffered tests as a batch."""
    global _buffer
    if not _buffer or not _client or not _launch_id:
        return
    batch = _buffer[:]
    _buffer = []
    _client.send_batch(_launch_id, batch)


def _step_to_dict(s: StepData) -> dict:
    """Convert StepData to dict recursively."""
    return {
        "name": s.name,
        "status": s.status,
        "duration_ms": s.duration_ms,
        "parameters": s.parameters,
        "steps": [_step_to_dict(sub) for sub in s.steps],
        "attachments": s.attachments,
        "status_details": s.status_details,
    }


def _ctx_to_dict(ctx: TestContext) -> dict:
    """Convert TestContext to serializable dict."""
    return {
        "name": ctx.name,
        "full_name": ctx.full_name,
        "status": ctx.status,
        "duration_ms": ctx.duration_ms,
        "markers": ctx.markers,
        "parameters": ctx.parameters,
        "feature": ctx.feature,
        "story": ctx.story,
        "severity": ctx.severity,
        "links": ctx.links,
        "steps": [_step_to_dict(s) for s in ctx.steps],
        "attachments": ctx.attachments,
        "status_details": ctx.status_details,
    }
