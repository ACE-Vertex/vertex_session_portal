#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
P = ROOT / "scripts" / "run_event_ray_activation_result_return_000077V4H1A.py"
ER = ROOT / "EVIDENCE" / "EVENT_RAY_ACTIVATION_INCIDENT_RECOVERY_000077V4H1"

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def main():
    xs = list(ER.rglob("event_ray_activation_incident_recovery_000077V4H1.json")) if ER.exists() else []
    checks = [
        ck("RETURN_RUNNER_PRESENT", P.exists()),
        ck("H1_EVIDENCE_PRESENT", bool(xs)),
    ]
    ok = all(checks)
    print("EVENT_RAY_ACTIVATION_RESULT_RETURN_000077V4H1A_VERIFY=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 3

if __name__ == "__main__":
    raise SystemExit(main())
