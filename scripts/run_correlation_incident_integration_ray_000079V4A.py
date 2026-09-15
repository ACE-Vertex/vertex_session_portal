#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
ER = ROOT / "EVIDENCE" / "CORRELATION_INCIDENT_INTEGRATION_RAY_000079V4A"

SEARCH_TERMS = [
    "VraDispatchLane",
    "vra-dispatch-service",
    "Human Approval",
    "human approval",
    "STAGING_FIRST",
    "_incoming",
    "return-queue",
    "return_channel",
    "correlation_id",
    "origin_session",
    "origin_vera",
    "allocated_lane",
    "requested_lane",
    "Human Gate",
    "HUMAN_APPLY",
    "VRA_ORIGIN_UNRESOLVED",
    "sourceSessionId",
    "VeraBrowserSession",
    "Workstation",
    "evidence",
    "dispatch",
    "approval",
]

INCLUDE_EXT = {".ts",".tsx",".js",".jsx",".json",".scss",".css"}

def stamp():
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def safe_read(path: Path):
    try:
        if path.stat().st_size > 5*1024*1024:
            return None
        return path.read_text(encoding="utf-8",errors="replace")
    except Exception:
        return None

def relative(path: Path):
    try:
        return str(path.relative_to(ROOT)).replace("\\","/")
    except Exception:
        return str(path)

def scan():
    rows=[]
    for base in [ROOT/"src", ROOT/"electron", ROOT/"app"]:
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            pdir=Path(dirpath)
            dirnames[:] = [d for d in dirnames if d.lower() not in {
                "node_modules",".git","dist","out","build","coverage","cache"
            }]
            for fn in filenames:
                p=pdir/fn
                if p.suffix.lower() not in INCLUDE_EXT:
                    continue
                text=safe_read(p)
                if text is None:
                    continue
                lines=text.splitlines()
                hits=[]
                for idx,line in enumerate(lines,1):
                    matched=[t for t in SEARCH_TERMS if t.lower() in line.lower()]
                    if matched:
                        hits.append({
                            "line":idx,
                            "text":line[:800],
                            "terms":matched,
                        })
                if hits:
                    rows.append({
                        "path":relative(p),
                        "hit_count":len(hits),
                        "hits":hits[:200],
                    })
    rows.sort(key=lambda r:(-r["hit_count"],r["path"]))
    return rows

def classify(rows):
    blob="\n".join(
        h["text"]
        for r in rows
        for h in r["hits"]
    ).lower()

    required={
        "origin_capture": any(x in blob for x in ["origin_session","sourcesessionid","origin_vera"]),
        "human_approval": any(x in blob for x in ["human approval","human_approval","human gate"]),
        "incoming_publish": "_incoming" in blob,
        "correlation_id": "correlation_id" in blob,
        "return_queue": "return-queue" in blob or "return_channel" in blob,
        "allocated_lane": "allocated_lane" in blob,
        "requested_lane": "requested_lane" in blob,
    }

    file_paths=[r["path"].lower() for r in rows]
    likely_dispatch=[p for p in file_paths if "dispatch" in p or "vra" in p]
    likely_return=[p for p in file_paths if "return" in p or "evidence" in p]
    likely_vera=[p for p in file_paths if "verabrowsersession" in p]
    likely_workstation=[p for p in file_paths if "workstation" in p]
    likely_renderer=[p for p in file_paths if "/renderer/" in p or "renderer/src" in p]

    if all(required.values()):
        classification="INTEGRATION_ANCHORS_PRESENT"
        next_step="000079V4B_LIMITED_CORRELATION_BINDING_AND_INCIDENT_MARKER"
    else:
        classification="INTEGRATION_ANCHORS_PARTIAL"
        next_step="000079V4B_ADAPTER_OR_ANCHOR_REPAIR_PLAN"

    return {
        "required":required,
        "likely_dispatch_files":likely_dispatch[:50],
        "likely_return_files":likely_return[:50],
        "likely_vera_session_files":likely_vera[:50],
        "likely_workstation_files":likely_workstation[:50],
        "likely_renderer_files":likely_renderer[:50],
        "classification":classification,
        "next":next_step,
    }

def main():
    print("=== VERTEX SESSION PORTAL / CORRELATION + INCIDENT INTEGRATION RAY 000079V4A ===")
    if not ROOT.exists():
        print("PROJECT_ROOT=FAIL")
        return 2

    rows=scan()
    decision=classify(rows)

    run_dir=ER/stamp()
    run_dir.mkdir(parents=True,exist_ok=True)
    rp=run_dir/"correlation_incident_integration_ray_000079V4A.json"

    report={
        "schema":"vertex-session-portal/correlation-incident-integration-ray/1",
        "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "project_root":str(ROOT),
        "files_with_hits":len(rows),
        "rows":rows,
        **decision,
        "mutation":{
            "production_source_mutated":False,
            "running_process_mutated":False,
            "runtime_logs_mutated":False,
            "workstation_mutated":False,
        },
        "constraints":{
            "human_gate_preserve":True,
            "staging_first_preserve":True,
            "origin_immutable_preserve":True,
            "no_dom_scrape":True,
            "path_hidden_from_human_card":True,
            "workstation_lane_authority":True,
            "no_http_post_jobs_assumed":True,
        }
    }
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    print(f"FILES_WITH_HITS={len(rows)}")
    for i,r in enumerate(rows[:30],1):
        print(f"FILE_{i} PATH={r['path']} HITS={r['hit_count']}")
        for h in r["hits"][:8]:
            compact=h["text"].strip().replace("\t"," ")
            print(f"  L{h['line']} TERMS={','.join(h['terms'])} TEXT={compact[:300]}")
    for k,v in decision["required"].items():
        print(f"ANCHOR_{k.upper()}={str(v).upper()}")
    print(f"LIKELY_DISPATCH_FILES={len(decision['likely_dispatch_files'])}")
    for p in decision["likely_dispatch_files"][:20]:
        print(f"DISPATCH_FILE={p}")
    print(f"LIKELY_RETURN_FILES={len(decision['likely_return_files'])}")
    for p in decision["likely_return_files"][:20]:
        print(f"RETURN_FILE={p}")
    print(f"LIKELY_VERA_SESSION_FILES={len(decision['likely_vera_session_files'])}")
    for p in decision["likely_vera_session_files"][:20]:
        print(f"VERA_SESSION_FILE={p}")
    print(f"LIKELY_WORKSTATION_FILES={len(decision['likely_workstation_files'])}")
    for p in decision["likely_workstation_files"][:20]:
        print(f"WORKSTATION_FILE={p}")
    print(f"CLASSIFICATION={decision['classification']}")
    print(f"NEXT={decision['next']}")
    print("PRODUCTION_MUTATION=FALSE")
    print("PROCESS_MUTATION=FALSE")
    print("WORKSTATION_MUTATION=FALSE")
    print(f"EVIDENCE={rp}")
    print("CORRELATION_INCIDENT_INTEGRATION_RAY_000079V4A_RUN=PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
