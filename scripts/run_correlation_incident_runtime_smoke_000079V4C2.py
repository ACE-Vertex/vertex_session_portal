#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt, json, os
from pathlib import Path

USER_DATA=Path(os.environ.get("APPDATA",""))/"vertex-session-portal"
BLACK_BOX=USER_DATA/"observability"/"black-box.jsonl"
EVENT_RAY=USER_DATA/"event-ray"/"focus-scroll-event-ray.jsonl"
INCIDENT_ROOT=USER_DATA/"observability"/"incidents"
PROJECT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
BUNDLE=PROJECT/"out"/"main"/"index.js"
ER=PROJECT/"EVIDENCE"/"CORRELATION_INCIDENT_RUNTIME_SMOKE_000079V4C2"

def stamp(): return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def read_jsonl(path:Path,max_bytes=12*1024*1024):
    if not path.exists(): return []
    size=path.stat().st_size
    with path.open("rb") as f:
        if size>max_bytes:
            f.seek(size-max_bytes); f.readline()
        raw=f.read()
    out=[]
    for line in raw.decode("utf-8",errors="replace").splitlines():
        try:
            obj=json.loads(line)
            if isinstance(obj,dict): out.append(obj)
        except Exception: pass
    return out

def incident_rows():
    if not INCIDENT_ROOT.exists(): return []
    out=[]
    for p in INCIDENT_ROOT.iterdir():
        if not p.is_dir(): continue
        pack=p/"incident-evidence-pack.json"
        if pack.exists():
            out.append({"id":p.name,"path":str(pack),"mtime":pack.stat().st_mtime,"bytes":pack.stat().st_size})
    out.sort(key=lambda x:x["mtime"],reverse=True)
    return out

def main():
    print("=== VERTEX SESSION PORTAL / CORRELATION + INCIDENT RUNTIME SMOKE 000079V4C2 ===")
    black=read_jsonl(BLACK_BOX)
    ray=read_jsonl(EVENT_RAY)
    incidents=incident_rows()
    bundle_text=BUNDLE.read_text(encoding="utf-8",errors="replace") if BUNDLE.exists() else ""

    bundle_corr="dispatch_correlation_observer_started" in bundle_text
    bundle_marker="MARK INCIDENT" in bundle_text and "human_incident_marker" in bundle_text

    observer_started=[r for r in black if r.get("event")=="dispatch_correlation_observer_started"]
    observer_baseline=[r for r in black if r.get("event")=="dispatch_correlation_observer_baseline"]
    corr_records=[
        r for r in black
        if isinstance(r.get("correlation_id"),str) and r.get("correlation_id")
        and str(r.get("event","")).startswith(("vra_","human_","incoming_","workstation_","dispatch_","evidence_"))
    ]
    marker_installed=[r for r in ray if r.get("type")=="page:incident_marker_installed"]
    marker_clicked=[r for r in ray if r.get("type")=="page:human_incident_marker"]
    marker_incident_black=[
        r for r in black
        if r.get("event")=="event_ray_incident_candidate"
        and isinstance(r.get("payload"),dict)
        and r["payload"].get("candidate_type")=="page:human_incident_marker"
    ]

    runtime_active=bool(observer_started and observer_baseline and marker_installed)
    human_marker_e2e=bool(marker_clicked and marker_incident_black and incidents)

    if runtime_active and human_marker_e2e:
        classification="CORRELATION_AND_INCIDENT_RUNTIME_E2E_ACTIVE"
        next_step="NORMAL_OPERATION_AND_CORRELATION_TRACE_ACCUMULATION"
    elif runtime_active:
        classification="RUNTIME_ACTIVE_HUMAN_MARKER_NOT_YET_EXERCISED"
        next_step="CLICK_MARK_INCIDENT_ONCE_THEN_RECHECK"
    elif bundle_corr and bundle_marker:
        classification="BUNDLE_UPDATED_RUNTIME_NOT_YET_ACTIVE"
        next_step="FULL_RESTART_SESSION_PORTAL_THEN_RECHECK"
    else:
        classification="BUNDLE_OR_RUNTIME_ACTIVATION_INCOMPLETE"
        next_step="000079V4D_RUNTIME_ACTIVATION_DIAGNOSIS"

    run_dir=ER/stamp(); run_dir.mkdir(parents=True,exist_ok=True)
    rp=run_dir/"correlation_incident_runtime_smoke_000079V4C2.json"
    report={
      "schema":"vertex-session-portal/correlation-incident-runtime-smoke/2",
      "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
      "bundle":{"exists":BUNDLE.exists(),"correlation_marker":bundle_corr,"incident_marker":bundle_marker},
      "black_box":{"path":str(BLACK_BOX),"exists":BLACK_BOX.exists(),"records":len(black),"observer_started":len(observer_started),"observer_baseline":len(observer_baseline),"correlated_transition_records":len(corr_records),"human_marker_incident_candidates":len(marker_incident_black)},
      "event_ray":{"path":str(EVENT_RAY),"exists":EVENT_RAY.exists(),"records":len(ray),"marker_installed":len(marker_installed),"marker_clicked":len(marker_clicked)},
      "incidents":{"root":str(INCIDENT_ROOT),"count":len(incidents),"latest":incidents[:10]},
      "runtime_active":runtime_active,"human_marker_e2e":human_marker_e2e,"classification":classification,"next":next_step,
      "mutation":{"production_source_mutated":False,"running_process_mutated":False,"runtime_logs_mutated":False,"incident_pack_mutated":False}
    }
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    print(f"BUNDLE_EXISTS={str(BUNDLE.exists()).upper()}")
    print(f"BUNDLE_CORRELATION_MARKER={str(bundle_corr).upper()}")
    print(f"BUNDLE_INCIDENT_MARKER={str(bundle_marker).upper()}")
    print(f"BLACK_BOX_EXISTS={str(BLACK_BOX.exists()).upper()}")
    print(f"EVENT_RAY_EXISTS={str(EVENT_RAY.exists()).upper()}")
    print(f"DISPATCH_CORRELATION_OBSERVER_STARTED={len(observer_started)}")
    print(f"DISPATCH_CORRELATION_OBSERVER_BASELINE={len(observer_baseline)}")
    print(f"CORRELATED_TRANSITION_RECORDS={len(corr_records)}")
    print(f"INCIDENT_MARKER_INSTALLED={len(marker_installed)}")
    print(f"HUMAN_INCIDENT_MARKER_CLICKS={len(marker_clicked)}")
    print(f"HUMAN_MARKER_INCIDENT_CANDIDATES={len(marker_incident_black)}")
    print(f"INCIDENT_PACK_COUNT={len(incidents)}")
    print(f"RUNTIME_ACTIVE={str(runtime_active).upper()}")
    print(f"HUMAN_MARKER_E2E={str(human_marker_e2e).upper()}")
    print(f"CLASSIFICATION={classification}")
    print(f"NEXT={next_step}")
    print("PRODUCTION_MUTATION=FALSE")
    print("PROCESS_MUTATION=FALSE")
    print("RUNTIME_LOG_MUTATION=FALSE")
    print(f"EVIDENCE={rp}")
    print("CORRELATION_INCIDENT_RUNTIME_SMOKE_000079V4C2_RUN=PASS")
    return 0

if __name__=="__main__": raise SystemExit(main())
