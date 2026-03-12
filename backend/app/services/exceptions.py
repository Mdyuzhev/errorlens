"""Service-layer exceptions."""


class GitLabConnectionError(Exception):
    """Failed to connect to GitLab instance."""
    pass


class GitLabAuthError(Exception):
    """GitLab authentication failed (401)."""
    pass


class TaskDepthExceededError(Exception):
    """Maximum task nesting depth exceeded."""
    pass


class TransitionNotAllowedError(Exception):
    """Task status transition is not allowed."""

    def __init__(self, reason: str, fields: list[str] | None = None):
        self.reason = reason
        self.fields = fields or []
        super().__init__(reason)
