"""Tests for automation service — rule matching and template rendering."""

import pytest
from unittest.mock import MagicMock

from app.services.automation_service import (
    build_context,
    match_rules,
    render_template,
)


class FakeRule:
    """Minimal mock for AutomationRule."""
    def __init__(self, trigger_event, trigger_conditions=None, task_type_id=None):
        self.trigger_event = trigger_event
        self.trigger_conditions = trigger_conditions
        self.task_type_id = task_type_id


class TestMatchRules:
    def test_matches_basic_event(self):
        rules = [FakeRule("task.status_changed")]
        event = {"type": "task.status_changed", "payload": {}}
        assert len(match_rules(event, rules)) == 1

    def test_no_match_wrong_event(self):
        rules = [FakeRule("task.assigned")]
        event = {"type": "task.status_changed", "payload": {}}
        assert len(match_rules(event, rules)) == 0

    def test_matches_to_status_id(self):
        rules = [FakeRule("task.status_changed", {"to_status_id": "s1"})]
        event = {"type": "task.status_changed", "payload": {"to_status_id": "s1"}}
        assert len(match_rules(event, rules)) == 1

    def test_no_match_wrong_to_status(self):
        rules = [FakeRule("task.status_changed", {"to_status_id": "s1"})]
        event = {"type": "task.status_changed", "payload": {"to_status_id": "s2"}}
        assert len(match_rules(event, rules)) == 0

    def test_matches_from_status_id(self):
        rules = [FakeRule("task.status_changed", {"from_status_id": "s0"})]
        event = {"type": "task.status_changed", "payload": {"from_status_id": "s0"}}
        assert len(match_rules(event, rules)) == 1

    def test_matches_both_statuses(self):
        rules = [FakeRule("task.status_changed", {"from_status_id": "s0", "to_status_id": "s1"})]
        event = {"type": "task.status_changed", "payload": {"from_status_id": "s0", "to_status_id": "s1"}}
        assert len(match_rules(event, rules)) == 1

    def test_no_match_task_type_filter(self):
        rules = [FakeRule("task.status_changed", task_type_id="type-bug")]
        event = {"type": "task.status_changed", "payload": {"type_id": "type-task"}}
        assert len(match_rules(event, rules)) == 0

    def test_matches_task_type_filter(self):
        rules = [FakeRule("task.status_changed", task_type_id="type-bug")]
        event = {"type": "task.status_changed", "payload": {"type_id": "type-bug"}}
        assert len(match_rules(event, rules)) == 1

    def test_null_task_type_matches_all(self):
        rules = [FakeRule("task.status_changed", task_type_id=None)]
        event = {"type": "task.status_changed", "payload": {"type_id": "any"}}
        assert len(match_rules(event, rules)) == 1

    def test_multiple_rules_partial_match(self):
        rules = [
            FakeRule("task.status_changed", {"to_status_id": "s1"}),
            FakeRule("task.status_changed", {"to_status_id": "s2"}),
            FakeRule("task.assigned"),
        ]
        event = {"type": "task.status_changed", "payload": {"to_status_id": "s1"}}
        matched = match_rules(event, rules)
        assert len(matched) == 1
        assert matched[0].trigger_conditions["to_status_id"] == "s1"


class TestBuildContext:
    def test_builds_task_context(self):
        task = MagicMock()
        task.human_id = "EL-42"
        task.title = "Fix bug"
        task.id = "abc-123"

        ctx = build_context(task, {})
        assert ctx["task.human_id"] == "EL-42"
        assert ctx["task.title"] == "Fix bug"
        assert ctx["task.id"] == "abc-123"

    def test_builds_pipeline_context(self):
        task = MagicMock()
        task.human_id = "EL-1"
        task.title = "Test"
        task.id = "id1"

        pipeline = {"web_url": "https://gl.com/p/1", "status": "success", "id": 42}
        ctx = build_context(task, {}, pipeline)
        assert ctx["pipeline.url"] == "https://gl.com/p/1"
        assert ctx["pipeline.status"] == "success"
        assert ctx["pipeline.id"] == "42"

    def test_handles_none_human_id(self):
        task = MagicMock()
        task.human_id = None
        task.title = "Test"
        task.id = "id1"

        ctx = build_context(task, {})
        assert ctx["task.human_id"] == ""


class TestRenderTemplate:
    def test_renders_simple_template(self):
        ctx = {"task.human_id": "EL-1", "task.title": "Fix"}
        result = render_template("Task {{task.human_id}}: {{task.title}}", ctx)
        assert result == "Task EL-1: Fix"

    def test_renders_pipeline_url(self):
        ctx = {"pipeline.url": "https://gl.com/p/42"}
        result = render_template("See {{pipeline.url}}", ctx)
        assert result == "See https://gl.com/p/42"

    def test_no_placeholders(self):
        result = render_template("No templates here", {"a": "b"})
        assert result == "No templates here"

    def test_unknown_placeholder_left_as_is(self):
        result = render_template("{{unknown.var}}", {"task.id": "1"})
        assert result == "{{unknown.var}}"
