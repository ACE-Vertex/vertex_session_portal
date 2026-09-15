from __future__ import annotations

import json
import sys
import traceback
import urllib.error
import urllib.request
import uuid

# Workstation on Windows may launch Python with cp932 stdout/stderr.
# Reconfigure before any logging so the probe cannot fail before HTTP I/O.
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

HOST = "127.0.0.1"
PORT = 47834
BASE = f"http://{HOST}:{PORT}"
HEALTH_URL = BASE + "/health"
EXECUTE_URL = BASE + "/v1/execute"

ORIGIN = {
    "vera": "VERA04",
    "session": "vera-04",
    "window": "vera-04",
}

REQ_SCHEMA = "vertex-vxs/vra-direct-request-1"
RESP_SCHEMA = "vertex-vxs/vra-direct-response-1"
HEALTH_SCHEMA = "vertex-vxs/vra-direct-health-1"

def out(label: str, value) -> None:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    else:
        text = str(value)
    print(f"{label}={text}", flush=True)

def http_json(method: str, url: str, payload=None, timeout: float = 30.0):
    data = None
    headers = {"accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["content-type"] = "application/json; charset=utf-8"

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            decoded = json.loads(body)
        except Exception:
            decoded = {"raw": body}
        return exc.code, decoded

def require(condition: bool, code: int, message: str):
    if not condition:
        out("PROBE_FAILURE", message)
        raise SystemExit(code)

def summarize_shape(value, prefix="$", depth=0, max_depth=6, rows=None):
    if rows is None:
        rows = []
    if depth > max_depth or len(rows) >= 120:
        return rows

    if isinstance(value, dict):
        rows.append(f"{prefix}:object[{len(value)}]")
        for key, child in value.items():
            summarize_shape(child, f"{prefix}.{key}", depth + 1, max_depth, rows)
    elif isinstance(value, list):
        rows.append(f"{prefix}:array[{len(value)}]")
        for index, child in enumerate(value[:12]):
            summarize_shape(child, f"{prefix}[{index}]", depth + 1, max_depth, rows)
    elif value is None:
        rows.append(f"{prefix}:null")
    else:
        text = str(value).replace("\r", "\\r").replace("\n", "\\n")
        if len(text) > 220:
            text = text[:219] + "..."
        rows.append(f"{prefix}:{type(value).__name__}={text}")
    return rows

def strings_under(value):
    strings = []
    def walk(node):
        if isinstance(node, dict):
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            strings.append(node)
    walk(value)
    return strings

def direct_command(command: str, label: str, timeout: float = 30.0):
    request_id = f"vera04-{label.lower()}-{uuid.uuid4()}"
    direct_correlation_id = str(uuid.uuid4())

    payload = {
        "schema": REQ_SCHEMA,
        "request_id": request_id,
        "correlation_id": direct_correlation_id,
        "origin": ORIGIN,
        "command": command,
    }

    out(f"{label}_REQUEST_ID", request_id)
    out(f"{label}_CORRELATION_ID", direct_correlation_id)
    out(f"{label}_COMMAND", command)

    status, body = http_json(
        "POST",
        EXECUTE_URL,
        payload=payload,
        timeout=timeout,
    )

    out(f"{label}_HTTP_STATUS", status)
    out(f"{label}_RESPONSE_SHAPE", summarize_shape(body))
    return status, body

def result_and_shell(body, fail_base: int):
    require(isinstance(body, dict), fail_base, "Response body is not an object.")
    require(body.get("schema") == RESP_SCHEMA, fail_base + 1, "Direct response schema mismatch.")
    require(body.get("ok") is True, fail_base + 2, f"Direct response ok != true: {body}")

    result = body.get("result")
    require(isinstance(result, dict), fail_base + 3, "Missing result object.")

    shell = result.get("shellResult")
    require(isinstance(shell, dict), fail_base + 4, "Missing result.shellResult.")

    require(shell.get("exitCode") == 0, fail_base + 5, f"shellResult.exitCode={shell.get('exitCode')}")
    return result, shell

def main() -> int:
    out("PROBE", "VERA04 VRA-to-VXS FULL DIRECT PRODUCTION PROBE 000093V4H2")
    out("TARGET", BASE)
    out("MODE", "TEST_READ_ONLY")
    out("EXPECTED_VISIBLE_ACTIVITY", "VERA04 -> VXS : RUNNING / OK")

    # 1) Production listener + Human Gate.
    try:
        health_status, health = http_json("GET", HEALTH_URL, timeout=8.0)
    except Exception as exc:
        out("HEALTH_EXCEPTION_TYPE", type(exc).__name__)
        out("HEALTH_EXCEPTION_MESSAGE", str(exc))
        return 41

    out("HEALTH_HTTP_STATUS", health_status)
    out("HEALTH_BODY", health)

    require(health_status == 200, 42, f"Health HTTP status={health_status}")
    require(
        isinstance(health, dict) and health.get("schema") == HEALTH_SCHEMA,
        43,
        "Health schema mismatch.",
    )

    authority = health.get("authority")
    require(isinstance(authority, dict), 44, "Health authority object missing.")
    require(authority.get("mode") == "FULL", 45, f"AUTH mode is not FULL: {authority}")
    require(authority.get("granted") is True, 46, f"AUTH granted is not true: {authority}")
    require(authority.get("granted_by") == "HUMAN", 47, f"AUTH grant is not HUMAN: {authority}")

    out("PRODUCTION_LISTENER_47834", "PASS")
    out("AUTH_FULL", "PASS")
    out("AUTH_GRANTED_BY_HUMAN", "PASS")

    # 2) VXS native identity route. H1 proved HTTP 200/ok/exit0; H2 reads
    # the real response shape instead of assuming shellResult.output.
    status, body = direct_command("vxs --version", "VXS_VERSION", timeout=20.0)
    require(status == 200, 51, f"vxs --version HTTP={status} body={body}")
    result, shell = result_and_shell(body, 52)

    result_text = "\n".join(strings_under(result)).lower()
    require(
        ("vxs" in result_text) or ("0.1.0" in result_text) or ("vertex execution shell" in result_text),
        58,
        "VXS semantic marker not found anywhere under result.",
    )
    out("VXS_VERSION_ROUTE", "PASS")
    out("VXS_VERSION_SHELL_KEYS", sorted(shell.keys()))

    # 3) VXS native PowerShell-engine capability route.
    status, body = direct_command("vxs ps engine", "VXS_PS_ENGINE", timeout=20.0)
    require(status == 200, 61, f"vxs ps engine HTTP={status} body={body}")
    result, shell = result_and_shell(body, 62)

    engine_text = "\n".join(strings_under(result)).lower()
    require(
        any(marker in engine_text for marker in ("powershell", "pwsh", "engine", "vxs")),
        68,
        "VXS PS engine semantic marker not found anywhere under result.",
    )
    out("VXS_PS_ENGINE_ROUTE", "PASS")
    out("VXS_PS_ENGINE_SHELL_KEYS", sorted(shell.keys()))

    # 4) Raw compatibility PowerShell. The 1.8 s delay creates a visible
    # RUNNING witness window in the VXS header. The command's success is
    # proven by PowerShell's own conditional exit code, not by output text.
    ps_command = (
        "Start-Sleep -Milliseconds 1800; "
        "if ((Get-Process | Measure-Object).Count -gt 0) { exit 0 } else { exit 23 }"
    )
    out("VISUAL_WITNESS_WINDOW_MS", 1800)

    status, body = direct_command(ps_command, "POWERSHELL_VISIBLE_READ", timeout=30.0)
    require(status == 200, 71, f"PowerShell HTTP={status} body={body}")
    result, shell = result_and_shell(body, 72)

    out("POWERSHELL_SAFE_READ_ROUTE", "PASS")
    out("POWERSHELL_SHELL_KEYS", sorted(shell.keys()))

    out("VERA_TO_VXS_DIRECT_TRANSPORT", "PASS")
    out("HUMAN_GATE_FULL", "PASS")
    out("VXS_NATIVE_VERSION_ROUTE", "PASS")
    out("VXS_NATIVE_PS_ENGINE_ROUTE", "PASS")
    out("POWERSHELL_COMPAT_ROUTE", "PASS")
    out("SECOND_EXECUTOR_REQUIRED", "false")
    out("PROBE_RESULT", "PASS")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        out("UNHANDLED_EXCEPTION_TYPE", type(exc).__name__)
        out("UNHANDLED_EXCEPTION_MESSAGE", str(exc))
        traceback.print_exc(file=sys.stdout)
        raise SystemExit(99)
