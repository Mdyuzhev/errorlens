"""Decorators and context managers for test enrichment."""
import functools
import inspect
import json as _json
import mimetypes as _mimetypes
import time

from .context import StepData, get_current


class _StepManager:
    """Universal step manager.

    Usage:
      with el.step("name"):          # sync context manager
      async with el.step("name"):    # async context manager
      @el.step("Create {username}")  # function decorator with interpolation
      ctx = el.step.start("name")    # explicit start
      el.step.stop(ctx)              # explicit stop
    """

    def __call__(self, name: str, params: dict | None = None):
        return _StepContext(name, params)

    def start(self, name: str, params: dict | None = None) -> StepData:
        ctx = get_current()
        s = StepData(name=name, _start_ms=time.perf_counter() * 1000)
        if params:
            s.parameters = [{"name": k, "value": str(v)} for k, v in params.items()]
        if ctx:
            ctx._step_stack.append(s)
        return s

    def stop(self, step_data: StepData, status: str = "passed", message: str = "") -> None:
        step_data.duration_ms = int(time.perf_counter() * 1000 - step_data._start_ms)
        step_data.status = status
        if message:
            step_data.status_details = {"message": message, "trace": ""}
        ctx = get_current()
        if ctx:
            if ctx._step_stack and ctx._step_stack[-1] is step_data:
                ctx._step_stack.pop()
            parent = ctx._step_stack[-1] if ctx._step_stack else None
            if parent:
                parent.steps.append(step_data)
            else:
                ctx.steps.append(step_data)


class _StepContext:
    """Supports sync (with), async (async with), and decorator modes."""

    def __init__(self, name: str, params: dict | None = None):
        self._name = name
        self._params = params
        self._step: StepData | None = None

    def __call__(self, func):
        name_template = self._name
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                resolved = _resolve_step_name(name_template, func, args, kwargs)
                async with _StepContext(resolved, self._params):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                resolved = _resolve_step_name(name_template, func, args, kwargs)
                with _StepContext(resolved, self._params):
                    return func(*args, **kwargs)
            return sync_wrapper

    def __enter__(self) -> StepData:
        ctx = get_current()
        self._step = StepData(name=self._name, _start_ms=time.perf_counter() * 1000)
        if self._params:
            self._step.parameters = [{"name": k, "value": str(v)}
                                      for k, v in self._params.items()]
        if ctx:
            ctx._step_stack.append(self._step)
        return self._step

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._step is None:
            return False
        self._step.duration_ms = int(time.perf_counter() * 1000 - self._step._start_ms)
        if exc_type is not None:
            self._step.status = "failed"
            self._step.status_details = {"message": str(exc_val), "trace": ""}
        else:
            self._step.status = "passed"
        ctx = get_current()
        if ctx:
            if ctx._step_stack and ctx._step_stack[-1] is self._step:
                ctx._step_stack.pop()
            parent = ctx._step_stack[-1] if ctx._step_stack else None
            if parent:
                parent.steps.append(self._step)
            else:
                ctx.steps.append(self._step)
        return False

    async def __aenter__(self) -> StepData:
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)


def _resolve_step_name(template: str, func, args, kwargs) -> str:
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return template.format_map(bound.arguments)
    except Exception:
        return template


# Singleton — replaces the old @contextmanager step
step = _StepManager()


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


def title(name: str):
    def decorator(func):
        func._el_title = name
        return func
    return decorator


def description(text: str):
    def decorator(func):
        func._el_description = text
        return func
    return decorator


def epic(name: str):
    def decorator(func):
        func._el_epic = name
        return func
    return decorator


def suite(name: str):
    def decorator(func):
        func._el_suite = name
        return func
    return decorator


def parent_suite(name: str):
    def decorator(func):
        func._el_parent_suite = name
        return func
    return decorator


def tag(*tags: str):
    def decorator(func):
        existing = getattr(func, "_el_tags", [])
        func._el_tags = existing + list(tags)
        return func
    return decorator


def id(test_id: str):
    def decorator(func):
        func._el_test_id = test_id
        return func
    return decorator


def owner(name: str):
    def decorator(func):
        func._el_owner = name
        return func
    return decorator


def issue(url: str, name: str = ""):
    def decorator(func):
        if not hasattr(func, "_el_links"):
            func._el_links = []
        func._el_links.append({"url": url, "name": name or url, "type": "issue"})
        return func
    return decorator


def testcase(url: str, name: str = ""):
    def decorator(func):
        if not hasattr(func, "_el_links"):
            func._el_links = []
        func._el_links.append({"url": url, "name": name or url, "type": "testcase"})
        return func
    return decorator


def flaky(reason: str = ""):
    def decorator(func):
        func._el_flaky = True
        func._el_flaky_reason = reason
        return func
    return decorator


def known_issue(issue_id: str, reason: str = ""):
    def decorator(func):
        func._el_known_issue = issue_id
        func._el_known_issue_reason = reason
        return func
    return decorator


def attach_json(name: str, obj, indent: int = 2) -> None:
    body = _json.dumps(obj, ensure_ascii=False, indent=indent, default=str)
    attach(name, body, "application/json")


def attach_text(name: str, text: str) -> None:
    attach(name, text, "text/plain")


def attach_html(name: str, html: str) -> None:
    attach(name, html, "text/html")


def attach_screenshot(name: str, data: bytes) -> None:
    import base64
    attach(name, base64.b64encode(data).decode(), "image/png")


def attach_file(name: str, path: str, mime_type: str | None = None) -> None:
    import base64
    import pathlib
    p = pathlib.Path(path)
    if mime_type is None:
        guessed, _ = _mimetypes.guess_type(str(p))
        mime_type = guessed or "application/octet-stream"
    raw = p.read_bytes()
    ctx = get_current()
    if ctx:
        ctx.attachments.append({
            "name": name,
            "body": base64.b64encode(raw).decode(),
            "type": mime_type,
            "encoding": "base64",
        })
