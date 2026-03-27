"""Pytest plugin hooks for ErrorLens reporting."""
import inspect
import logging
import os
import pathlib
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
_verbose: bool = False
_no_report: bool = False


def _read_pyproject_config() -> dict:
    """Read [tool.errorlens] or [tool.pytest.ini_options] from pyproject.toml."""
    for directory in [pathlib.Path.cwd(), *pathlib.Path.cwd().parents]:
        pyproject = directory / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError:
                    return {}
            data = tomllib.loads(pyproject.read_text())
            el_section = data.get("tool", {}).get("errorlens", {})
            pytest_section = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
            return {**pytest_section, **el_section}
    return {}


def pytest_addoption(parser):
    group = parser.getgroup("errorlens", "ErrorLens reporting")
    group.addoption("--el-no-report", action="store_true", default=False,
                    help="Disable ErrorLens reporting (tests still run)")
    group.addoption("--el-launch-name", action="store", default=None,
                    help="Override EL_LAUNCH_NAME")
    group.addoption("--el-env", action="store", default=None,
                    help="Override EL_ENVIRONMENT")
    group.addoption("--el-branch", action="store", default=None,
                    help="Override EL_BRANCH")
    group.addoption("--el-verbose", action="store_true", default=False,
                    help="Print step results to console during test run")


def pytest_configure(config):
    """Apply CLI flags and read pyproject.toml config."""
    global _verbose, _no_report

    _no_report = getattr(config.option, "el_no_report", False)
    _verbose = getattr(config.option, "el_verbose", False)

    # CLI flags override env vars
    if getattr(config.option, "el_launch_name", None):
        os.environ["EL_LAUNCH_NAME"] = config.option.el_launch_name
    if getattr(config.option, "el_env", None):
        os.environ["EL_ENVIRONMENT"] = config.option.el_env
    if getattr(config.option, "el_branch", None):
        os.environ["EL_BRANCH"] = config.option.el_branch

    # Read pyproject.toml if env vars not set
    pyproject_cfg = _read_pyproject_config()
    ini_keys = {
        "el_url": "EL_URL", "el_token": "EL_TOKEN",
        "el_project_id": "EL_PROJECT_ID", "el_launch_name": "EL_LAUNCH_NAME",
        "el_branch": "EL_BRANCH", "el_environment": "EL_ENVIRONMENT",
        "el_pipeline_id": "EL_PIPELINE_ID", "el_batch_size": "EL_BATCH_SIZE",
        "el_timeout": "EL_TIMEOUT",
    }
    for ini_key, env_key in ini_keys.items():
        if not os.environ.get(env_key):
            val = pyproject_cfg.get(ini_key)
            if val:
                os.environ[env_key] = str(val)


def pytest_collection_modifyitems(session, config, items):
    """After collection is done, start streaming launch."""
    global _client, _launch_id, _started
    if _no_report:
        logger.warning("errorlens: reporting disabled (--el-no-report)")
        return
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

    # Existing fields
    ctx.feature = getattr(fn, "_el_feature", "") or getattr(cls, "_el_feature", "")
    ctx.story = getattr(fn, "_el_story", "") or getattr(cls, "_el_story", "")
    ctx.severity = getattr(fn, "_el_severity", "") or getattr(cls, "_el_severity", "normal")
    ctx.links = getattr(fn, "_el_links", []) or getattr(cls, "_el_links", [])

    # New fields v2.0
    ctx.title = getattr(fn, "_el_title", "") or getattr(cls, "_el_title", "")
    ctx.epic = getattr(fn, "_el_epic", "") or getattr(cls, "_el_epic", "")
    ctx.suite = getattr(fn, "_el_suite", "") or getattr(cls, "_el_suite", "")
    ctx.parent_suite = getattr(fn, "_el_parent_suite", "") or getattr(cls, "_el_parent_suite", "")
    ctx.owner = getattr(fn, "_el_owner", "") or getattr(cls, "_el_owner", "")
    ctx.test_id = getattr(fn, "_el_test_id", "") or getattr(cls, "_el_test_id", "")
    ctx.flaky = getattr(fn, "_el_flaky", False) or getattr(cls, "_el_flaky", False)
    ctx.known_issue = getattr(fn, "_el_known_issue", "") or getattr(cls, "_el_known_issue", "")

    # Tags: merge from class and function (deduplicated, order preserved)
    fn_tags = getattr(fn, "_el_tags", [])
    cls_tags = getattr(cls, "_el_tags", []) if cls else []
    ctx.tags = list(dict.fromkeys(cls_tags + fn_tags))

    # Description: explicit decorator > docstring
    ctx.description = (getattr(fn, "_el_description", "")
                       or getattr(cls, "_el_description", "")
                       or (inspect.getdoc(fn) or ""))

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

        if _verbose and ctx.steps:
            _print_steps_verbose(ctx.steps, indent=0)

        _buffer.append(_ctx_to_dict(ctx))
        clear_current()

        global _total_collected
        _total_collected += 1

        if len(_buffer) >= BATCH_SIZE:
            _flush_buffer()


def _print_steps_verbose(steps: list, indent: int) -> None:
    prefix = "  " * indent
    for s in steps:
        icon = "✓" if s.status == "passed" else "✗"
        print(f"[EL] {prefix}{icon} STEP ({s.duration_ms}ms): {s.name}")
        if s.steps:
            _print_steps_verbose(s.steps, indent + 1)


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
        # v2.0
        "title": ctx.title,
        "description": ctx.description,
        "epic": ctx.epic,
        "suite": ctx.suite,
        "parent_suite": ctx.parent_suite,
        "tags": ctx.tags,
        "owner": ctx.owner,
        "test_id": ctx.test_id,
        "flaky": ctx.flaky,
        "known_issue": ctx.known_issue,
        "retry_count": ctx.retry_count,
        # existing
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
