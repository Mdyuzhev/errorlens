"""Service layer for spec-based test generation."""

from app.generators.spec_parser import OpenAPISpecParser
from app.generators.spec_generator import SpecTestGenerator, GeneratorConfig


class SpecGenService:
    def parse_spec(self, spec: str | None, spec_url: str | None) -> dict:
        """Parse OpenAPI spec and return endpoint summaries."""
        parser = self._create_parser(spec, spec_url)
        parsed = parser.parse()

        endpoints = []
        for ep in parsed.endpoints:
            endpoints.append({
                "id": f"{ep.method}:{ep.path}",
                "method": ep.method,
                "path": ep.path,
                "summary": ep.summary,
                "tags": ep.tags,
                "params_count": len(ep.path_params) + len(ep.query_params),
                "has_request_body": len(ep.request_body_schema) > 0,
                "has_response_schema": ep.has_response_schema,
            })

        return {
            "title": parsed.title,
            "version": parsed.version,
            "base_url": parsed.base_url,
            "endpoints": endpoints,
        }

    def generate_tests(self, spec, spec_url, endpoint_ids, config) -> dict:
        """Generate test files from spec."""
        parser = self._create_parser(spec, spec_url)
        parsed = parser.parse()

        # Filter endpoints by IDs if specified
        endpoints = parsed.endpoints
        if endpoint_ids is not None:
            id_set = set(endpoint_ids)
            endpoints = [
                ep for ep in endpoints
                if f"{ep.method}:{ep.path}" in id_set
            ]

        # Build generator config
        gen_config = GeneratorConfig(
            base_url=config.base_url or parsed.base_url,
            framework=config.framework,
            generate_negative_tests=config.generate_negative_tests,
            use_placeholders=config.use_placeholders,
        )

        # Generate
        result = SpecTestGenerator().generate(endpoints, gen_config)

        if not result.success:
            raise ValueError("; ".join(result.errors))

        return {
            "files": [
                {"filename": f.filename, "content": f.content, "language": f.language}
                for f in result.files
            ],
            "stats": {
                "total_endpoints": result.stats.total_endpoints,
                "total_tests": result.stats.total_tests,
                "positive_tests": result.stats.positive_tests,
                "negative_tests": result.stats.negative_tests,
                "assertions": result.stats.assertions,
            },
        }

    def _create_parser(self, spec: str | None, spec_url: str | None) -> OpenAPISpecParser:
        """Create parser from spec string or URL."""
        if spec_url:
            try:
                return OpenAPISpecParser.from_url(spec_url)
            except Exception as e:
                raise ValueError(f"Cannot fetch spec from URL: {e}")
        if spec:
            return OpenAPISpecParser(spec)
        raise ValueError("No spec provided")
