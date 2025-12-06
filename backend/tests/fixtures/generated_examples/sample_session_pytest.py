"""
Auto-generated pytest tests from ErrorLens session.

This file contains API tests automatically generated from recorded browser session.
Tests are designed to run sequentially and share state (like auth tokens).

Run with: pytest test_sample_session.py -v
Or simply: python test_sample_session.py

Environment variables:
  BASE_URL - Override base URL (default: recorded URL)
"""

import os
import sys

import pytest
import requests

# =============================================================================
# Configuration
# =============================================================================

# Base URL - override with environment variable or change here
BASE_URL = os.environ.get("BASE_URL", "https://api.wh-lab.ru")


# =============================================================================
# Health Check Fixture
# =============================================================================


@pytest.fixture(scope="session", autouse=True)
def check_server_available():
    """Check if API server is reachable before running tests."""
    try:
        response = requests.get(BASE_URL, timeout=5)
        # Any response means server is up (even 404)
    except requests.exceptions.ConnectionError:
        pytest.exit(
            f"API server unavailable at {BASE_URL}. Start the server or set BASE_URL env variable.",
            returncode=1,
        )
    except requests.exceptions.Timeout:
        pytest.exit(f"API server timeout at {BASE_URL}. Server may be overloaded.", returncode=1)


# =============================================================================
# Helper Functions
# =============================================================================


def assert_json_response(response, context=""):
    """Assert response is JSON and return parsed data."""
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        # Check for common error pages
        text = response.text[:500]
        if "<!DOCTYPE" in text or "<html" in text:
            pytest.fail(
                f"{context}Server returned HTML instead of JSON. "
                f"Possible causes: wrong URL, API not running, or server misconfiguration.\n"
                f"Status: {response.status_code}, Content-Type: {content_type}"
            )
        pytest.fail(f"{context}Expected JSON response, got {content_type}: {text[:200]}")
    return response.json()


# =============================================================================
# Test Class
# =============================================================================


class TestSession:
    """
    Tests generated from recorded browser session.

    Tests run in order and share authentication state.
    Override BASE_URL with environment variable for different environments.
    """

    # Shared auth token extracted from login response
    token = None

    def test_01_post_auth_login(self):
        """
        POST /api/auth/login
        Expected: 200 OK
        """
        url = BASE_URL + "/api/auth/login"
        headers = {"Content-Type": "application/json"}

        json_body = {"username": "ivanov", "password": "password123"}

        response = requests.post(url, headers=headers, json=json_body)

        # Assertions
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text[:200]}"

        # Extract auth token for subsequent requests
        data = assert_json_response(response, "Login failed: ")
        TestSession.token = data.get("token")
        assert TestSession.token, "Token not found in login response"

    def test_02_get_api_products(self):
        """
        GET /api/products
        Expected: 200 OK
        """
        url = BASE_URL + "/api/products"
        headers = {}

        # Add auth token if available
        if TestSession.token:
            headers["Authorization"] = f"Bearer {TestSession.token}"

        response = requests.get(url, headers=headers)

        # Assertions
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text[:200]}"

    def test_03_post_api_products(self):
        """
        POST /api/products
        Expected: 201 Created
        """
        url = BASE_URL + "/api/products"
        headers = {"Content-Type": "application/json"}

        # Add auth token if available
        if TestSession.token:
            headers["Authorization"] = f"Bearer {TestSession.token}"

        json_body = {
            "name": "Тестовый товар",
            "quantity": 1,
            "price": 12,
            "description": "Описание товара",
            "category": "Одежда",
        }

        response = requests.post(url, headers=headers, json=json_body)

        # Assertions
        assert (
            response.status_code == 201
        ), f"Expected 201, got {response.status_code}: {response.text[:200]}"

        # Verify response structure
        data = assert_json_response(response)
        assert "id" in data, "Missing key: id"
        assert "name" in data, "Missing key: name"
        assert "quantity" in data, "Missing key: quantity"
        assert "price" in data, "Missing key: price"

    def test_04_get_api_products(self):
        """
        GET /api/products
        Expected: 200 OK
        """
        url = BASE_URL + "/api/products"
        headers = {}

        # Add auth token if available
        if TestSession.token:
            headers["Authorization"] = f"Bearer {TestSession.token}"

        response = requests.get(url, headers=headers)

        # Assertions
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text[:200]}"


