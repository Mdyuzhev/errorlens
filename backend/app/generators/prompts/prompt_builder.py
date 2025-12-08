"""Adaptive prompts for test generation."""


class PromptBuilder:
    def __init__(self, framework: str = "pytest", model_size: str = "cloud"):
        self.framework = framework
        self.model_size = model_size

    def build_prompt(self, method: str, path: str, parameters: dict | None = None,
                     request_body: dict | None = None, responses: dict | None = None) -> str:
        prompt = f"""{self._get_base_instructions()}

{self._get_method_instructions(method)}

{self._get_example(method)}

ENDPOINT:
Method: {method}
Path: {path}
"""
        if parameters:
            prompt += f"Parameters: {parameters}\n"
        if request_body:
            prompt += f"Request body: {request_body}\n"
        return prompt

    def _get_base_instructions(self) -> str:
        if self.model_size in ["3b", "7b"]:
            return """Generate ONE pytest test function. Return ONLY Python code.
Rules: Start with import pytest, use api_client.request(METHOD, PATH, json=DATA), assert status_code.
NO markdown, NO explanations."""
        return """Generate pytest test. Return ONLY Python code.
Use api_client.request(METHOD, PATH, json=data), assert status code."""

    def _get_method_instructions(self, method: str) -> str:
        instructions = {
            "GET": "Test with valid parameters, validate response status.",
            "POST": "Include valid request body, test creation (201/200).",
            "PUT": "Include complete body, test update (200/204).",
            "DELETE": "Test deletion (200/204), use example ID.",
            "PATCH": "Include partial update body, test success.",
        }
        return instructions.get(method.upper(), "")

    def _get_example(self, method: str) -> str:
        if self.framework != "pytest":
            return ""
        examples = {
            "GET": """EXAMPLE:
import pytest
def test_get_user(api_client):
    response = api_client.request('GET', '/users/123')
    assert response.status_code in [200, 404]""",
            "POST": """EXAMPLE:
import pytest
def test_create_user(api_client):
    response = api_client.request('POST', '/users', json={"name": "Test"})
    assert response.status_code in [200, 201]""",
        }
        return examples.get(method.upper(), "")
