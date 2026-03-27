"""Decorators and context managers for test enrichment."""
import time
from contextlib import contextmanager

from .context import StepData, get_current


@contextmanager
def step(name: str, params: dict | None = None):
    """Context manager for test steps with optional parameters."""
    ctx = get_current()
    s = StepData(name=name, _start_ms=time.perf_counter() * 1000)
    if params:
        s.parameters = [{"name": k, "value": str(v)} for k, v in params.items()]

    if ctx:
        ctx._step_stack.append(s)

    try:
        yield s
        s.status = "passed"
    except Exception as e:
        s.status = "failed"
        s.status_details = {"message": str(e), "trace": ""}
        raise
    finally:
        s.duration_ms = int(time.perf_counter() * 1000 - s._start_ms)
        if ctx:
            ctx._step_stack.pop()
            parent = ctx._step_stack[-1] if ctx._step_stack else None
            if parent:
                parent.steps.append(s)
            else:
                ctx.steps.append(s)


def feature(name: str):
    """Decorator to mark test with feature label."""
    def decorator(func):
        func._el_feature = name
        return func
    return decorator


def story(name: str):
    """Decorator to mark test with story label."""
    def decorator(func):
        func._el_story = name
        return func
    return decorator


def severity(level: str):
    """Decorator to mark test severity (blocker, critical, normal, minor, trivial)."""
    def decorator(func):
        func._el_severity = level
        return func
    return decorator


def link(url: str, name: str = "", link_type: str = ""):
    """Decorator to attach a link to test."""
    def decorator(func):
        if not hasattr(func, "_el_links"):
            func._el_links = []
        func._el_links.append({"url": url, "name": name, "type": link_type})
        return func
    return decorator


def attach(name: str, body: str, attachment_type: str = "text/plain"):
    """Attach data to current test context."""
    ctx = get_current()
    if ctx:
        ctx.attachments.append({
            "name": name,
            "body": body,
            "type": attachment_type,
        })
