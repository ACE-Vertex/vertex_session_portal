from __future__ import annotations

from pathlib import Path
import json
import re
import sys

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")

FILES = {
    "dispatch_service": ROOT / "src/main/vra/vra-dispatch-service.ts",
    "dispatch_ipc": ROOT / "src/main/ipc/register-vra-dispatch-ipc.ts",
    "workstation_client": ROOT / "src/main/workstation/workstation-client.ts",
    "contracts": ROOT / "src/shared/contracts.ts",
    "browser_session": ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts",
    "dispatch_lane": ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts",
}

TERMS = {
    "origin": [
        r"captureOrigin",
        r"originVera",
        r"originSession",
        r"originWindow",
        r"VRA_ORIGIN_UNRESOLVED",
    ],
    "routing": [
        r"vra-routing/1",
        r"return_channel",
        r"correlation",
        r"requestedLane",
        r"allocatedLane",
        r"lanePolicy",
    ],
    "evidence": [
        r"evidence",
        r"Evidence",
        r"RETURN_QUEUED",
        r"RETURNED",
        r"evidenceReturn",
        r"evidence_return",
    ],
    "reconcile": [
        r"reconcileWorkstation",
        r"reconcileWorkstationCard",
        r"probeWorkstationHealth",
        r"workstationInFlight",
    ],
    "human_gate": [
        r"HUMAN_APPLY",
        r"humanApproval",
        r"APPROVED",
        r"STAGING_FIRST",
    ],
    "ray": [
        r"\bRay\b",
        r"\bRAY\b",
        r"Deep Ray",
        r"deepRay",
        r"ray_",
    ],
    "sensor": [
        r"\bSensor\b",
        r"\bSENSOR\b",
        r"observe",
        r"health",
        r"probe",
    ],
    "judge": [
        r"\bJudge\b",
        r"\bJUDGE\b",
        r"evaluate",
        r"classif",
        r"failure",
    ],
}

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")

def line_hits(text: str, pattern: str):
    rx = re.compile(pattern, re.IGNORECASE)
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if rx.search(line):
            hits.append((i, line.strip()))
    return hits

def main() -> int:
    print("=== VERTEX SESSION PORTAL / OBSERVABILITY CORE PRE-FLIGHT 000091V5 ===")
    print(f"ROOT={ROOT}")
    print("MODE=READ_ONLY_SOURCE_AUDIT")
    print("PRODUCTION_MUTATION=NONE")
    print("HUMAN_UI_CHANGE=NONE")
    print("TARGET_ARCHITECTURE=HIDDEN_CONTROL_PLANE")

    if not ROOT.exists():
        print("ROOT_PRESENT=FAIL")
        return 2
    print("ROOT_PRESENT=PASS")

    missing = []
    loaded = {}
    for key, path in FILES.items():
        if not path.exists():
            print(f"FILE_{key.upper()}=MISSING:{path.relative_to(ROOT)}")
            missing.append(key)
            continue
        text = read_text(path)
        loaded[key] = (path, text)
        print(f"FILE_{key.upper()}=PASS:{path.relative_to(ROOT)}:{len(text)}")

    if missing:
        print("KNOWN_ANCHORS_COMPLETE=NO")
    else:
        print("KNOWN_ANCHORS_COMPLETE=YES")

    print("\n=== CAPABILITY SURVEY ===")
    totals = {}
    samples = {}
    for group, patterns in TERMS.items():
        count = 0
        sample_rows = []
        for file_key, (path, text) in loaded.items():
            for pattern in patterns:
                for line_no, line in line_hits(text, pattern):
                    count += 1
                    if len(sample_rows) < 12:
                        sample_rows.append({
                            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                            "line": line_no,
                            "text": line[:220],
                        })
        totals[group] = count
        samples[group] = sample_rows
        print(f"{group.upper()}_HITS={count}")

    print("\n=== SOURCE ANCHORS ===")
    preferred = {
        "dispatch_service": [
            "captureOrigin", "ensureCaptureRoutingEnvelope", "publishToIncomingAtomic",
            "reconcileWorkstation", "reconcileWorkstationCard", "evidence"
        ],
        "workstation_client": ["health", "job", "evidence"],
        "dispatch_ipc": ["ipc", "dispatch", "approval"],
        "contracts": ["evidence", "workstation", "routing"],
    }
    for file_key, needles in preferred.items():
        if file_key not in loaded:
            continue
        path, text = loaded[file_key]
        for needle in needles:
            hits = line_hits(text, re.escape(needle))
            if hits:
                line_no, line = hits[0]
                print(f"ANCHOR={file_key}:{needle}:{line_no}:{line[:200]}")

    print("\n=== HIDDEN CONTROL PLANE READINESS ===")
    checks = {
        "IMMUTABLE_ORIGIN_BASE": totals.get("origin", 0) > 0,
        "ROUTING_BASE": totals.get("routing", 0) > 0,
        "EVIDENCE_BASE": totals.get("evidence", 0) > 0,
        "RECONCILE_BASE": totals.get("reconcile", 0) > 0,
        "HUMAN_GATE_BASE": totals.get("human_gate", 0) > 0,
    }
    for key, ok in checks.items():
        print(f"{key}={'PASS' if ok else 'FAIL'}")

    # Deliberately informational. Existing Ray/Sensor/Judge may be absent or partial.
    print(f"RAY_EXISTING={'YES' if totals.get('ray', 0) else 'NO_OR_NOT_ANCHORED'}")
    print(f"SENSOR_EXISTING={'YES' if totals.get('sensor', 0) else 'NO_OR_NOT_ANCHORED'}")
    print(f"JUDGE_EXISTING={'YES' if totals.get('judge', 0) else 'NO_OR_NOT_ANCHORED'}")

    recommended = [
        "observability/contracts.ts",
        "observability/ray-core.ts",
        "observability/sensor-core.ts",
        "observability/judge-core.ts",
        "observability/impact-core.ts",
        "observability/guard-core.ts",
        "observability/black-box.ts",
        "observability/evidence-intelligence.ts",
        "observability/observability-coordinator.ts",
    ]
    print("\n=== PROPOSED INTERNAL MODULE BOUNDARY ===")
    for item in recommended:
        print(f"MODULE={item}")

    report = {
        "schema": "vertex-session-portal/observability-preflight-1",
        "artifact_id": "vertex-session-portal-observability-core-preflight-000091V5",
        "root": str(ROOT),
        "mode": "READ_ONLY_SOURCE_AUDIT",
        "human_ui_change": False,
        "production_mutation": False,
        "totals": totals,
        "samples": samples,
        "checks": checks,
        "proposed_modules": recommended,
        "invariants": [
            "Ray is READ_ONLY",
            "No Browser DOM scrape",
            "Human Gate preserved",
            "STAGING_FIRST preserved",
            "Workstation remains execution authority",
            "Lane allocation authority remains Workstation",
            "External lane policy remains ANY/PREFER",
            "No new human-facing observability UI",
        ],
    }

    report_path = ROOT / "research" / "observability_core_preflight_000091V5.report.json"
    try:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"REPORT_WRITE={report_path}")
        print("REPORT_WRITE_SCOPE=RESEARCH_ONLY")
    except Exception as exc:
        print(f"REPORT_WRITE=FAIL:{exc}")
        return 3

    critical = all(checks.values())
    print(f"PRE_FLIGHT_CRITICAL_BASE={'PASS' if critical else 'FAIL'}")
    print("NEXT=USE_EVIDENCE_TO_BUILD_000091V5H1_FOUNDATION")
    return 0 if critical else 1

if __name__ == "__main__":
    raise SystemExit(main())
