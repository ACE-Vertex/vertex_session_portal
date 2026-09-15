#!/usr/bin/env python3
from pathlib import Path
import json

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
MAIN=ROOT/"src"/"main"/"index.ts"
CORE=ROOT/"src"/"main"/"observability"/"vertex-observability-core.ts"
OBS_INDEX=ROOT/"src"/"main"/"observability"/"index.ts"
ER=ROOT/"EVIDENCE"/"OBSERVABILITY_CORE_FOUNDATION_000078V4"
IMPORT_LINE="import './observability'"

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def latest():
    xs=list(ER.rglob("observability_core_foundation_000078V4.json")) if ER.exists() else []
    return max(xs,key=lambda p:p.stat().st_mtime_ns) if xs else None

def main():
    checks=[]
    checks.append(ck("MAIN_EXISTS",MAIN.exists()))
    checks.append(ck("CORE_EXISTS",CORE.exists()))
    checks.append(ck("OBS_INDEX_EXISTS",OBS_INDEX.exists()))
    if not MAIN.exists() or not CORE.exists() or not OBS_INDEX.exists():
        return 3

    main=MAIN.read_text(encoding="utf-8-sig",errors="replace")
    core=CORE.read_text(encoding="utf-8-sig",errors="replace")
    obs=OBS_INDEX.read_text(encoding="utf-8-sig",errors="replace")

    checks.append(ck("IMPORT_EXACTLY_ONCE",main.count(IMPORT_LINE)==1))
    checks.append(ck("ACTIVATE_WHEN_READY","app.whenReady()" in obs))
    checks.append(ck("BLACK_BOX","black-box.jsonl" in core))
    checks.append(ck("FLIGHT_RECORDER","FLIGHT_WINDOW_MS" in core and "flight" in core))
    checks.append(ck("CORRELATION_TRACE_API","trace(" in core and "correlation_id" in core))
    checks.append(ck("STATE_JOURNAL","stateTransition(" in core and "state_transition" in core))
    checks.append(ck("PERFORMANCE_METRICS","event_loop_lag_ms" in core and "process.memoryUsage()" in core))
    checks.append(ck("CRASH_OBSERVER","uncaughtExceptionMonitor" in core and "render-process-gone" in core))
    checks.append(ck("EVENT_RAY_BRIDGE","event_ray_bridge_started" in core and "pollEventRay" in core))
    checks.append(ck("INCIDENT_PACKER","incident-evidence-pack.json" in core and "markIncident(" in core))
    checks.append(ck("AUTO_INCIDENT_CANDIDATES","ime_submit_collision_candidate" in core and "scroll_backlash_candidate" in core))
    checks.append(ck("ROTATION","rotateBlackBox" in core and "BLACK_BOX_MAX_BYTES" in core))
    checks.append(ck("NO_PAGE_TEXT_DIRECT_CAPTURE","document." not in core and "webContents.executeJavaScript" not in core))
    checks.append(ck("NO_AUTO_REPAIR","autoRepair" not in core and "auto_apply" not in core.lower()))
    checks.append(ck("NO_RENDERER_MUTATION","src/renderer" not in core))
    checks.append(ck("NO_WORKSTATION_MUTATION","vertex_workstation" not in core))

    rp=latest()
    checks.append(ck("INSTALL_EVIDENCE_EXISTS",rp is not None))
    if rp:
        d=json.loads(rp.read_text(encoding="utf-8-sig"))
        checks.append(ck("INSTALL_STATUS",d.get("status")=="INSTALLED"))
        checks.append(ck("NO_NEW_TSC_DIAGNOSTICS",len(d.get("new_diagnostics") or [])==0))
        checks.append(ck("NO_OBS_TSC_DIAGNOSTICS",len(d.get("observability_diagnostics") or [])==0))
        behavior=d.get("behavior") or {}
        checks.append(ck("HUMAN_GATE_PRESERVED",behavior.get("human_gate_mutated") is False))
        checks.append(ck("AUTO_REPAIR_FALSE",behavior.get("auto_repair") is False))
        checks.append(ck("RESTART_REQUIRED",d.get("restart_required") is True))

    ok=all(checks)
    print("OBSERVABILITY_CORE_FOUNDATION_000078V4_VERIFY="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
