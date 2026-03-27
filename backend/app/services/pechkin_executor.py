"""Pechkin script executor — runs pre-request and test scripts in subprocess sandbox."""

import asyncio
import json
import sys

WRAPPER = '''
import sys, json
ctx = json.loads(sys.stdin.read())
request = ctx.get("request", {})
response = ctx.get("response")
__results__ = {"assertions": {"passed":0,"failed":0,"tests":[]}, "output":[], "modified_request": None}

def log(*a): __results__["output"].append(" ".join(str(x) for x in a))
def set_header(n,v):
    if __results__["modified_request"] is None: __results__["modified_request"] = {}
    __results__["modified_request"].setdefault("headers", dict(request.get("headers",{})))[n] = v
def set_body(b):
    if __results__["modified_request"] is None: __results__["modified_request"] = {}
    __results__["modified_request"]["body"] = b
def test(cond, msg=None):
    name = msg or f"Test #{len(__results__['assertions']['tests'])+1}"
    passed = bool(cond)
    __results__["assertions"]["tests"].append({"name": name, "passed": passed})
    if passed: __results__["assertions"]["passed"] += 1
    else: __results__["assertions"]["failed"] += 1

try:
    exec("""USER_CODE""")
except Exception as e:
    __results__["assertions"]["tests"].append({"name": str(e), "passed": False})
    __results__["assertions"]["failed"] += 1
print(json.dumps(__results__))
'''


async def run_script(code: str, context: dict, timeout: int = 10) -> dict:
    """Run user script in a sandboxed subprocess.

    Uses create_subprocess_exec (not shell) for safety — no shell injection possible.
    Returns dict with keys: success, assertions, output, modified_request, error.
    """
    script = WRAPPER.replace('USER_CODE', code.replace('"""', '\\"\\"\\"'))
    # Safe: create_subprocess_exec passes args as list, no shell interpretation
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-c", script,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdin_data = json.dumps(context).encode()
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(stdin_data), timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        return {"success": False, "error": f"Script timeout after {timeout}s"}

    try:
        result = json.loads(stdout.decode())
        return {"success": result["assertions"]["failed"] == 0, **result}
    except (json.JSONDecodeError, KeyError):
        return {"success": False, "error": stderr.decode() or "Parse error"}
