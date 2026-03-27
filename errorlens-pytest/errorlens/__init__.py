"""ErrorLens pytest plugin — native test reporting."""
from errorlens.decorators import (
    attach, attach_file, attach_html, attach_json, attach_screenshot, attach_text,
    description, epic, feature, flaky, id, issue, known_issue,
    link, owner, parent_suite, severity, step, story, suite, tag, testcase, title,
)
from errorlens.dynamic import dynamic

__all__ = [
    "step", "feature", "story", "severity", "link", "attach",
    "title", "description", "epic", "suite", "parent_suite",
    "tag", "id", "owner", "issue", "testcase", "flaky", "known_issue",
    "attach_json", "attach_text", "attach_html", "attach_file", "attach_screenshot",
    "dynamic",
]
__version__ = "2.0.0"
