#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

PROJECT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
H2_EVIDENCE_ROOT = PROJECT / "EVIDENCE" / "FOCUS_SCROLL_IME_SUBMIT_EVENT_RAY_000076V4H2"
OUT_ROOT = PROJECT / "EVIDENCE" / "EVENT_RAY_RUNTIME_ACTIVATION_PROBE_000077V4H2"
LOG_NAME = "focus-scroll-event-ray.jsonl"

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def stamp():
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def latest(root: Path, name: str):
    xs = list(root.rglob(name)) if root.exists() else []
    return max(xs, key=lambda p: p.stat().st_mtime_ns) if xs else None

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
                    "node_modules","temp","tmp"
                }
            ]
            if LOG_NAME in filenames and p.name.lower()=="event-ray":
                q=p/LOG_NAME
                key=str(q).lower()
                if key not in seen:
                    seen.add(key)
                    found.append(q)
    found.sort(key=lambda p:p.stat().st_mtime_ns, reverse=True)
    return found

def read_tail(path: Path, max_bytes=4*1024*1024):
    size=path.stat().st_size
    with path.open("rb") as f:
        if size > max_bytes:
            f.seek(size-max_bytes)
            f.readline()
        raw=f.read()
    records=[]
    bad=0
    for line in raw.decode("utf-8",errors="replace").splitlines():
        try:
            obj=json.loads(line)
            if isinstance(obj,dict):
                records.append(obj)
        except Exception:
            bad += 1
    return records,bad

def parse_ts(v):
    if not isinstance(v,str):
        return None
    try:
        return dt.datetime.fromisoformat(v.replace("Z","+00:00"))
    except Exception:
        return None

def main():
    print("=== VERTEX SESSION PORTAL / EVENT RAY RUNTIME ACTIVATION PROBE 000077V4H2 ===")
    now=now_utc()

    h2p=latest(H2_EVIDENCE_ROOT,"focus_scroll_ime_submit_event_ray_000076V4H2.json")
    if not h2p:
        print("H2_INSTALL_EVIDENCE=FALSE")
        return 2

    h2=json.loads(h2p.read_text(encoding="utf-8-sig"))
    logs=search_logs()

    log_rows=[]
    for p in logs:
        records,bad=read_tail(p)
        started=[r for r in records if r.get("type")=="event_ray_started"]
        observer=[r for r in records if r.get("type") in {"page:observer_installed","page_observer_injection"}]
        h2_events=[r for r in records if r.get("type") in {
            "page:compositionstart","page:compositionupdate","page:compositionend",
            "page:beforeinput","page:input","ime_submit_collision_candidate",
            "ime_composition_focus_loss_candidate","ime_enter_during_composition"
        }]
        latest_ts=max(
            [parse_ts(r.get("ts")) for r in records if parse_ts(r.get("ts"))],
            default=None
        )
        mtime=dt.datetime.fromtimestamp(p.stat().st_mtime,dt.timezone.utc)
        row={
            "path":str(p),
            "bytes":p.stat().st_size,
            "mtime_utc":mtime.isoformat(),
            "age_seconds":(now-mtime).total_seconds(),
            "records":len(records),
            "parse_errors":bad,
            "event_ray_started_count":len(started),
            "observer_event_count":len(observer),
            "h2_ime_event_count":len(h2_events),
            "latest_event_ts":latest_ts.isoformat() if latest_ts else None,
        }
        log_rows.append(row)

    active_log=None
    for row in log_rows:
        if row["event_ray_started_count"] > 0 and row["age_seconds"] <= 600:
            active_log=row
            break

    if active_log:
        classification="EVENT_RAY_RUNTIME_ACTIVE"
        next_step="NORMAL_USE_AND_CAPTURE_NEXT_INCIDENT"
    elif log_rows:
        classification="EVENT_RAY_LOG_PRESENT_BUT_RUNTIME_ACTIVATION_NOT_CONFIRMED"
        next_step="000077V4H3_BUILD_ENTRYPOINT_DIAGNOSIS"
    else:
        classification="EVENT_RAY_RUNTIME_NOT_ACTIVE_NO_LOG"
        next_step="000077V4H3_BUILD_ENTRYPOINT_DIAGNOSIS"

    run_dir=OUT_ROOT/stamp()
    run_dir.mkdir(parents=True,exist_ok=True)
    rp=run_dir/"event_ray_runtime_activation_probe_000077V4H2.json"

    report={
        "schema":"vertex-session-portal/event-ray-runtime-activation-probe/1",
        "generated_at":now.isoformat(),
        "h2":{
            "status":h2.get("status"),
            "evidence":str(h2p),
        },
        "logs_found":len(log_rows),
        "logs":log_rows,
        "classification":classification,
        "next":next_step,
        "runtime_active":classification=="EVENT_RAY_RUNTIME_ACTIVE",
        "scientific_boundary":{
            "focus_root_cause_identified":False,
            "ime_submit_root_cause_identified":False,
            "scroll_backlash_root_cause_identified":False,
        },
        "mutation":{
            "production_source_mutated":False,
            "running_process_mutated":False,
            "event_ray_log_mutated":False,
        },
    }
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    print(f"H2_STATUS={h2.get('status')}")
    print(f"EVENT_RAY_LOGS_FOUND={len(log_rows)}")
    for i,row in enumerate(log_rows[:10],1):
        print(
            f"LOG_{i} PATH={row['path']} AGE_SEC={row['age_seconds']:.1f} "
            f"BYTES={row['bytes']} RECORDS={row['records']} "
            f"STARTED={row['event_ray_started_count']} "
            f"OBSERVER={row['observer_event_count']} "
            f"H2_IME={row['h2_ime_event_count']}"
        )
    print(f"RUNTIME_ACTIVE={str(classification=='EVENT_RAY_RUNTIME_ACTIVE').upper()}")
    print(f"CLASSIFICATION={classification}")
    print(f"NEXT={next_step}")
    print("PRODUCTION_MUTATION=FALSE")
    print("PROCESS_MUTATION=FALSE")
    print("EVENT_RAY_LOG_MUTATION=FALSE")
    print(f"EVIDENCE={rp}")
    print("EVENT_RAY_RUNTIME_ACTIVATION_PROBE_000077V4H2_RUN=PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