# =============================================================================
# Direct execution support with beautiful reporting
# =============================================================================

if __name__ == "__main__":
    import time
    from datetime import datetime

    class DetailedResultCollector:
        """Collects detailed test results for human-readable reporting."""

        def __init__(self):
            self.results = []
            self.start_time = None

        def pytest_sessionstart(self, session):
            self.start_time = time.time()

        def pytest_runtest_logreport(self, report):
            if report.when == "call":
                self.results.append(
                    {
                        "name": report.nodeid.split("::")[-1],
                        "status": "PASS" if report.passed else "FAIL",
                        "duration": report.duration,
                        "message": str(report.longrepr) if report.failed else None,
                    }
                )
            elif report.when == "setup" and report.failed:
                self.results.append(
                    {
                        "name": report.nodeid.split("::")[-1],
                        "status": "ERROR",
                        "duration": 0,
                        "message": str(report.longrepr),
                    }
                )

        def get_summary(self):
            passed = sum(1 for r in self.results if r["status"] == "PASS")
            failed = sum(1 for r in self.results if r["status"] == "FAIL")
            errors = sum(1 for r in self.results if r["status"] == "ERROR")
            total_time = time.time() - self.start_time if self.start_time else 0
            return {"passed": passed, "failed": failed, "errors": errors, "duration": total_time}

    def print_beautiful_report(collector):
        """Print human-readable test report."""
        summary = collector.get_summary()
        total = summary["passed"] + summary["failed"] + summary["errors"]

        # Header
        print("\n")
        print("=" * 70)
        print("                    TEST RESULTS REPORT")
        print(f"                    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # Individual results
        print("\nTEST DETAILS:")
        print("-" * 70)

        for r in collector.results:
            status_icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "ERROR": "[ERR ]"}.get(
                r["status"], "[????]"
            )

            # Clean test name for display
            name = r["name"].replace("test_", "").replace("_", " ").title()
            print(f"  {status_icon} {name} ({r['duration']:.2f}s)")

            if r["message"]:
                # Extract first meaningful line of error
                error_lines = str(r["message"]).split("\n")
                for line in error_lines:
                    if "AssertionError" in line or "Failed:" in line or "Error:" in line:
                        clean_error = line.strip()[:60]
                        print(f"         -> {clean_error}")
                        break

        # Summary
        print("\n" + "-" * 70)
        print("SUMMARY:")
        print(f"  Total tests: {total}")
        print(f"  Passed:      {summary['passed']} ({100*summary['passed']//max(total,1)}%)")
        print(f"  Failed:      {summary['failed']}")
        print(f"  Errors:      {summary['errors']}")
        print(f"  Duration:    {summary['duration']:.2f}s")

        # Verdict
        print("\n" + "=" * 70)
        if summary["failed"] == 0 and summary["errors"] == 0:
            print("  ALL TESTS PASSED! API is working correctly.")
        elif summary["passed"] > 0 and summary["failed"] > 0:
            print(
                f"  PARTIAL SUCCESS: {summary['passed']} passed, {summary['failed']} need attention."
            )
        else:
            print("  TESTS FAILED: Check the errors above and fix the issues.")
        print("=" * 70)

    # Run tests
    collector = DetailedResultCollector()
    exit_code = pytest.main([__file__, "-v", "--tb=line", "-q"], plugins=[collector])

    # Print beautiful report
    print_beautiful_report(collector)

    sys.exit(exit_code)
