"""Stub — full implementation in task-02."""
from dataclasses import dataclass, field


@dataclass
class GeneratorConfig:
    base_url: str = ""
    framework: str = "pytest"
    generate_negative_tests: bool = True
    use_placeholders: bool = True
    java_package: str = "com.api.tests"


@dataclass
class GeneratedFile:
    filename: str
    content: str
    language: str


@dataclass
class GenerationStats:
    total_endpoints: int = 0
    total_tests: int = 0
    positive_tests: int = 0
    negative_tests: int = 0
    assertions: int = 0


@dataclass
class GenerationResult:
    success: bool
    files: list[GeneratedFile]
    stats: GenerationStats
    errors: list[str] = field(default_factory=list)


class SpecTestGenerator:
    def generate(self, endpoints, config):
        return GenerationResult(
            success=True, files=[], stats=GenerationStats(), errors=[],
        )
