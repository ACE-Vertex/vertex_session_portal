#!/usr/bin/env python3
from pathlib import Path
import json
ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
ER=ROOT/"EVIDENCE"/"CORRELATION_INCIDENT_RUNTIME_SMOKE_000079V4C2"
def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}"); return bool(v)
def latest():
    xs=list(ER.rglob("correlation_incident_runtime_smoke_000079V4C2.json")) if ER.exists() else []
    return max(xs,key=lambda p:p.stat().st_mtime_ns) if xs else None
def main():
    rp=latest(); checks=[ck("SMOKE_EVIDENCE_EXISTS",rp is not None)]
    if not rp: return 3
    d=json.loads(rp.read_text(encoding="utf-8-sig"))
    checks += [
      ck("BUNDLE_SECTION",isinstance(d.get("bundle"),dict)),
      ck("CLASSIFICATION_PRESENT",bool(d.get("classification"))),
      ck("NEXT_PRESENT",bool(d.get("next"))),
      ck("BLACK_BOX_SECTION",isinstance(d.get("black_box"),dict)),
      ck("EVENT_RAY_SECTION",isinstance(d.get("event_ray"),dict)),
      ck("INCIDENT_SECTION",isinstance(d.get("incidents"),dict)),
    ]
    mut=d.get("mutation") or {}
    checks += [
      ck("NO_SOURCE_MUTATION",mut.get("production_source_mutated") is False),
      ck("NO_PROCESS_MUTATION",mut.get("running_process_mutated") is False),
      ck("NO_LOG_MUTATION",mut.get("runtime_logs_mutated") is False),
      ck("NO_INCIDENT_PACK_MUTATION",mut.get("incident_pack_mutated") is False),
    ]
    ok=all(checks)
    print(f"RUNTIME_ACTIVE={d.get('runtime_active')}")
    print(f"HUMAN_MARKER_E2E={d.get('human_marker_e2e')}")
    print(f"CLASSIFICATION={d.get('classification')}")
    print(f"NEXT={d.get('next')}")
    print(f"EVIDENCE={rp}")
    print("CORRELATION_INCIDENT_RUNTIME_SMOKE_000079V4C2_VERIFY="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4
if __name__=="__main__": raise SystemExit(main())
