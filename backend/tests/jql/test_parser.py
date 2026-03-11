"""Tests for JQL grammar parser."""

import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.jql.compiler import _get_parser, JQLCompiler
from app.jql.exceptions import JQLSyntaxError


@pytest.fixture
def parser():
    return _get_parser()


@pytest.fixture
def compiler():
    return JQLCompiler()


class TestParser:
    """Test JQL grammar parsing."""

    def test_simple_equality(self, parser):
        tree = parser.parse('status = "todo"')
        assert tree is not None

    def test_unquoted_value(self, parser):
        tree = parser.parse('status = todo')
        assert tree is not None

    def test_in_operator(self, parser):
        tree = parser.parse('priority in (High, Critical)')
        assert tree is not None

    def test_and_or(self, parser):
        tree = parser.parse('status = todo AND priority = high OR severity = critical')
        assert tree is not None

    def test_not_operator(self, parser):
        tree = parser.parse('NOT status = Done')
        assert tree is not None

    def test_current_user(self, parser):
        tree = parser.parse('assignee = currentUser()')
        assert tree is not None

    def test_relative_date(self, parser):
        tree = parser.parse('created >= -7d')
        assert tree is not None

    def test_order_by(self, parser):
        tree = parser.parse('status = todo ORDER BY created DESC')
        assert tree is not None

    def test_order_by_multiple(self, parser):
        tree = parser.parse('status = todo ORDER BY priority ASC, created DESC')
        assert tree is not None

    def test_was_operator(self, parser):
        tree = parser.parse('status WAS "Done"')
        assert tree is not None

    def test_changed_operator(self, parser):
        tree = parser.parse('status CHANGED')
        assert tree is not None

    def test_syntax_error(self, compiler):
        with pytest.raises(JQLSyntaxError):
            compiler.parse_only('= = =')

    def test_case_insensitive(self, parser):
        """AND, and, And should all work."""
        tree1 = parser.parse('status = todo AND priority = high')
        tree2 = parser.parse('status = todo and priority = high')
        tree3 = parser.parse('status = todo And priority = high')
        assert tree1 is not None
        assert tree2 is not None
        assert tree3 is not None

    def test_jira_aliases(self, parser):
        tree = parser.parse('issuetype = Bug')
        assert tree is not None

    def test_duedate_alias(self, parser):
        tree = parser.parse('duedate >= -2w')
        assert tree is not None

    def test_is_empty(self, parser):
        tree = parser.parse('summary IS EMPTY')
        assert tree is not None

    def test_is_not_empty(self, parser):
        tree = parser.parse('summary IS NOT EMPTY')
        assert tree is not None

    def test_not_in(self, parser):
        tree = parser.parse('priority NOT IN (Low, Trivial)')
        assert tree is not None

    def test_contains(self, parser):
        tree = parser.parse('text ~ "login"')
        assert tree is not None

    def test_not_contains(self, parser):
        tree = parser.parse('summary !~ "test"')
        assert tree is not None

    def test_parentheses(self, parser):
        tree = parser.parse('type = Bug AND (priority = High OR priority = Critical)')
        assert tree is not None

    def test_complex_query(self, parser):
        jql = 'assignee = currentUser() AND status != Done AND priority in (High, Critical) ORDER BY created DESC'
        tree = parser.parse(jql)
        assert tree is not None

    def test_empty_input(self, compiler):
        """Empty input should raise syntax error."""
        with pytest.raises(JQLSyntaxError):
            compiler.parse_only('')

    def test_function_startOfDay(self, parser):
        tree = parser.parse('created >= startOfDay()')
        assert tree is not None

    def test_relative_date_weeks(self, parser):
        tree = parser.parse('created >= -2w')
        assert tree is not None

    def test_relative_date_hours(self, parser):
        tree = parser.parse('updated >= -4h')
        assert tree is not None

    def test_relative_date_future(self, parser):
        tree = parser.parse('due <= +7d')
        assert tree is not None
