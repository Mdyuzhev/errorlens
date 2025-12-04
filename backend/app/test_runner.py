"""Run tests (pytest or REST Assured) and track results."""

import asyncio
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# In-memory storage for test runs
test_runs: dict[str, dict] = {}


async def run_restassured(java_code: str, pom_xml: str, test_id: str) -> dict:
    """Run REST Assured (Maven) tests and return results."""
    temp_dir = Path(tempfile.mkdtemp(prefix="errorlens_java_"))

    try:
        # Create Maven project structure
        src_dir = temp_dir / "src" / "test" / "java" / "com" / "errorlens" / "tests"
        src_dir.mkdir(parents=True, exist_ok=True)

        # Write files
        (src_dir / "SessionTest.java").write_text(java_code, encoding="utf-8")
        (temp_dir / "pom.xml").write_text(pom_xml, encoding="utf-8")

        # Update status
        test_runs[test_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "output": "Starting Maven tests...\n",
            "summary": None,
        }

        # Run Maven
        process = await asyncio.create_subprocess_exec(
            "mvn",
            "test",
            "-q",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(temp_dir),
        )

        stdout, _ = await process.communicate()
        output = stdout.decode("utf-8", errors="replace")

        # Parse results (simple parsing)
        passed = output.count("Tests run:") and "Failures: 0" in output
        failed_match = output.count("Failures:")

        status = "passed" if process.returncode == 0 else "failed"

        test_runs[test_id] = {
            "status": status,
            "started_at": test_runs[test_id]["started_at"],
            "finished_at": datetime.now().isoformat(),
            "output": output,
            "returncode": process.returncode,
            "summary": {
                "passed": 1 if status == "passed" else 0,
                "failed": 1 if status == "failed" else 0,
                "errors": 0,
                "skipped": 0,
                "total": 1,
            },
        }

        return test_runs[test_id]

    except Exception as e:
        test_runs[test_id] = {
            "status": "error",
            "started_at": test_runs[test_id].get("started_at"),
            "finished_at": datetime.now().isoformat(),
            "output": f"Error: {str(e)}",
            "summary": None,
        }
        return test_runs[test_id]

    finally:
        # Cleanup
        import shutil
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


async def run_pytest(test_code: str, test_id: str) -> dict:
    """Run pytest and return results."""
    temp_dir = Path(tempfile.mkdtemp(prefix="errorlens_test_"))
    test_file = temp_dir / "test_session.py"

    try:
        # Write test file
        test_file.write_text(test_code, encoding="utf-8")

        # Update status
        test_runs[test_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "output": "Starting tests...\n",
            "summary": None,
        }

        # Run pytest
        process = await asyncio.create_subprocess_exec(
            "python",
            "-m",
            "pytest",
            str(test_file),
            "-v",
            "--tb=short",
            "--no-header",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(temp_dir),
        )

        stdout, _ = await process.communicate()
        output = stdout.decode("utf-8", errors="replace")

        # Parse results
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        errors = output.count(" ERROR")
        skipped = output.count(" SKIPPED")

        status = "passed" if process.returncode == 0 else "failed"

        test_runs[test_id] = {
            "status": status,
            "started_at": test_runs[test_id]["started_at"],
            "finished_at": datetime.now().isoformat(),
            "output": output,
            "returncode": process.returncode,
            "summary": {
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "skipped": skipped,
                "total": passed + failed + errors + skipped,
            },
        }

        return test_runs[test_id]

    except Exception as e:
        test_runs[test_id] = {
            "status": "error",
            "started_at": test_runs[test_id].get("started_at"),
            "finished_at": datetime.now().isoformat(),
            "output": f"Error: {str(e)}",
            "summary": None,
        }
        return test_runs[test_id]

    finally:
        # Cleanup
        try:
            if test_file.exists():
                test_file.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()
        except Exception:
            pass


def get_test_run(test_id: str) -> Optional[dict]:
    """Get test run status."""
    return test_runs.get(test_id)


def create_test_run() -> str:
    """Create new test run ID."""
    test_id = str(uuid.uuid4())
    test_runs[test_id] = {
        "status": "pending",
        "output": "",
        "summary": None,
    }
    return test_id
