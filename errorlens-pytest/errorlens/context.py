"""ContextVar-based storage for current test state."""
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class StepData:
    name: str
    status: str = "passed"
    duration_ms: int = 0
    parameters: list[dict] = field(default_factory=list)
    steps: list["StepData"] = field(default_factory=list)
    attachments: list[dict] = field(default_factory=list)
    status_details: dict = field(default_factory=dict)
    _start_ms: float = 0.0


@dataclass
class TestContext:
    name: str = ""
    full_name: str = ""
    status: str = "passed"
    duration_ms: int = 0
    markers: list[str] = field(default_factory=list)
    parameters: list[dict] = field(default_factory=list)
    feature: str = ""
    story: str = ""
    severity: str = "normal"
    links: list[dict] = field(default_factory=list)
    steps: list[StepData] = field(default_factory=list)
    attachments: list[dict] = field(default_factory=list)
    status_details: dict = field(default_factory=dict)
    _step_stack: list[StepData] = field(default_factory=list)
    _start_ms: float = 0.0


_current_test: ContextVar[TestContext | None] = ContextVar("_current_test", default=None)


def get_current() -> TestContext | None:
    return _current_test.get()


def set_current(ctx: TestContext) -> None:
    _current_test.set(ctx)


def clear_current() -> None:
    _current_test.set(None)
