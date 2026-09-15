#!/usr/bin/env python3
from pathlib import Path
import json

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
ER=ROOT/"EVIDENCE"/"OBSERVABILITY_RUNTIME_STARTUP_ERROR_DIAGNOSIS_000078V4C"

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def latest():
    xs=list(ER.rglob("observability_runtime_startup_error_diagnosis_000078V4C.json")) if ER.exists() else []
    return max(xs,key=lambda p:p.stat().st_mtime_ns) if xs else None

def main():
    rp=latest()
    checks=[ck("DIAGNOSIS_EVIDENCE_EXISTS",rp is not None)]
    if not rp:
        return 3
    d=json.loads(rp.read_text(encoding="utf-8-sig"))
    checks.append(ck("PROCESS_SNAPSHOT_PRESENT","main_process" in d))
    checks.append(ck("BUNDLE_SECTION_PRESENT",isinstance(d.get("bundle"),dict)))
    checks.append(ck("ACTIVATION_TOKENS_PRESENT",isinstance(d.get("activation_tokens"),dict)))
    checks.append(ck("RUNTIME_PATHS_PRESENT",isinstance(d.get("runtime_paths"),dict)))
    checks.append(ck("CLASSIFICATION_PRESENT",bool(d.get("classification"))))
    checks.append(ck("NEXT_PRESENT",bool(d.get("next"))))
    mut=d.get("mutation") or {}
    checks.append(ck("NO_SOURCE_MUTATION",mut.get("production_source_mutated") is False))
    checks.append(ck("NO_PROCESS_MUTATION",mut.get("running_process_mutated") is False))
    checks.append(ck("NO_BUILD_MUTATION",mut.get("build_artifact_mutated") is False))
    checks.append(ck("NO_USERDATA_MUTATION",mut.get("user_data_mutated") is False))
    checks.append(ck("NO_EVENT_RAY_MUTATION",mut.get("event_ray_mutated") is False))
    ok=all(checks)
    print(f"CLASSIFICATION={d.get('classification')}")
    print(f"NEXT={d.get('next')}")
    print(f"EVIDENCE={rp}")
    print("OBSERVABILITY_RUNTIME_STARTUP_ERROR_DIAGNOSIS_000078V4C_VERIFY="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
