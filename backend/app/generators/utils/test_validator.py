"""Validate generated test code."""
import ast


class TestValidator:
    def __init__(self, language: str = "python"):
        self.language = language

    def validate(self, code: str) -> tuple[bool, str]:
        if self.language == "python":
            return self._validate_python(code)
        return True, ""

    def _validate_python(self, code: str) -> tuple[bool, str]:
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error line {e.lineno}: {e.msg}"


def validate_pytest_syntax(code: str) -> bool:
    return "import pytest" in code and "def test_" in code
