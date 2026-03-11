"""Tests for JQL compiler (AST → SQLAlchemy)."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.jql.compiler import JQLCompiler, JQLContext, _parse_relative_date
from app.jql.exceptions import JQLFieldError, JQLFunctionError, JQLSyntaxError


@pytest.fixture
def compiler():
    return JQLCompiler()


@pytest.fixture
def context():
    return JQLContext(
        current_user_id="user-123",
        project_id="proj-456",
        db=None,
    )


class TestRelativeDateParsing:

    def test_minus_7_days(self):
        result = _parse_relative_date("-7d")
        expected = datetime.utcnow() - timedelta(days=7)
        assert abs((result - expected).total_seconds()) < 2

    def test_plus_1_hour(self):
        result = _parse_relative_date("+1h")
        expected = datetime.utcnow() + timedelta(hours=1)
        assert abs((result - expected).total_seconds()) < 2

    def test_minus_2_weeks(self):
        result = _parse_relative_date("-2w")
        expected = datetime.utcnow() - timedelta(weeks=2)
        assert abs((result - expected).total_seconds()) < 2

    def test_minus_30_minutes(self):
        result = _parse_relative_date("-30m")
        expected = datetime.utcnow() - timedelta(minutes=30)
        assert abs((result - expected).total_seconds()) < 2


class TestCompiler:

    @pytest.mark.asyncio
    async def test_compile_equality(self, compiler, context):
        result = await compiler.compile('priority = high', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_compile_in(self, compiler, context):
        result = await compiler.compile('priority in (High, Critical)', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_compile_current_user(self, compiler, context):
        result = await compiler.compile('assignee = currentUser()', context)
        assert result.where_clause is not None
        # The compiled clause should use context.current_user_id
        clause_str = str(result.where_clause.compile(compile_kwargs={"literal_binds": True}))
        assert "user-123" in clause_str

    @pytest.mark.asyncio
    async def test_compile_relative_date(self, compiler, context):
        result = await compiler.compile('created >= -7d', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_compile_text_search(self, compiler, context):
        result = await compiler.compile('text ~ "login"', context)
        assert result.where_clause is not None
        clause_str = str(result.where_clause)
        # Should search both title and description
        assert "title" in clause_str.lower() or "ILIKE" in clause_str

    @pytest.mark.asyncio
    async def test_compile_was(self, compiler, context):
        result = await compiler.compile('status WAS todo', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_compile_changed(self, compiler, context):
        result = await compiler.compile('status CHANGED', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_unknown_field(self, compiler, context):
        with pytest.raises(JQLFieldError):
            await compiler.compile('unknownfield = test', context)

    @pytest.mark.asyncio
    async def test_compile_is_empty(self, compiler, context):
        result = await compiler.compile('severity IS EMPTY', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_compile_is_not_empty(self, compiler, context):
        result = await compiler.compile('severity IS NOT EMPTY', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_compile_not_in(self, compiler, context):
        result = await compiler.compile('priority NOT IN (Low, Trivial)', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_compile_and(self, compiler, context):
        result = await compiler.compile('priority = high AND severity = critical', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_compile_or(self, compiler, context):
        result = await compiler.compile('priority = high OR priority = critical', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_compile_not(self, compiler, context):
        result = await compiler.compile('NOT priority = low', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_compile_order_by(self, compiler, context):
        result = await compiler.compile('priority = high ORDER BY created DESC', context)
        assert result.where_clause is not None
        assert len(result.order_clauses) == 1

    @pytest.mark.asyncio
    async def test_compile_order_by_multiple(self, compiler, context):
        result = await compiler.compile('priority = high ORDER BY priority ASC, created DESC', context)
        assert len(result.order_clauses) == 2

    @pytest.mark.asyncio
    async def test_compile_not_contains(self, compiler, context):
        result = await compiler.compile('summary !~ "test"', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_fk_lookup_cached(self, compiler, context):
        """One SELECT to users for two mentions of same field."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "resolved-id"
        mock_db.execute.return_value = mock_result

        context.db = mock_db
        result = await compiler.compile(
            'assignee = "ivan" OR assignee = "ivan"', context
        )
        # Should only call execute once due to caching
        assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_unknown_function(self, compiler, context):
        with pytest.raises(JQLFunctionError):
            await compiler.compile('assignee = unknownFunc()', context)

    @pytest.mark.asyncio
    async def test_none_handling(self, compiler, context):
        """Null/empty queries should raise syntax error."""
        with pytest.raises(JQLSyntaxError):
            await compiler.compile('', context)

    @pytest.mark.asyncio
    async def test_compile_parentheses(self, compiler, context):
        result = await compiler.compile(
            'type = Bug AND (priority = high OR severity = critical)', context
        )
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_compile_jira_alias(self, compiler, context):
        """issuetype should resolve to type field."""
        result = await compiler.compile('issuetype = Bug', context)
        assert result.where_clause is not None

    @pytest.mark.asyncio
    async def test_compile_startofday(self, compiler, context):
        result = await compiler.compile('created >= startOfDay()', context)
        assert result.where_clause is not None
