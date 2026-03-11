"""JQL error hierarchy."""


class JQLError(Exception):
    """Base JQL exception."""


class JQLSyntaxError(JQLError):
    """Invalid JQL syntax."""

    def __init__(self, message: str, position: int | None = None, line: int | None = None):
        self.message = message
        self.position = position
        self.line = line
        super().__init__(message)


class JQLFieldError(JQLError):
    """Unknown or invalid field."""

    def __init__(self, field_name: str):
        self.field_name = field_name
        super().__init__(f"Unknown field: {field_name}")


class JQLValueError(JQLError):
    """Invalid value for a field."""

    def __init__(self, field_name: str, value: str):
        self.field_name = field_name
        self.value = value
        super().__init__(f"Invalid value '{value}' for field '{field_name}'")


class JQLFunctionError(JQLError):
    """Unknown function."""

    def __init__(self, function_name: str):
        self.function_name = function_name
        super().__init__(f"Unknown function: {function_name}")
