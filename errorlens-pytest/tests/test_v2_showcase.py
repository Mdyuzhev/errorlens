"""Showcase tests for errorlens-pytest v2.0 — exercises all new features."""
import time

import errorlens as el


@el.title("Login with valid credentials")
@el.description("Verify that user can login with correct username and password")
@el.epic("Authentication")
@el.feature("Login")
@el.story("Basic Login Flow")
@el.suite("Smoke")
@el.parent_suite("Auth Module")
@el.severity("critical")
@el.owner("QA Team")
@el.id("TC-001")
@el.tag("smoke", "auth", "p0")
@el.issue("https://github.com/example/issues/42", "Login bug #42")
@el.testcase("https://testcase.example.com/TC-001", "TC-001 Login")
def test_login_decorators():
    """All 12 decorators on a single test."""
    with el.step("Open login page"):
        time.sleep(0.01)
    with el.step("Enter credentials", params={"user": "admin"}):
        time.sleep(0.01)
    with el.step("Click submit"):
        time.sleep(0.01)
    assert True


@el.feature("Login")
@el.story("Validation")
def test_dynamic_api():
    """Runtime dynamic labels via el.dynamic.*"""
    el.dynamic.title("Dynamic title set at runtime")
    el.dynamic.description("This description was set dynamically")
    el.dynamic.epic("Dynamic Epic")
    el.dynamic.suite("Dynamic Suite")
    el.dynamic.severity("blocker")
    el.dynamic.owner("Runtime Owner")
    el.dynamic.id("DYN-001")
    el.dynamic.tag("dynamic", "runtime")
    el.dynamic.parameter("browser", "Chrome 120")
    el.dynamic.parameter("os", "Linux")
    el.dynamic.link("https://docs.example.com", "Documentation", "docs")
    el.dynamic.issue("https://github.com/example/issues/99", "Related issue")
    el.dynamic.testcase("https://tc.example.com/DYN-001")

    with el.step("Verify dynamic labels applied"):
        ctx = el.decorators.get_current()
        assert ctx.title == "Dynamic title set at runtime"
        assert "dynamic" in ctx.tags
        assert ctx.severity == "blocker"


@el.feature("Steps")
@el.story("Step as decorator")
def test_step_decorator():
    """@el.step as function decorator with arg interpolation."""

    @el.step("Create user {username}")
    def create_user(username: str, role: str = "viewer"):
        time.sleep(0.01)
        return {"username": username, "role": role}

    @el.step("Assign role {role} to {username}")
    def assign_role(username: str, role: str):
        time.sleep(0.01)

    user = create_user("alice", role="admin")
    assign_role(user["username"], "editor")
    assert user["role"] == "admin"


@el.feature("Steps")
@el.story("Nested steps")
def test_nested_steps():
    """Nested with-steps and start/stop API."""
    with el.step("Setup environment"):
        with el.step("Create database"):
            time.sleep(0.01)
        with el.step("Run migrations"):
            time.sleep(0.01)

    # Explicit start/stop
    s = el.step.start("Manual step via start/stop")
    time.sleep(0.02)
    el.step.stop(s, status="passed")

    assert True


@el.feature("Attachments")
@el.story("Attach helpers")
def test_attach_helpers():
    """All 5 attach helper functions."""
    el.attach_json("API Response", {"status": "ok", "users": [1, 2, 3]})
    el.attach_text("Log output", "INFO: test started\nINFO: test passed")
    el.attach_html("Report", "<h1>Test Report</h1><p>All passed</p>")

    # attach_screenshot with dummy PNG header
    png_header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
    el.attach_screenshot("Login page", png_header)

    assert True


@el.feature("Login")
@el.flaky("Intermittent network timeout")
@el.tag("flaky")
def test_flaky_marker():
    """Test marked as flaky — should show badge in UI."""
    time.sleep(0.01)
    assert True


@el.feature("Login")
@el.known_issue("PROJ-123", "Known race condition in auth")
@el.tag("known-issue")
def test_known_issue_marker():
    """Test with known issue — should show badge in UI."""
    time.sleep(0.01)
    assert True


@el.feature("Login")
@el.story("Validation")
@el.severity("minor")
def test_expected_failure():
    """Intentional failure to verify error reporting with v2.0 fields."""
    el.dynamic.title("This test intentionally fails")
    el.dynamic.owner("Failure Inspector")
    el.dynamic.tag("negative", "intentional-fail")

    el.attach_text("Debug info", "This failure is expected for QA report showcase")

    with el.step("Validate empty username"):
        time.sleep(0.01)
    with el.step("Assert error message"):
        assert False, "Expected: 'Username required' error message"


class TestClassDecorators:
    """Class-level decorators inherited by all methods."""

    _el_feature = "User Management"
    _el_suite = "Regression"
    _el_owner = "Backend Team"

    @el.story("Create User")
    @el.tag("crud")
    def test_create_user(self):
        with el.step("POST /users"):
            time.sleep(0.01)
        assert True

    @el.story("Delete User")
    @el.tag("crud", "destructive")
    def test_delete_user(self):
        with el.step("DELETE /users/1"):
            time.sleep(0.01)
        assert True
