from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid

DEFAULT_URL = "http://127.0.0.1:47834/v1/execute"

def main() -> int:
    parser = argparse.ArgumentParser(description="VRA -> VXS direct nerve client")
    parser.add_argument("--command", required=True)
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--request-id", default=None)
    parser.add_argument("--correlation-id", default=None)
    parser.add_argument("--origin-vera", default="VERA04")
    parser.add_argument("--origin-session", default="vera-04")
    parser.add_argument("--origin-window", default="vera-04")
    args = parser.parse_args()

    request_id = args.request_id or ("vra-direct-" + str(uuid.uuid4()))
    correlation_id = args.correlation_id or str(uuid.uuid4())

    payload = {
        "schema": "vertex-vxs/vra-direct-request-1",
        "request_id": request_id,
        "correlation_id": correlation_id,
        "origin": {
            "vera": args.origin_vera,
            "session": args.origin_session,
            "window": args.origin_window,
        },
        "command": args.command,
    }
    if args.cwd:
        payload["cwd"] = args.cwd

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        args.url,
        data=data,
        headers={"content-type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(body)
            parsed = json.loads(body)
            if not parsed.get("ok"):
                return 31
            result = parsed.get("result") or {}
            shell = result.get("shellResult") or {}
            exit_code = shell.get("exitCode")
            if exit_code not in (0, None):
                return int(exit_code) if isinstance(exit_code, int) and 0 < exit_code < 126 else 32
            return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(body)
        if exc.code == 423:
            return 23
        if exc.code == 429:
            return 24
        return 30
    except Exception as exc:
        print(json.dumps({
            "schema": "vertex-vxs/vra-direct-client-error-1",
            "error": type(exc).__name__,
            "message": str(exc),
        }, ensure_ascii=False))
        return 40

if __name__ == "__main__":
    raise SystemExit(main())
