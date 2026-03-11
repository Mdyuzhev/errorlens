"""Service-layer exceptions."""


class GitLabConnectionError(Exception):
    """Failed to connect to GitLab instance."""
    pass


class GitLabAuthError(Exception):
    """GitLab authentication failed (401)."""
    pass
