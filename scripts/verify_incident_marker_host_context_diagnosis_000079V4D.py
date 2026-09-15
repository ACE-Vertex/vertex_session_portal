#!/usr/bin/env python3
from pathlib import Path
import json
ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
ER=ROOT/"EVIDENCE"/"INCIDENT_MARKER_HOST_CONTEXT_DIAGNOSIS_000079V4D"
def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}"); return bool(v)
def latest():
    xs=list(ER.rglob("incident_marker_host_context_diagnosis_000079V4D.json")) if ER.exists() else []
    return max(xs,key=lambda p:p.stat().st_mtime_ns) if xs else None
def main():
    rp=latest(); checks=[ck("DIAG_EVIDENCE_EXISTS",rp is not None)]
    if not rp: return 3
    d=json.loads(rp.read_text(encoding="utf-8-sig"))
    checks += [
      ck("OBSERVATIONS_PRESENT",isinstance(d.get("observations"),dict)),
      ck("FILES_PRESENT",isinstance(d.get("files"),list)),
      ck("CLASSIFICATION_PRESENT",bool(d.get("classification"))),
      ck("NEXT_PRESENT",bool(d.get("next"))),
    ]
    mut=d.get("mutation") or {}
    checks += [
      ck("NO_SOURCE_MUTATION",mut.get("production_source_mutated") is False),
      ck("NO_PROCESS_MUTATION",mut.get("running_process_mutated") is False),
      ck("NO_LOG_MUTATION",mut.get("runtime_logs_mutated") is False),
      ck("NO_WORKSTATION_MUTATION",mut.get("workstation_mutated") is False),
    ]
    ok=all(checks)
    print(f"CLASSIFICATION={d.get('classification')}")
    print(f"NEXT={d.get('next')}")
    print(f"EVIDENCE={rp}")
    print("INCIDENT_MARKER_HOST_CONTEXT_DIAGNOSIS_000079V4D_VERIFY="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4
if __name__=="__main__": raise SystemExit(main())
