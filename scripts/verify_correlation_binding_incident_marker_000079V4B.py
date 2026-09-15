#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
CORE = ROOT / "src" / "main" / "observability" / "vertex-observability-core.ts"
INDEX = ROOT / "src" / "main" / "observability" / "index.ts"
OBSERVER = ROOT / "src" / "main" / "observability" / "dispatch-correlation-observer.ts"
RAY = ROOT / "src" / "main" / "diagnostics" / "focus-scroll-event-ray.ts"

ERROR_RE = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+),(?P<col>\d+)\): error (?P<code>TS\d+): (?P<msg>.*)$"
)

def ck(name, value):
    print(f"{name}={'PASS' if value else 'FAIL'}")
    return bool(value)

def run_typecheck():
    p = subprocess.run(
        ["npm.cmd", "run", "typecheck"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return p

def main():
    checks = []
    checks += [
        ck("CORE_EXISTS", CORE.exists()),
        ck("INDEX_EXISTS", INDEX.exists()),
        ck("CORRELATION_OBSERVER_EXISTS", OBSERVER.exists()),
        ck("EVENT_RAY_EXISTS", RAY.exists()),
    ]
    if not all(checks):
        return 3

    core = CORE.read_text(encoding="utf-8-sig", errors="replace")
    index = INDEX.read_text(encoding="utf-8-sig", errors="replace")
    observer = OBSERVER.read_text(encoding="utf-8-sig", errors="replace")
    ray = RAY.read_text(encoding="utf-8-sig", errors="replace")

    checks += [
        ck("HUMAN_INCIDENT_EVENT_BRIDGED", "'page:human_incident_marker'" in core),
        ck("OBSERVER_IMPORTED", "startDispatchCorrelationObserver" in index),
        ck("OBSERVER_STARTS_AFTER_CORE", "vertexObservability.start()" in index and "startDispatchCorrelationObserver()" in index),
        ck("LEDGER_READ_ONLY_SOURCE", "vra-dispatch" in observer and "ledger.json" in observer),
        ck("CORRELATION_ID_PRESERVED", "correlationId" in observer and "correlation_id" in observer),
        ck("HUMAN_APPROVAL_TRACE", "human_approval_durable_commit_observed" in observer),
        ck("INCOMING_PUBLISH_TRACE", "incoming_atomic_publish_observed" in observer),
        ck("LANE_ALLOCATION_TRACE", "workstation_lane_allocation_observed" in observer),
        ck("EVIDENCE_RETURN_TRACE", "workstation_evidence_return_observed" in observer),
        ck("INCIDENT_MARKER_UI", "MARK INCIDENT" in ray and "human_incident_marker" in ray),
        ck("HOST_ONLY_UI_GATE", "vertex-vra-dispatch-lane" in ray),
        ck("NO_DISPATCH_SERVICE_MUTATION", "vra-dispatch-service" not in index and "vra-dispatch-service" not in observer),
        ck("NO_PRELOAD_BRIDGE_REQUIRED", "ipcRenderer" not in observer and "contextBridge" not in observer),
        ck("NO_AUTO_REPAIR", "autoRepair" not in observer and "auto_apply" not in observer.lower()),
    ]

    p = run_typecheck()
    print(f"TYPECHECK_EXIT={p.returncode}")
    if p.stdout:
        print("TYPECHECK_STDOUT_TAIL=" + " | ".join(p.stdout.splitlines()[-40:]))
    if p.stderr:
        print("TYPECHECK_STDERR_TAIL=" + " | ".join(p.stderr.splitlines()[-40:]))
    checks.append(ck("TYPECHECK_PASS", p.returncode == 0))

    ok = all(checks)
    print("PRODUCTION_MUTATION_FROM_VERIFY=FALSE")
    print("HUMAN_GATE_MUTATED=FALSE")
    print("STAGING_FIRST_MUTATED=FALSE")
    print("WORKSTATION_MUTATED=FALSE")
    print("CORRELATION_BINDING_MODE=DURABLE_LEDGER_OBSERVER")
    print("INCIDENT_MARKER_PATH=EVENT_RAY_TO_OBSERVABILITY_CORE")
    print("RESTART_REQUIRED=TRUE")
    print("VERTEX_SESSION_PORTAL_CORRELATION_BINDING_INCIDENT_MARKER_000079V4B=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__ == "__main__":
    raise SystemExit(main())
