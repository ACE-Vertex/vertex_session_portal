from __future__ import annotations

import json
import sys
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

ORIGIN = {
    "vera": "VERA04",
    "session": "vera-04",
    "window": "vera-04",
}

REQ_SCHEMA = "vertex-vxs/vra-direct-request-1"
RESP_SCHEMA = "vertex-vxs/vra-direct-response-1"
HEALTH_SCHEMA = "vertex-vxs/vra-direct-health-1"

def emit(label, value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    print(f"{label}={value}", flush=True)

def call(method, url, payload=None, timeout=20):
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

def require(ok, code, msg):
    if not ok:
        emit("FAIL", msg)
        raise SystemExit(code)

def strings_under(value):
    found = []
    def walk(node):
        if isinstance(node, dict):
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            found.append(node)
    walk(value)
    return found

def main():
    emit("TEST", "VERA04 VRA -> VXS direct hit 000094V4")
    emit("TARGET", BASE)

    # Gate check.
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

    # The actual VERA04 -> VXS hit.
    request_id = "vera04-vxs-hit-" + str(uuid.uuid4())
    direct_corr = str(uuid.uuid4())
    command = "vxs ps engine"

    payload = {
        "schema": REQ_SCHEMA,
        "request_id": request_id,
        "correlation_id": direct_corr,
        "origin": ORIGIN,
        "command": command,
    }

    emit("REQUEST_ID", request_id)
    emit("DIRECT_CORRELATION_ID", direct_corr)
    emit("COMMAND", command)

    status, body = call("POST", EXECUTE, payload=payload, timeout=20)
    emit("EXECUTE_STATUS", status)
    emit("EXECUTE_RESPONSE", body)

    require(status == 200, 51, f"/v1/execute HTTP {status}")
    require(isinstance(body, dict) and body.get("schema") == RESP_SCHEMA, 52, "response schema mismatch")
    require(body.get("ok") is True, 53, f"response ok != true: {body}")

    result = body.get("result")
    require(isinstance(result, dict), 54, "result missing")
    shell = result.get("shellResult")
    require(isinstance(shell, dict), 55, "shellResult missing")
    require(shell.get("exitCode") == 0, 56, f"VXS exitCode={shell.get('exitCode')}")

    semantic = "\n".join(strings_under(result)).lower()
    require(
        any(marker in semantic for marker in ("powershell", "pwsh", "engine", "vxs")),
        57,
        "VXS engine semantic marker missing",
    )

    emit("VERA04_TO_VXS", "PASS")
    emit("VXS_COMMAND", command)
    emit("VXS_EXIT_CODE", shell.get("exitCode"))
    emit("RESULT", "VERIFIED_BY_PROBE")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
