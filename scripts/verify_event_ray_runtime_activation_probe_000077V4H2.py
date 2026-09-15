#!/usr/bin/env python3
from pathlib import Path
import json

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
ER=ROOT/"EVIDENCE"/"EVENT_RAY_RUNTIME_ACTIVATION_PROBE_000077V4H2"

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def latest():
    xs=list(ER.rglob("event_ray_runtime_activation_probe_000077V4H2.json")) if ER.exists() else []
    return max(xs,key=lambda p:p.stat().st_mtime_ns) if xs else None

def main():
    rp=latest()
    checks=[ck("PROBE_EVIDENCE_EXISTS",rp is not None)]
    if not rp:
        return 3
    d=json.loads(rp.read_text(encoding="utf-8-sig"))
    checks.append(ck("CLASSIFICATION_PRESENT",bool(d.get("classification"))))
    checks.append(ck("NEXT_PRESENT",bool(d.get("next"))))
    checks.append(ck("LOG_LIST_PRESENT","logs" in d))
    mut=d.get("mutation") or {}
    checks.append(ck("NO_PRODUCTION_MUTATION",mut.get("production_source_mutated") is False))
    checks.append(ck("NO_PROCESS_MUTATION",mut.get("running_process_mutated") is False))
    checks.append(ck("NO_LOG_MUTATION",mut.get("event_ray_log_mutated") is False))
    ok=all(checks)
    print(f"RUNTIME_ACTIVE={d.get('runtime_active')}")
    print(f"CLASSIFICATION={d.get('classification')}")
    print(f"NEXT={d.get('next')}")
    print(f"EVIDENCE={rp}")
    print("EVENT_RAY_RUNTIME_ACTIVATION_PROBE_000077V4H2_VERIFY="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
