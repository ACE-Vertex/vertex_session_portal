#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt, json, re
from pathlib import Path

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
ER=ROOT/"EVIDENCE"/"INCIDENT_MARKER_HOST_CONTEXT_DIAGNOSIS_000079V4D"

FILES=[
  ROOT/"src"/"main"/"diagnostics"/"focus-scroll-event-ray.ts",
  ROOT/"src"/"main"/"observability"/"vertex-observability-core.ts",
  ROOT/"src"/"renderer"/"src"/"components"/"MainFrame"/"MainFrame.ts",
  ROOT/"src"/"renderer"/"src"/"components"/"VraDispatchLane"/"VraDispatchLane.ts",
  ROOT/"src"/"preload"/"index.ts",
  ROOT/"src"/"main"/"ipc"/"register-vra-dispatch-ipc.ts",
  ROOT/"src"/"shared"/"contracts.ts",
  ROOT/"src"/"main"/"index.ts",
]

TERMS=[
  "executeJavaScript","web-contents-created","webContents","BrowserWindow",
  "did-finish-load","dom-ready","focus-scroll-event-ray","PAGE_OBSERVER",
  "installIncidentMarker","MARK INCIDENT","human_incident_marker",
  "vertex-vra-dispatch-lane","ipcRenderer","ipcMain","contextBridge",
  "VraDispatchLane","MainFrame","event_ray_incident_candidate"
]

def stamp(): return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def snippets(p:Path):
    if not p.exists(): return {"path":str(p.relative_to(ROOT)).replace("\\","/"),"exists":False,"hits":[]}
    text=p.read_text(encoding="utf-8",errors="replace")
    lines=text.splitlines()
    hits=[]
    for i,line in enumerate(lines,1):
        mt=[t for t in TERMS if t.lower() in line.lower()]
        if mt:
            lo=max(1,i-2); hi=min(len(lines),i+2)
            hits.append({
              "line":i,"terms":mt,
              "context":[f"{n:05d}: {lines[n-1][:500]}" for n in range(lo,hi+1)]
            })
    return {"path":str(p.relative_to(ROOT)).replace("\\","/"),"exists":True,"hits":hits[:200]}

def main():
    print("=== VERTEX SESSION PORTAL / INCIDENT MARKER HOST CONTEXT DIAGNOSIS 000079V4D ===")
    rows=[snippets(p) for p in FILES]
    bypath={r["path"]:r for r in rows}

    ray_path="src/main/diagnostics/focus-scroll-event-ray.ts"
    mainframe_path="src/renderer/src/components/MainFrame/MainFrame.ts"
    ray_text=(ROOT/ray_path).read_text(encoding="utf-8",errors="replace") if (ROOT/ray_path).exists() else ""
    mf_text=(ROOT/mainframe_path).read_text(encoding="utf-8",errors="replace") if (ROOT/mainframe_path).exists() else ""

    marker_in_ray = "MARK INCIDENT" in ray_text and "human_incident_marker" in ray_text
    marker_gate_in_ray = "vertex-vra-dispatch-lane" in ray_text
    execute_js = "executeJavaScript" in ray_text
    webcontents_hook = "web-contents-created" in ray_text or ".webContents" in ray_text or "webContents" in ray_text
    host_has_lane = "<vertex-vra-dispatch-lane" in mf_text

    if marker_in_ray and marker_gate_in_ray and execute_js and host_has_lane:
        classification="MARKER_UI_EMBEDDED_IN_EVENT_RAY_INJECTED_PAGE_CONTEXT"
        next_step="000079V4E_MOVE_HUMAN_MARKER_TO_HOST_RENDERER_BRIDGE"
    elif marker_in_ray and host_has_lane:
        classification="MARKER_HOST_CONTEXT_MISMATCH_LIKELY"
        next_step="000079V4E_HOST_MARKER_BRIDGE_DESIGN"
    else:
        classification="INCIDENT_MARKER_CONTEXT_UNRESOLVED"
        next_step="000079V4E_DEEP_CONTEXT_RAY"

    run_dir=ER/stamp(); run_dir.mkdir(parents=True,exist_ok=True)
    rp=run_dir/"incident_marker_host_context_diagnosis_000079V4D.json"
    report={
      "schema":"vertex-session-portal/incident-marker-host-context-diagnosis/1",
      "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
      "observations":{
        "marker_in_event_ray_source":marker_in_ray,
        "marker_host_gate_in_event_ray_source":marker_gate_in_ray,
        "event_ray_execute_javascript":execute_js,
        "event_ray_webcontents_hook":webcontents_hook,
        "mainframe_hosts_vra_dispatch_lane":host_has_lane,
      },
      "files":rows,
      "classification":classification,
      "next":next_step,
      "mutation":{
        "production_source_mutated":False,
        "running_process_mutated":False,
        "runtime_logs_mutated":False,
        "workstation_mutated":False,
      }
    }
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    for k,v in report["observations"].items():
        print(f"{k.upper()}={str(v).upper()}")
    for r in rows:
        print(f"FILE={r['path']} EXISTS={str(r['exists']).upper()} HITS={len(r['hits'])}")
        for h in r["hits"][:12]:
            print(f"  HIT L{h['line']} TERMS={','.join(h['terms'])}")
            for c in h["context"]:
                print("    "+c)
    print(f"CLASSIFICATION={classification}")
    print(f"NEXT={next_step}")
    print("PRODUCTION_MUTATION=FALSE")
    print("PROCESS_MUTATION=FALSE")
    print("RUNTIME_LOG_MUTATION=FALSE")
    print("WORKSTATION_MUTATION=FALSE")
    print(f"EVIDENCE={rp}")
    print("INCIDENT_MARKER_HOST_CONTEXT_DIAGNOSIS_000079V4D_RUN=PASS")
    return 0

if __name__=="__main__": raise SystemExit(main())
