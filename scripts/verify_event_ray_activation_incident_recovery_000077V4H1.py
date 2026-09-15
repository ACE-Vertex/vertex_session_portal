#!/usr/bin/env python3
from pathlib import Path
import json

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
ER=ROOT/"EVIDENCE"/"EVENT_RAY_ACTIVATION_INCIDENT_RECOVERY_000077V4H1"

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def latest():
    xs=list(ER.rglob("event_ray_activation_incident_recovery_000077V4H1.json")) if ER.exists() else []
    return max(xs,key=lambda p:p.stat().st_mtime_ns) if xs else None

def main():
    rp=latest()
    checks=[ck("RECOVERY_EVIDENCE_EXISTS",rp is not None)]
    if not rp:
        return 3
    d=json.loads(rp.read_text(encoding="utf-8-sig"))
    checks.append(ck("H2_STATUS_RECORDED",bool((d.get("h2") or {}).get("status"))))
    checks.append(ck("PROCESS_PROBE_RECORDED","portal_candidates" in (d.get("process_probe") or {})))
    checks.append(ck("LOG_PROBE_RECORDED","logs" in (d.get("log_probe") or {})))
    checks.append(ck("CLASSIFICATION_PRESENT",bool(d.get("classification"))))
    checks.append(ck("NEXT_PRESENT",bool(d.get("next"))))
    sci=d.get("scientific_boundary") or {}
    checks.append(ck("NO_FALSE_INCIDENT_CAPTURE",sci.get("incident_000077V4_captured") is False))
    checks.append(ck("NO_FALSE_ROOT_CAUSE",sci.get("focus_root_cause_identified") is False))
    mut=d.get("mutation") or {}
    checks.append(ck("NO_PRODUCTION_MUTATION",mut.get("production_source_mutated") is False))
    checks.append(ck("NO_PROCESS_MUTATION",mut.get("running_process_mutated") is False))
    checks.append(ck("NO_RESTART",mut.get("session_portal_restarted") is False))
    ok=all(checks)
    print(f"CLASSIFICATION={d.get('classification')}")
    print(f"NEXT={d.get('next')}")
    print(f"EVIDENCE={rp}")
    print("EVENT_RAY_ACTIVATION_INCIDENT_RECOVERY_000077V4H1_VERIFY="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
