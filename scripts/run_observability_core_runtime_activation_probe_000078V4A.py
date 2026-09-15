#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

PROJECT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
INSTALL_ER = PROJECT / "EVIDENCE" / "OBSERVABILITY_CORE_FOUNDATION_000078V4"
OUT_ER = PROJECT / "EVIDENCE" / "OBSERVABILITY_CORE_RUNTIME_ACTIVATION_000078V4A"
BLACK_BOX_NAME = "black-box.jsonl"

REQUIRED_EVENTS = {
    "runtime_start",
    "feature_flags",
    "runtime_fingerprint",
    "event_ray_bridge_started",
    "runtime_sample",
}

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def stamp():
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def latest(root: Path, name: str):
    xs = list(root.rglob(name)) if root.exists() else []
    return max(xs, key=lambda p: p.stat().st_mtime_ns) if xs else None

def parse_ts(v):
    if not isinstance(v, str):
        return None
    try:
        return dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
    except Exception:
        return None

def search_black_boxes():
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
            if BLACK_BOX_NAME in filenames and p.name.lower()=="observability":
                q=p/BLACK_BOX_NAME
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

def main():
    print("=== VERTEX SESSION PORTAL / OBSERVABILITY CORE RUNTIME ACTIVATION PROBE 000078V4A ===")
    now=now_utc()

    install=latest(INSTALL_ER,"observability_core_foundation_000078V4.json")
    if not install:
        print("INSTALL_EVIDENCE=FALSE")
        return 2

    install_data=json.loads(install.read_text(encoding="utf-8-sig"))
    boxes=search_black_boxes()

    rows=[]
    for p in boxes:
        records,bad=read_tail(p)
        events={}
        latest_event=None
        generation_seen=False
        incident_packed=0

        for r in records:
            ev=str(r.get("event") or "")
            events[ev]=events.get(ev,0)+1

            ts=parse_ts(r.get("ts"))
            if ts and (latest_event is None or ts > latest_event):
                latest_event=ts

            payload=r.get("payload") if isinstance(r.get("payload"),dict) else {}
            if payload.get("observability_generation")=="000078V4":
                generation_seen=True
            if ev=="incident_evidence_packed":
                incident_packed += 1

        mtime=dt.datetime.fromtimestamp(p.stat().st_mtime,dt.timezone.utc)
        rows.append({
            "path":str(p),
            "bytes":p.stat().st_size,
            "mtime_utc":mtime.isoformat(),
            "age_seconds":(now-mtime).total_seconds(),
            "records":len(records),
            "parse_errors":bad,
            "events":events,
            "generation_000078V4_seen":generation_seen,
            "latest_event_ts":latest_event.isoformat() if latest_event else None,
            "incident_packed_count":incident_packed,
            "required_events_present":{
                ev:events.get(ev,0)>0 for ev in sorted(REQUIRED_EVENTS)
            },
        })

    active=None
    for row in rows:
        req=row["required_events_present"]
        if (
            row["age_seconds"] <= 120
            and row["generation_000078V4_seen"]
            and req.get("runtime_start")
            and req.get("event_ray_bridge_started")
            and req.get("runtime_sample")
        ):
            active=row
            break

    if active:
        classification="OBSERVABILITY_CORE_RUNTIME_ACTIVE"
        next_step="000079V4_CORRELATION_BINDING_AND_HUMAN_INCIDENT_MARKER"
    elif rows:
        classification="OBSERVABILITY_BLACK_BOX_PRESENT_RUNTIME_INCOMPLETE"
        next_step="000078V4B_RUNTIME_ENTRYPOINT_DIAGNOSIS"
    else:
        classification="OBSERVABILITY_CORE_RUNTIME_NOT_ACTIVE_NO_BLACK_BOX"
        next_step="000078V4B_RUNTIME_ENTRYPOINT_DIAGNOSIS"

    run_dir=OUT_ER/stamp()
    run_dir.mkdir(parents=True,exist_ok=True)
    rp=run_dir/"observability_core_runtime_activation_000078V4A.json"

    report={
        "schema":"vertex-session-portal/observability-core-runtime-activation/1",
        "generated_at":now.isoformat(),
        "install":{
            "evidence":str(install),
            "status":install_data.get("status"),
            "restart_required":install_data.get("restart_required"),
        },
        "black_boxes_found":len(rows),
        "black_boxes":rows,
        "runtime_active":active is not None,
        "classification":classification,
        "next":next_step,
        "mutation":{
            "production_source_mutated":False,
            "running_process_mutated":False,
            "black_box_mutated":False,
            "event_ray_mutated":False,
        },
    }
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    print(f"INSTALL_STATUS={install_data.get('status')}")
    print(f"BLACK_BOXES_FOUND={len(rows)}")
    for i,row in enumerate(rows[:10],1):
        req=row["required_events_present"]
        print(
            f"BLACK_BOX_{i} PATH={row['path']} AGE_SEC={row['age_seconds']:.1f} "
            f"BYTES={row['bytes']} RECORDS={row['records']} "
            f"GEN_000078V4={str(row['generation_000078V4_seen']).upper()} "
            f"RUNTIME_START={req.get('runtime_start')} "
            f"FINGERPRINT={req.get('runtime_fingerprint')} "
            f"EVENT_RAY_BRIDGE={req.get('event_ray_bridge_started')} "
            f"METRIC_SAMPLE={req.get('runtime_sample')} "
            f"INCIDENT_PACKED={row['incident_packed_count']}"
        )

    print(f"RUNTIME_ACTIVE={str(active is not None).upper()}")
    print(f"CLASSIFICATION={classification}")
    print(f"NEXT={next_step}")
    print("PRODUCTION_MUTATION=FALSE")
    print("PROCESS_MUTATION=FALSE")
    print("BLACK_BOX_MUTATION=FALSE")
    print("EVENT_RAY_MUTATION=FALSE")
    print(f"EVIDENCE={rp}")
    print("OBSERVABILITY_CORE_RUNTIME_ACTIVATION_PROBE_000078V4A_RUN=PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
