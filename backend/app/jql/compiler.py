"""JQL Compiler — parse JQL string and produce SQLAlchemy WHERE clause."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from lark import Lark, Token, Tree, UnexpectedInput
from sqlalchemy import and_, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jql.exceptions import (
    JQLFieldError,
    JQLFunctionError,
    JQLSyntaxError,
    JQLValueError,
)
from app.jql.fields import (
    FieldDescriptor,
    resolve_field,
)
from app.models.db_models import Task, TaskActivity

_GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"
_parser: Lark | None = None


def _get_parser() -> Lark:
    global _parser
    if _parser is None:
        _parser = Lark(
            _GRAMMAR_PATH.read_text(encoding="utf-8"),
            parser="earley",
            ambiguity="resolve",
        )
    return _parser


# --- Relative date parsing ---
_REL_DATE_RE = re.compile(r"^([+-])(\d+)([dwhmDWHM])$")
_UNIT_MAP = {"d": "days", "w": "weeks", "h": "hours", "m": "minutes"}


def _parse_relative_date(token: str) -> datetime:
    m = _REL_DATE_RE.match(token)
    if not m:
        raise JQLValueError("date", token)
    sign, amount, unit = m.group(1), int(m.group(2)), m.group(3).lower()
    delta = timedelta(**{_UNIT_MAP[unit]: amount})
    if sign == "-":
        return datetime.utcnow() - delta
    return datetime.utcnow() + delta


# --- Known functions ---
_KNOWN_FUNCTIONS = {
    "currentuser", "now", "startofday", "endofday",
    "startofweek", "startofmonth", "membersof",
}


@dataclass
class JQLContext:
    """Runtime context for JQL compilation."""

    current_user_id: str
    project_id: str | None = None
    db: AsyncSession | None = None


@dataclass
class JQLResult:
    """Compilation result."""

    where_clause: Any  # SQLAlchemy BooleanClauseList
    order_clauses: list[Any] = field(default_factory=list)


class JQLCompiler:
    """Compile JQL string → SQLAlchemy WHERE clause."""

    def __init__(self) -> None:
        self._lookup_cache: dict[tuple[str, str], str | None] = {}

    async def compile(self, jql: str, context: JQLContext) -> JQLResult:
        """Parse and compile JQL string."""
        self._context = context
        self._lookup_cache.clear()

        try:
            tree = _get_parser().parse(jql)
        except UnexpectedInput as e:
            raise JQLSyntaxError(
                message=str(e),
                position=getattr(e, "pos_in_stream", None),
                line=getattr(e, "line", None),
            ) from e

        return await self._visit_query(tree)

    def parse_only(self, jql: str) -> Tree:
        """Parse JQL without compilation (for validation)."""
        try:
            return _get_parser().parse(jql)
        except UnexpectedInput as e:
            raise JQLSyntaxError(
                message=str(e),
                position=getattr(e, "pos_in_stream", None),
                line=getattr(e, "line", None),
            ) from e

    # --- Tree visitors ---

    async def _visit_query(self, tree: Tree) -> JQLResult:
        result = JQLResult(where_clause=None)
        for child in tree.children:
            if isinstance(child, Tree):
                if child.data == "query":
                    return await self._visit_query(child)
                elif child.data == "order_by":
                    result.order_clauses = await self._visit_order_by(child)
                else:
                    result.where_clause = await self._visit(child)
        return result

    async def _visit(self, node: Tree | Token) -> Any:
        if isinstance(node, Token):
            return node

        handler = getattr(self, f"_visit_{node.data}", None)
        if handler:
            return await handler(node)

        # Generic: AND/OR chain detection
        children = [c for c in node.children if isinstance(c, Tree)]
        if len(children) == 1:
            return await self._visit(children[0])

        # Default: visit all children and AND them
        clauses = []
        for child in node.children:
            if isinstance(child, Tree):
                clauses.append(await self._visit(child))
        if len(clauses) == 1:
            return clauses[0]
        return and_(*clauses) if clauses else True

    async def _visit_or_expr(self, node: Tree) -> Any:
        clauses = []
        for child in node.children:
            if isinstance(child, Tree):
                clauses.append(await self._visit(child))
        if len(clauses) == 1:
            return clauses[0]
        return or_(*clauses)

    async def _visit_and_expr(self, node: Tree) -> Any:
        clauses = []
        for child in node.children:
            if isinstance(child, Tree):
                clauses.append(await self._visit(child))
        if len(clauses) == 1:
            return clauses[0]
        return and_(*clauses)

    async def _visit_not_clause(self, node: Tree) -> Any:
        child = next(c for c in node.children if isinstance(c, Tree))
        return not_(await self._visit(child))

    async def _visit_comparison(self, node: Tree) -> Any:
        field_name = self._extract_field(node)
        op = self._extract_op(node)
        value = await self._extract_value(node, field_name)
        canonical, desc = resolve_field(field_name)
        column = desc.column
        resolved = await self._resolve_value(canonical, desc, value)

        ops = {
            "=": lambda c, v: c == v,
            "!=": lambda c, v: c != v,
            "<": lambda c, v: c < v,
            ">": lambda c, v: c > v,
            "<=": lambda c, v: c <= v,
            ">=": lambda c, v: c >= v,
        }
        return ops[op](column, resolved)

    async def _visit_in_condition(self, node: Tree) -> Any:
        field_name = self._extract_field(node)
        values = await self._extract_value_list(node, field_name)
        canonical, desc = resolve_field(field_name)
        resolved = [await self._resolve_value(canonical, desc, v) for v in values]
        return desc.column.in_(resolved)

    async def _visit_not_in_condition(self, node: Tree) -> Any:
        field_name = self._extract_field(node)
        values = await self._extract_value_list(node, field_name)
        canonical, desc = resolve_field(field_name)
        resolved = [await self._resolve_value(canonical, desc, v) for v in values]
        return desc.column.notin_(resolved)

    async def _visit_is_empty(self, node: Tree) -> Any:
        field_name = self._extract_field(node)
        _, desc = resolve_field(field_name)
        return desc.column.is_(None)

    async def _visit_is_not_empty(self, node: Tree) -> Any:
        field_name = self._extract_field(node)
        _, desc = resolve_field(field_name)
        return desc.column.isnot(None)

    async def _visit_contains_condition(self, node: Tree) -> Any:
        field_name = self._extract_field(node)
        value = await self._extract_value(node, field_name)
        canonical, desc = resolve_field(field_name)

        if desc.is_text_search:
            pattern = f"%{value}%"
            return or_(
                Task.title.ilike(pattern),
                Task.description.ilike(pattern),
            )
        return desc.column.ilike(f"%{value}%")

    async def _visit_not_contains_condition(self, node: Tree) -> Any:
        field_name = self._extract_field(node)
        value = await self._extract_value(node, field_name)
        canonical, desc = resolve_field(field_name)

        if desc.is_text_search:
            pattern = f"%{value}%"
            return and_(
                not_(Task.title.ilike(pattern)),
                not_(Task.description.ilike(pattern)),
            )
        return not_(desc.column.ilike(f"%{value}%"))

    async def _visit_was_condition(self, node: Tree) -> Any:
        field_name = self._extract_field(node)
        canonical, desc = resolve_field(field_name)
        if not desc.supports_history:
            raise JQLFieldError(f"{field_name} does not support WAS operator")
        value = await self._extract_value(node, field_name)
        resolved = await self._resolve_value(canonical, desc, value)

        subq = (
            select(TaskActivity.task_id)
            .where(
                TaskActivity.field_name == canonical,
                TaskActivity.old_value[canonical].as_string() == str(resolved),
            )
        )
        return Task.id.in_(subq)

    async def _visit_changed_condition(self, node: Tree) -> Any:
        field_name = self._extract_field(node)
        canonical, desc = resolve_field(field_name)
        if not desc.supports_history:
            raise JQLFieldError(f"{field_name} does not support CHANGED operator")

        subq = (
            select(TaskActivity.task_id)
            .where(TaskActivity.field_name == canonical)
        )
        return Task.id.in_(subq)

    async def _visit_order_by(self, node: Tree) -> list:
        clauses = []
        for child in node.children:
            if isinstance(child, Tree) and child.data == "order_field":
                field_name = self._extract_field(child)
                _, desc = resolve_field(field_name)
                col = desc.column
                direction = "asc"
                for token in child.children:
                    if isinstance(token, Token):
                        if token.type in ("ASC", "DESC"):
                            direction = str(token).lower()
                clauses.append(col.asc() if direction == "asc" else col.desc())
        return clauses

    # --- Helpers ---

    def _extract_field(self, node: Tree) -> str:
        for child in node.children:
            if isinstance(child, Tree) and child.data == "field":
                return str(child.children[0]).strip()
            if isinstance(child, Token) and child.type == "FIELD_NAME":
                return str(child).strip()
        raise JQLSyntaxError("Missing field name")

    def _extract_op(self, node: Tree) -> str:
        for child in node.children:
            if isinstance(child, Tree) and child.data == "op":
                return str(child.children[0]).strip()
            if isinstance(child, Token) and child.type == "OP":
                return str(child).strip()
        raise JQLSyntaxError("Missing operator")

    async def _extract_value(self, node: Tree, field_name: str) -> Any:
        for child in node.children:
            if isinstance(child, Tree) and child.data == "value":
                return await self._resolve_raw_value(child)
        raise JQLSyntaxError(f"Missing value for field {field_name}")

    async def _extract_value_list(self, node: Tree, field_name: str) -> list:
        for child in node.children:
            if isinstance(child, Tree) and child.data == "value_list":
                values = []
                for vc in child.children:
                    if isinstance(vc, Tree) and vc.data == "value":
                        values.append(await self._resolve_raw_value(vc))
                return values
        raise JQLSyntaxError(f"Missing value list for field {field_name}")

    async def _resolve_raw_value(self, value_node: Tree) -> Any:
        """Extract raw value from a value node."""
        for child in value_node.children:
            if isinstance(child, Tree) and child.data == "function":
                return await self._resolve_function(child)
            if isinstance(child, Token):
                if child.type == "RELATIVE_DATE":
                    return _parse_relative_date(str(child))
                if child.type == "QUOTED_STRING":
                    # Strip surrounding quotes
                    raw = str(child)
                    if raw.startswith('"') and raw.endswith('"'):
                        return raw[1:-1]
                    return raw
                return str(child)
        return None

    async def _resolve_function(self, func_node: Tree) -> Any:
        func_name = None
        args = []
        for child in func_node.children:
            if isinstance(child, Token) and child.type == "FUNC_NAME":
                func_name = str(child).lower()
            elif isinstance(child, Tree) and child.data == "func_args":
                for arg in child.children:
                    if isinstance(arg, Tree) and arg.data == "value":
                        args.append(await self._resolve_raw_value(arg))

        if func_name not in _KNOWN_FUNCTIONS:
            raise JQLFunctionError(func_name or "unknown")

        if func_name == "currentuser":
            return self._context.current_user_id
        elif func_name == "now":
            return datetime.utcnow()
        elif func_name == "startofday":
            return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        elif func_name == "endofday":
            return datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)
        elif func_name == "startofweek":
            now = datetime.utcnow()
            return (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif func_name == "startofmonth":
            now = datetime.utcnow()
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif func_name == "membersof":
            return args[0] if args else None

        return None

    async def _resolve_value(
        self, canonical: str, desc: FieldDescriptor, value: Any
    ) -> Any:
        """Resolve a raw value to the appropriate DB value (with FK lookup)."""
        if isinstance(value, datetime):
            return value

        if desc.lookup_table and desc.lookup_field and isinstance(value, str):
            # Check cache first
            cache_key = (canonical, value)
            if cache_key in self._lookup_cache:
                return self._lookup_cache[cache_key]

            if self._context.db is None:
                return value

            table = desc.lookup_table
            lookup_col = getattr(table, desc.lookup_field)
            id_col = getattr(table, "id")

            stmt = select(id_col).where(lookup_col == value)
            # Add project filter if available
            if hasattr(table, "project_id") and self._context.project_id:
                stmt = stmt.where(table.project_id == self._context.project_id)

            result = await self._context.db.execute(stmt)
            row = result.scalar_one_or_none()
            resolved = row if row else value
            self._lookup_cache[cache_key] = resolved
            return resolved

        return value
