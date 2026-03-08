"""Test code generators for various frameworks.

Available generators:
- pytest: Python pytest tests
- restassured: Java REST Assured tests
- postman: Postman Collection
- cypress: Cypress API tests
- k6: k6 load tests

Usage:
    from app.generators import pytest, restassured, postman, cypress, k6

    # Generate pytest file
    code = pytest.generate_pytest_file(recorded_requests)

    # Generate REST Assured file
    code = restassured.generate_restassured_file(recorded_requests)

    # Generate Postman collection
    result = postman.generate_postman_collection(request)

    # Generate Cypress file
    code = cypress.generate_cypress_file(recorded_requests)

    # Generate k6 load test
    code = k6.generate_k6_file(recorded_requests)
"""

# Base classes and utilities
from .base import (
    BaseGenerator,
    detect_token_in_response,
    escape_string,
    extract_path,
    filter_headers,
    generate_method_name,
    get_token_field_names,
    has_auth_header_in_request,
    is_auth_endpoint,
    parse_json_body,
)

# Cypress generator
from .cypress import (
    CypressGenerator,
    generate_cypress_config,
    generate_cypress_file,
    generate_package_json_deps,
)
from .inputs import EndpointSpec, HARInput, SwaggerInput

# k6 load test generator
from .k6 import (
    K6Generator,
    generate_k6_file,
)

# LLM comments
from .llm_comments import generate_llm_comments

# Wave 4.0: LLM-based test generator
from .llm_generator import GeneratedTest, GenerationResult, LLMTestGenerator

# Postman generator
from .postman import (
    PostmanGenerator,
    generate_postman_collection,
)
from .prompts import PromptBuilder

# Pytest generator
from .pytest import (
    PytestGenerator,
    generate_pytest_file,
    generate_pytest_file_async,
)

# REST Assured generator
from .restassured import (
    RestAssuredGenerator,
    generate_pom_xml,
    generate_restassured_file,
)

# TestIt test case generator
from .testit import (
    TestItGenerator,
    generate_testit_testcase,
)

__all__ = [
    # Base
    "BaseGenerator",
    "is_auth_endpoint",
    "has_auth_header_in_request",
    "filter_headers",
    "generate_method_name",
    "extract_path",
    "parse_json_body",
    "escape_string",
    "get_token_field_names",
    "detect_token_in_response",
    # Pytest
    "PytestGenerator",
    "generate_pytest_file",
    "generate_pytest_file_async",
    # REST Assured
    "RestAssuredGenerator",
    "generate_restassured_file",
    "generate_pom_xml",
    # Postman
    "PostmanGenerator",
    "generate_postman_collection",
    # Cypress
    "CypressGenerator",
    "generate_cypress_file",
    "generate_cypress_config",
    "generate_package_json_deps",
    # k6
    "K6Generator",
    "generate_k6_file",
    # TestIt
    "TestItGenerator",
    "generate_testit_testcase",
    # LLM
    "generate_llm_comments",
    # Wave 4.0
    "LLMTestGenerator",
    "GenerationResult",
    "GeneratedTest",
    "HARInput",
    "SwaggerInput",
    "EndpointSpec",
    "PromptBuilder",
]
