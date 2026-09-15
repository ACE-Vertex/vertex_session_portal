from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import uuid

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

BASE = "http://127.0.0.1:47834"
HEALTH = BASE + "/health"
EXECUTE = BASE + "/v1/execute"

HEALTH_SCHEMA = "vertex-vxs/vra-direct-health-1"
REQ_SCHEMA = "vertex-vxs/vra-direct-request-1"
RESP_SCHEMA = "vertex-vxs/vra-direct-response-1"

ORIGIN = {
    "vera": "VERA04",
    "session": "vera-04",
    "window": "vera-04",
}

def emit(label, value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    print(f"{label}={value}", flush=True)

def call(method, url, payload=None, timeout=30):
    data = None
    headers = {"accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["content-type"] = "application/json; charset=utf-8"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            body = res.read().decode("utf-8", errors="replace")
            return res.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return exc.code, parsed

def require(ok, code, message):
    if not ok:
        emit("FAIL", message)
        raise SystemExit(code)

def execute(command: str, label: str):
    request_id = f"vera04-persistent-{label.lower()}-" + str(uuid.uuid4())
    direct_corr = str(uuid.uuid4())
    payload = {
        "schema": REQ_SCHEMA,
        "request_id": request_id,
        "correlation_id": direct_corr,
        "origin": ORIGIN,
        "command": command,
    }

    emit(label + "_REQUEST_ID", request_id)
    emit(label + "_DIRECT_CORRELATION_ID", direct_corr)
    emit(label + "_COMMAND", command)

    status, body = call("POST", EXECUTE, payload=payload, timeout=30)
    emit(label + "_HTTP_STATUS", status)
    emit(label + "_RESPONSE", body)

    require(status == 200, 50, f"{label}: /v1/execute HTTP {status}")
    require(isinstance(body, dict) and body.get("schema") == RESP_SCHEMA, 51, f"{label}: response schema mismatch")
    require(body.get("ok") is True, 52, f"{label}: response ok != true")

    result = body.get("result")
    require(isinstance(result, dict), 53, f"{label}: result missing")
    shell = result.get("shellResult")
    require(isinstance(shell, dict), 54, f"{label}: shellResult missing")
    require(shell.get("exitCode") == 0, 55, f"{label}: exitCode={shell.get('exitCode')}")

    emit(label + "_RESULT", "PASS")
    return request_id, direct_corr

def main():
    emit("TEST", "VERA04 VXS PERSISTENT WORKSPACE LIVE TWO-HIT TEST 000099V4")
    emit("EXPECTED_HUMAN_UI", "VERA04 · S04 dedicated tab stays open and receives two runs")
    emit("EXPECTED_BEHAVIOR", "FIRST creates/opens tab; SECOND reuses same tab and appends history")

    status, health = call("GET", HEALTH, timeout=8)
    emit("HEALTH_STATUS", status)
    emit("HEALTH", health)

    require(status == 200, 41, f"/health HTTP {status}")
    require(isinstance(health, dict) and health.get("schema") == HEALTH_SCHEMA, 42, "health schema mismatch")

    authority = health.get("authority")
    require(isinstance(authority, dict), 43, "authority missing")
    require(authority.get("mode") == "FULL", 44, f"AUTH not FULL: {authority}")
    require(authority.get("granted") is True, 45, f"AUTH not granted: {authority}")
    require(authority.get("granted_by") == "HUMAN", 46, f"AUTH not HUMAN: {authority}")

    # First hit: keep RUNNING visible long enough for human observation.
    first_command = (
        "Start-Sleep -Seconds 4; "
        "Write-Output 'VERA04 FIRST HIT'; "
        "$p = Get-Process | Select-Object -First 1; "
        "if ($null -ne $p) { $p | Select-Object Id,ProcessName; exit 0 } else { exit 23 }"
    )
    first_request, first_corr = execute(first_command, "FIRST")

    emit("INTER_HIT_PAUSE_SECONDS", 2)
    time.sleep(2)

    # Second hit: same origin_session, so persistent workspace must be reused.
    second_command = (
        "Start-Sleep -Seconds 4; "
        "Write-Output 'VERA04 SECOND HIT'; "
        "$now = Get-Date; "
        "Write-Output $now.ToString('yyyy-MM-dd HH:mm:ss'); "
        "exit 0"
    )
    second_request, second_corr = execute(second_command, "SECOND")

    require(first_request != second_request, 61, "request ids must differ")
    require(first_corr != second_corr, 62, "direct correlation ids must differ")

    emit("SESSION_PROVENANCE", "VERA04 / vera-04 / vera-04")
    emit("EXPECTED_TAB_LABEL", "VERA04 · S04")
    emit("EXPECTED_TAB_COUNT_FOR_SESSION", 1)
    emit("EXPECTED_HISTORY_RUNS", 2)
    emit("EXPECTED_AUTO_CLOSE", "false")
    emit("EXPECTED_SECOND_FOCUS_STEAL", "false")
    emit("LIVE_ROUTE_RESULT", "PASS")
    emit("HUMAN_VISUAL_CONFIRMATION", "SEPARATE_OBSERVATION_REQUIRED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
