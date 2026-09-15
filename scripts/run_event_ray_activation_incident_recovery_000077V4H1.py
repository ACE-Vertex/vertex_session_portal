#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path

PROJECT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
H2_EVIDENCE_ROOT = PROJECT / "EVIDENCE" / "FOCUS_SCROLL_IME_SUBMIT_EVENT_RAY_000076V4H2"
OUT_ROOT = PROJECT / "EVIDENCE" / "EVENT_RAY_ACTIVATION_INCIDENT_RECOVERY_000077V4H1"
MODULE = PROJECT / "src" / "main" / "diagnostics" / "focus-scroll-event-ray.ts"
LOG_NAME = "focus-scroll-event-ray.jsonl"

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def stamp():
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def latest(root: Path, name: str):
    xs = list(root.rglob(name)) if root.exists() else []
    return max(xs, key=lambda p: p.stat().st_mtime_ns) if xs else None

def parse_iso(v):
    if not isinstance(v, str):
        return None
    try:
        return dt.datetime.fromisoformat(v.replace("Z","+00:00"))
    except Exception:
        return None

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def powershell_processes():
    ps_script = r'''
$items = Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match 'electron|vertex') -or
  ($_.CommandLine -match 'vertex_session_portal|vertex-session-portal')
} | ForEach-Object {
  [PSCustomObject]@{
    Name = $_.Name
    ProcessId = $_.ProcessId
    ParentProcessId = $_.ParentProcessId
    CreationDate = $_.CreationDate
    ExecutablePath = $_.ExecutablePath
    CommandLine = $_.CommandLine
  }
}
$items | ConvertTo-Json -Depth 4 -Compress
'''
    p = subprocess.run(
        ["powershell.exe","-NoProfile","-Command",ps_script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if p.returncode != 0:
        return {"ok":False,"error":p.stderr.strip(),"items":[]}
    raw=p.stdout.strip()
    if not raw:
        return {"ok":True,"items":[]}
    try:
        obj=json.loads(raw)
        if isinstance(obj,dict):
            obj=[obj]
        return {"ok":True,"items":obj}
    except Exception as e:
        return {"ok":False,"error":f"json parse: {e}","raw":raw[:2000],"items":[]}

def parse_wmi_creation(v):
    if not isinstance(v,str):
        return None
    try:
        x=dt.datetime.fromisoformat(v)
        if x.tzinfo is None:
            x=x.astimezone()
        return x.astimezone(dt.timezone.utc)
    except Exception:
        return None

def portal_candidates(items):
    out=[]
    for x in items:
        cl=str(x.get("CommandLine") or "")
        ep=str(x.get("ExecutablePath") or "")
        name=str(x.get("Name") or "")
        low=(cl+" "+ep+" "+name).lower()
        if "vertex_session_portal" in low or "vertex-session-portal" in low:
            out.append(x)
    return out

def search_logs():
    roots=[]
    for env_name in ("APPDATA","LOCALAPPDATA"):
        raw=os.environ.get(env_name)
        if raw:
            roots.append(Path(raw))
    found=[]
    seen=set()
    for root in roots:
        if not root.exists():
            continue
        base_depth=len(root.parts)
        for dirpath, dirnames, filenames in os.walk(root):
            p=Path(dirpath)
            depth=len(p.parts)-base_depth
            if depth >= 5:
                dirnames[:] = []
            dirnames[:] = [
                d for d in dirnames
                if d.lower() not in {
                    "cache","code cache","gpucache","shadercache",
                    "node_modules","temp","tmp",
                }
            ]
            if LOG_NAME in filenames and p.name.lower()=="event-ray":
                q=p/LOG_NAME
                key=str(q).lower()
                if key not in seen:
                    seen.add(key)
                    found.append(q)
    found.sort(key=lambda p:p.stat().st_mtime_ns,reverse=True)
    return found

def tail_events(path: Path, max_bytes=2*1024*1024):
    size=path.stat().st_size
    with path.open("rb") as f:
        if size>max_bytes:
            f.seek(size-max_bytes)
            f.readline()
        data=f.read()
    records=[]
    for line in data.decode("utf-8",errors="replace").splitlines():
        try:
            obj=json.loads(line)
            if isinstance(obj,dict):
                records.append(obj)
        except Exception:
            pass
    return records

def main():
    print("=== VERTEX SESSION PORTAL / EVENT RAY ACTIVATION INCIDENT RECOVERY 000077V4H1 ===")

    h2p=latest(H2_EVIDENCE_ROOT,"focus_scroll_ime_submit_event_ray_000076V4H2.json")
    if not h2p or not MODULE.exists():
        print("H2_INSTALL_EVIDENCE_OR_MODULE=FAIL")
        return 2

    h2=read_json(h2p)
    h2_installed=h2.get("status")=="INSTALLED"
    module_mtime=dt.datetime.fromtimestamp(MODULE.stat().st_mtime,dt.timezone.utc)

    proc_result=powershell_processes()
    all_items=proc_result.get("items") or []
    portals=portal_candidates(all_items)

    proc_rows=[]
    for x in portals:
        created=parse_wmi_creation(x.get("CreationDate"))
        proc_rows.append({
            "name":x.get("Name"),
            "pid":x.get("ProcessId"),
            "ppid":x.get("ParentProcessId"),
            "created_at_utc":created.isoformat() if created else None,
            "created_before_h2_module": bool(created and created < module_mtime),
            "executable":x.get("ExecutablePath"),
            "command_line":x.get("CommandLine"),
        })

    logs=search_logs()
    log_rows=[]
    recent_log=None
    for p in logs:
        mtime=dt.datetime.fromtimestamp(p.stat().st_mtime,dt.timezone.utc)
        recs=tail_events(p)
        has_started=any(r.get("type")=="event_ray_started" for r in recs)
        has_h2=any(
            r.get("type") in {
                "page:compositionstart","page:beforeinput",
                "ime_submit_collision_candidate",
            }
            for r in recs
        )
        row={
            "path":str(p),
            "mtime_utc":mtime.isoformat(),
            "bytes":p.stat().st_size,
            "event_ray_started_seen":has_started,
            "h2_event_seen":has_h2,
            "tail_records":len(recs),
        }
        log_rows.append(row)
        if recent_log is None:
            recent_log=(p,recs,row)

    now=now_utc()
    process_post_h2=any(
        (parse_iso(x.get("created_at_utc")) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)) >= module_mtime
        for x in proc_rows
    )
    all_processes_pre_h2=bool(proc_rows) and all(x.get("created_before_h2_module") for x in proc_rows)

    if recent_log:
        p,recs,row=recent_log
        age=(now-parse_iso(row["mtime_utc"])).total_seconds()
        if age <= 180:
            classification="EVENT_RAY_RUNTIME_LOG_ACTIVE"
            next_step="000077V4H2_RECENT_INCIDENT_TIMELINE_CAPTURE"
        else:
            classification="EVENT_RAY_LOG_FOUND_BUT_STALE"
            next_step="SESSION_PORTAL_RESTART_THEN_000077V4H2_ACTIVATION_PROBE"
    elif all_processes_pre_h2:
        classification="EVENT_RAY_NOT_ACTIVE_RUNNING_PORTAL_PREDATES_H2"
        next_step="SESSION_PORTAL_RESTART_THEN_000077V4H2_ACTIVATION_PROBE"
    elif process_post_h2:
        classification="EVENT_RAY_RUNTIME_OR_BUILD_MISMATCH_AFTER_H2"
        next_step="000077V4H2_RUNTIME_BUILD_ENTRYPOINT_DIAGNOSIS"
    elif not proc_rows:
        classification="SESSION_PORTAL_PROCESS_NOT_RESOLVED"
        next_step="000077V4H2_PROCESS_ENTRYPOINT_DIAGNOSIS"
    else:
        classification="EVENT_RAY_ACTIVATION_STATE_AMBIGUOUS"
        next_step="000077V4H2_ACTIVATION_PROBE"

    run_dir=OUT_ROOT/stamp()
    run_dir.mkdir(parents=True,exist_ok=True)

    report={
        "schema":"vertex-session-portal/event-ray-activation-incident-recovery/1",
        "generated_at":now.isoformat(),
        "h2":{
            "evidence":str(h2p),
            "status":h2.get("status"),
            "installed":h2_installed,
            "module":str(MODULE),
            "module_mtime_utc":module_mtime.isoformat(),
        },
        "process_probe":{
            "powershell_ok":proc_result.get("ok"),
            "error":proc_result.get("error"),
            "portal_candidates":proc_rows,
            "all_portal_candidates_predate_h2":all_processes_pre_h2,
            "post_h2_portal_candidate_exists":process_post_h2,
        },
        "log_probe":{
            "found":len(log_rows),
            "logs":log_rows,
        },
        "classification":classification,
        "next":next_step,
        "scientific_boundary":{
            "incident_000077V4_captured":False,
            "reason":"000077V4 exited 2 because no Event Ray log was found by that runner.",
            "focus_root_cause_identified":False,
            "ime_submit_root_cause_identified":False,
            "scroll_backlash_root_cause_identified":False,
        },
        "mutation":{
            "production_source_mutated":False,
            "running_process_mutated":False,
            "event_ray_log_mutated":False,
            "session_portal_restarted":False,
        },
    }
    rp=run_dir/"event_ray_activation_incident_recovery_000077V4H1.json"
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    print(f"H2_INSTALLED={str(h2_installed).upper()}")
    print(f"H2_MODULE_MTIME_UTC={module_mtime.isoformat()}")
    print(f"PORTAL_PROCESS_CANDIDATES={len(proc_rows)}")
    for i,x in enumerate(proc_rows[:20],1):
        print(
            f"PROCESS_{i} PID={x.get('pid')} CREATED={x.get('created_at_utc')} "
            f"PREDATES_H2={str(bool(x.get('created_before_h2_module'))).upper()} "
            f"NAME={x.get('name')}"
        )
    print(f"EVENT_RAY_LOGS_FOUND={len(log_rows)}")
    for i,x in enumerate(log_rows[:10],1):
        print(
            f"LOG_{i} PATH={x['path']} MTIME={x['mtime_utc']} BYTES={x['bytes']} "
            f"STARTED={str(x['event_ray_started_seen']).upper()} "
            f"H2_EVENT={str(x['h2_event_seen']).upper()}"
        )
    print("INCIDENT_000077V4_CAPTURED=FALSE")
    print(f"CLASSIFICATION={classification}")
    print(f"NEXT={next_step}")
    print("PRODUCTION_MUTATION=FALSE")
    print("PROCESS_MUTATION=FALSE")
    print("SESSION_PORTAL_RESTARTED=FALSE")
    print(f"EVIDENCE={rp}")
    print("EVENT_RAY_ACTIVATION_INCIDENT_RECOVERY_000077V4H1_RUN=PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
