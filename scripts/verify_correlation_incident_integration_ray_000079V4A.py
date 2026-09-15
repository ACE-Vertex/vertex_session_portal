#!/usr/bin/env python3
from pathlib import Path
import json

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
ER=ROOT/"EVIDENCE"/"CORRELATION_INCIDENT_INTEGRATION_RAY_000079V4A"

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def latest():
    xs=list(ER.rglob("correlation_incident_integration_ray_000079V4A.json")) if ER.exists() else []
    return max(xs,key=lambda p:p.stat().st_mtime_ns) if xs else None

def main():
    rp=latest()
    checks=[ck("RAY_EVIDENCE_EXISTS",rp is not None)]
    if not rp:
        return 3
    d=json.loads(rp.read_text(encoding="utf-8-sig"))
    checks.append(ck("ROWS_PRESENT",isinstance(d.get("rows"),list)))
    checks.append(ck("REQUIRED_ANCHORS_SECTION",isinstance(d.get("required"),dict)))
    checks.append(ck("CLASSIFICATION_PRESENT",bool(d.get("classification"))))
    checks.append(ck("NEXT_PRESENT",bool(d.get("next"))))
    mut=d.get("mutation") or {}
    checks.append(ck("NO_PRODUCTION_MUTATION",mut.get("production_source_mutated") is False))
    checks.append(ck("NO_PROCESS_MUTATION",mut.get("running_process_mutated") is False))
    checks.append(ck("NO_RUNTIME_LOG_MUTATION",mut.get("runtime_logs_mutated") is False))
    checks.append(ck("NO_WORKSTATION_MUTATION",mut.get("workstation_mutated") is False))
    ok=all(checks)
    print(f"CLASSIFICATION={d.get('classification')}")
    print(f"NEXT={d.get('next')}")
    print(f"EVIDENCE={rp}")
    print("CORRELATION_INCIDENT_INTEGRATION_RAY_000079V4A_VERIFY="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
