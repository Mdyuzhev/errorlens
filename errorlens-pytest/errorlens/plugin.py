"""Pytest plugin hooks for ErrorLens reporting."""
import time
from dataclasses import asdict

from .client import ELClient
from .context import TestContext, clear_current, get_current, set_current, StepData

_results: list[dict] = []


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
    ctx.feature = getattr(fn, "_el_feature", "")
    ctx.story = getattr(fn, "_el_story", "")
    ctx.severity = getattr(fn, "_el_severity", "normal")
    ctx.links = getattr(fn, "_el_links", [])
    set_current(ctx)


def pytest_runtest_logreport(report):
    """Collect test result on each phase."""
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
        _results.append(_ctx_to_dict(ctx))
        clear_current()


def pytest_sessionfinish(session, exitstatus):
    """Send collected results to ErrorLens server."""
    if not _results:
        return
    client = ELClient.from_env()
    if not client:
        return
    client.send(_results)


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
