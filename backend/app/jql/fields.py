"""JQL field descriptors — mapping JQL names to SQLAlchemy columns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import InstrumentedAttribute

from app.models.db_models import Task, TaskActivity, TaskStatus, TaskType
from app.models.user import User


@dataclass(frozen=True)
class FieldDescriptor:
    """Describes how a JQL field maps to the database."""

    column: Any  # InstrumentedAttribute or special marker
    lookup_table: type | None = None
    lookup_field: str | None = None
    supports_history: bool = False
    is_text_search: bool = False
    is_json: bool = False


# Registry: canonical JQL name → descriptor
FIELD_REGISTRY: dict[str, FieldDescriptor] = {
    "type": FieldDescriptor(
        column=Task.type_id,
        lookup_table=TaskType,
        lookup_field="slug",
        supports_history=True,
    ),
    "status": FieldDescriptor(
        column=Task.status_id,
        lookup_table=TaskStatus,
        lookup_field="slug",
        supports_history=True,
    ),
    "priority": FieldDescriptor(column=Task.priority, supports_history=True),
    "severity": FieldDescriptor(column=Task.severity),
    "assignee": FieldDescriptor(
        column=Task.assignee_id,
        lookup_table=User,
        lookup_field="username",
        supports_history=True,
    ),
    "reporter": FieldDescriptor(
        column=Task.reporter_id,
        lookup_table=User,
        lookup_field="username",
    ),
    "project": FieldDescriptor(
        column=Task.project_id,
        lookup_table=None,
        lookup_field=None,
    ),
    "created": FieldDescriptor(column=Task.created_at),
    "updated": FieldDescriptor(column=Task.updated_at),
    "due": FieldDescriptor(column=Task.due_date),
    "summary": FieldDescriptor(column=Task.title),
    "description": FieldDescriptor(column=Task.description),
    "text": FieldDescriptor(column=None, is_text_search=True),
    "label": FieldDescriptor(column=Task.labels, is_json=True),
    "parent": FieldDescriptor(column=Task.parent_id),
    "environment": FieldDescriptor(column=Task.environment),
    "estimated": FieldDescriptor(column=Task.estimated_hours),
    "id": FieldDescriptor(column=Task.human_id),
}

# Jira-compatible aliases → canonical name
FIELD_ALIASES: dict[str, str] = {
    "issuetype": "type",
    "duedate": "due",
    "labels": "label",
}

# All known field names (canonical + aliases)
ALL_FIELD_NAMES: set[str] = set(FIELD_REGISTRY.keys()) | set(FIELD_ALIASES.keys())


def resolve_field(name: str) -> tuple[str, FieldDescriptor]:
    """Resolve a JQL field name (with alias support) to (canonical_name, descriptor)."""
    canonical = FIELD_ALIASES.get(name.lower(), name.lower())
    descriptor = FIELD_REGISTRY.get(canonical)
    if descriptor is None:
        from app.jql.exceptions import JQLFieldError
        raise JQLFieldError(canonical)
    return canonical, descriptor
