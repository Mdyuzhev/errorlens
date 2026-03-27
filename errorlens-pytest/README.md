# errorlens-pytest

Native pytest plugin for [ErrorLens](https://github.com/Mdyuzhev/errorlens) test reporting.

## Install

```bash
pip install errorlens-pytest
```

## Configuration

Set environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `EL_URL` | Yes | ErrorLens server URL (e.g. `http://192.168.1.74:3000`) |
| `EL_TOKEN` | Yes | JWT access token |
| `EL_PROJECT_ID` | Yes | Project UUID |
| `EL_LAUNCH_NAME` | No | Launch name (default: "Unnamed launch") |
| `EL_BRANCH` | No | Git branch |
| `EL_ENVIRONMENT` | No | Environment name |
| `EL_PIPELINE_ID` | No | CI pipeline ID |

## Usage

```python
import errorlens as el

@el.feature("Auth")
@el.story("Login")
@el.severity("critical")
def test_login():
    with el.step("Open login page"):
        pass
    with el.step("Enter credentials", params={"user": "admin"}):
        pass
    with el.step("Verify redirect"):
        pass
```

Plugin activates automatically when installed. No conftest.py needed.
