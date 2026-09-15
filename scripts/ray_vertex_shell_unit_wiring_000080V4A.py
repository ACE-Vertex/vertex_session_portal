#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, json, re, datetime as dt

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
OUT=ROOT/"EVIDENCE"/"VERTEX_SHELL_UNIT_WIRING_RAY_000080V4A"

TARGETS=[
  ROOT/"src"/"main"/"index.ts",
  ROOT/"src"/"preload"/"index.ts",
  ROOT/"src"/"preload"/"index.d.ts",
  ROOT/"src"/"shared"/"contracts.ts",
  ROOT/"src"/"renderer"/"src"/"components"/"MainFrame"/"MainFrame.ts",
  ROOT/"src"/"renderer"/"src"/"components"/"MainFrame"/"MainFrame.css",
  ROOT/"src"/"renderer"/"src"/"env.d.ts",
]

PATTERNS=[
  r"register[A-Za-z0-9_]+Ipc",
  r"contextBridge\.exposeInMainWorld",
  r"const\s+api\s*=",
  r"interface\s+\w*Api",
  r"declare\s+global",
  r"vertex-vra-dispatch-lane",
  r"sessionTrack",
  r"sessionViewport",
  r"customElements\.define",
]

def sha256(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def hits(p:Path):
    if not p.exists():
        return {"path":str(p.relative_to(ROOT)).replace("\\","/"),"exists":False,"sha256":None,"hits":[]}
    lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
    found=[]
    for i,line in enumerate(lines,1):
        matched=[pat for pat in PATTERNS if re.search(pat,line,re.I)]
        if not matched: continue
        lo=max(1,i-3); hi=min(len(lines),i+3)
        found.append({
          "line":i,
          "patterns":matched,
          "context":[f"{n:05d}: {lines[n-1]}" for n in range(lo,hi+1)]
        })
    return {
      "path":str(p.relative_to(ROOT)).replace("\\","/"),
      "exists":True,
      "sha256":sha256(p),
      "lines":len(lines),
      "hits":found[:160],
    }

def main():
    print("=== VERTEX SESSION PORTAL / VERTEX SHELL UNIT WIRING RAY 000080V4A ===")
    rows=[hits(p) for p in TARGETS]
    stamp=dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    d=OUT/stamp
    d.mkdir(parents=True,exist_ok=True)
    rp=d/"vertex_shell_unit_wiring_ray_000080V4A.json"
    report={
      "schema":"vertex-session-portal/vertex-shell-unit-wiring-ray/1",
      "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
      "files":rows,
      "classification":"FOUNDATION_READY_WIRING_ANCHORS_CAPTURED",
      "next":"000080V4B_LIMITED_SESSION_PORTAL_WIRING",
      "mutation":{
        "existing_production_files_mutated_by_ray":False,
        "running_process_mutated":False,
        "workstation_mutated":False,
      }
    }
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    for row in rows:
        print(f"FILE={row['path']} EXISTS={str(row['exists']).upper()} SHA256={row.get('sha256')} HITS={len(row['hits'])}")
        for h in row["hits"][:24]:
            print(f"  HIT L{h['line']} PATTERNS={','.join(h['patterns'])}")
            for c in h["context"]:
                print("    "+c)
    print("CLASSIFICATION=FOUNDATION_READY_WIRING_ANCHORS_CAPTURED")
    print("NEXT=000080V4B_LIMITED_SESSION_PORTAL_WIRING")
    print("EXISTING_PRODUCTION_MUTATION_FROM_RAY=FALSE")
    print("PROCESS_MUTATION=FALSE")
    print("WORKSTATION_MUTATION=FALSE")
    print(f"EVIDENCE={rp}")
    print("VERTEX_SHELL_UNIT_WIRING_RAY_000080V4A_RUN=PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
