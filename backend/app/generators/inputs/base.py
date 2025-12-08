"""Base classes for input parsers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EndpointSpec:
    """Unified endpoint specification."""
    method: str
    path: str
    parameters: dict | None = None
    request_body: dict | None = None
    response_schema: dict | None = None
    headers: dict = field(default_factory=dict)
    auth_type: str | None = None
    description: str = ""


class TestGeneratorInput(ABC):
    """Abstract base for input sources."""

    @abstractmethod
    def to_endpoints(self) -> list[EndpointSpec]:
        pass

    @abstractmethod
    def get_base_url(self) -> str:
        pass

    @abstractmethod
    def get_auth_config(self) -> dict | None:
        pass
