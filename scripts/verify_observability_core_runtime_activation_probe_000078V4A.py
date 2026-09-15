#!/usr/bin/env python3
from pathlib import Path
import json

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
ER=ROOT/"EVIDENCE"/"OBSERVABILITY_CORE_RUNTIME_ACTIVATION_000078V4A"

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def latest():
    xs=list(ER.rglob("observability_core_runtime_activation_000078V4A.json")) if ER.exists() else []
    return max(xs,key=lambda p:p.stat().st_mtime_ns) if xs else None

def main():
    rp=latest()
    checks=[ck("PROBE_EVIDENCE_EXISTS",rp is not None)]
    if not rp:
        return 3
    d=json.loads(rp.read_text(encoding="utf-8-sig"))
    checks.append(ck("CLASSIFICATION_PRESENT",bool(d.get("classification"))))
    checks.append(ck("NEXT_PRESENT",bool(d.get("next"))))
    checks.append(ck("BLACK_BOX_LIST_PRESENT","black_boxes" in d))
    mut=d.get("mutation") or {}
    checks.append(ck("NO_PRODUCTION_MUTATION",mut.get("production_source_mutated") is False))
    checks.append(ck("NO_PROCESS_MUTATION",mut.get("running_process_mutated") is False))
    checks.append(ck("NO_BLACK_BOX_MUTATION",mut.get("black_box_mutated") is False))
    checks.append(ck("NO_EVENT_RAY_MUTATION",mut.get("event_ray_mutated") is False))
    ok=all(checks)
    print(f"RUNTIME_ACTIVE={d.get('runtime_active')}")
    print(f"CLASSIFICATION={d.get('classification')}")
    print(f"NEXT={d.get('next')}")
    print(f"EVIDENCE={rp}")
    print("OBSERVABILITY_CORE_RUNTIME_ACTIVATION_PROBE_000078V4A_VERIFY="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
