#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
BUNDLE = ROOT / "out" / "main" / "index.js"
SRC_MAIN = ROOT / "src" / "main" / "index.ts"
OBS_INDEX = ROOT / "src" / "main" / "observability" / "index.ts"
OBS_CORE = ROOT / "src" / "main" / "observability" / "vertex-observability-core.ts"
ER = ROOT / "EVIDENCE" / "OBSERVABILITY_RUNTIME_STARTUP_ERROR_DIAGNOSIS_000078V4C"
USER_DATA = Path(os.environ.get("APPDATA","")) / "vertex-session-portal"
OBS_DIR = USER_DATA / "observability"
BLACK_BOX = OBS_DIR / "black-box.jsonl"
EVENT_RAY = USER_DATA / "event-ray" / "focus-scroll-event-ray.jsonl"

def now():
    return dt.datetime.now(dt.timezone.utc)

def stamp():
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def iso_mtime(p: Path):
    if not p.exists():
        return None
    return dt.datetime.fromtimestamp(p.stat().st_mtime,dt.timezone.utc).isoformat()

def read_text(p: Path, limit=30*1024*1024):
    try:
        if p.stat().st_size > limit:
            return ""
        return p.read_text(encoding="utf-8",errors="replace")
    except Exception:
        return ""

def main_process():
    ps = "$root='G:\\Vertex_Project\\Development\\vertex_session_portal'; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'electron.exe' -and $_.CommandLine -and $_.CommandLine -match 'vertex_session_portal' -and $_.CommandLine -notmatch '--type=' } | Select-Object -First 1 ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Compress"
    p=subprocess.run(
        ["powershell.exe","-NoProfile","-Command",ps],
        capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=20
    )
    raw=p.stdout.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return {"parse_error":raw,"stderr":p.stderr[-2000:]}

def creation_ms(v):
    if not isinstance(v,str):
        return None
    m=re.search(r"/Date\((\d+)\)/",v)
    if m:
        return int(m.group(1))
    try:
        return int(dt.datetime.fromisoformat(v.replace("Z","+00:00")).timestamp()*1000)
    except Exception:
        return None

def node_check():
    if not BUNDLE.exists():
        return {"exit_code":None,"stdout":"","stderr":"bundle missing"}
    p=subprocess.run(
        ["node.exe","--check",str(BUNDLE)],
        capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30
    )
    return {"exit_code":p.returncode,"stdout":p.stdout[-4000:],"stderr":p.stderr[-4000:]}

def acl_snapshot(path: Path):
    ps = f"$p={json.dumps(str(path))}; if (Test-Path -LiteralPath $p) {{ Get-Acl -LiteralPath $p | Select-Object Path,Owner,AccessToString | ConvertTo-Json -Depth 3 -Compress }} else {{ '{{\"missing\":true}}' }}"
    p=subprocess.run(
        ["powershell.exe","-NoProfile","-Command",ps],
        capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=20
    )
    raw=p.stdout.strip()
    try:
        return json.loads(raw) if raw else None
    except Exception:
        return {"raw":raw,"stderr":p.stderr[-2000:]}

def marker_context(text: str, marker: str, radius=700):
    i=text.find(marker)
    if i < 0:
        return None
    start=max(0,i-radius)
    end=min(len(text),i+len(marker)+radius)
    return text[start:end]

def find_recent_logs():
    rows=[]
    if not USER_DATA.exists():
        return rows
    cutoff=now().timestamp()-3600
    for dirpath,dirnames,filenames in os.walk(USER_DATA):
        pdir=Path(dirpath)
        try:
            depth=len(pdir.relative_to(USER_DATA).parts)
        except Exception:
            depth=99
        if depth>=5:
            dirnames[:]=[]
        dirnames[:]=[d for d in dirnames if d.lower() not in {
            "cache","code cache","gpucache","shadercache"
        }]
        for fn in filenames:
            p=pdir/fn
            if p.suffix.lower() not in {".log",".txt",".jsonl"}:
                continue
            try:
                st=p.stat()
            except Exception:
                continue
            if st.st_mtime < cutoff:
                continue
            rows.append({
                "path":str(p),
                "mtime_utc":dt.datetime.fromtimestamp(st.st_mtime,dt.timezone.utc).isoformat(),
                "bytes":st.st_size,
            })
    rows.sort(key=lambda x:x["mtime_utc"],reverse=True)
    return rows[:100]

def main():
    print("=== VERTEX SESSION PORTAL / OBSERVABILITY RUNTIME STARTUP ERROR DIAGNOSIS 000078V4C ===")
    if not ROOT.exists():
        print("PROJECT_ROOT=FAIL")
        return 2

    bundle_text=read_text(BUNDLE)
    src_main_text=read_text(SRC_MAIN)
    obs_index_text=read_text(OBS_INDEX)
    obs_core_text=read_text(OBS_CORE)

    proc=main_process()
    proc_created_ms=creation_ms(proc.get("CreationDate")) if isinstance(proc,dict) else None
    bundle_mtime_ms=int(BUNDLE.stat().st_mtime*1000) if BUNDLE.exists() else None

    activation_tokens={
        "bundle_has_observability_generation":"000078V4" in bundle_text,
        "bundle_has_black_box":"black-box.jsonl" in bundle_text,
        "bundle_has_event_ray_bridge":"event_ray_bridge_started" in bundle_text,
        "bundle_has_runtime_start":"'runtime_start'" in bundle_text or '"runtime_start"' in bundle_text,
        "bundle_has_activate_symbol":"activateVertexObservabilityCore" in bundle_text,
        "bundle_has_start_call":".start()" in bundle_text,
        "bundle_has_when_ready":"whenReady()" in bundle_text,
        "source_main_import_count":src_main_text.count("import './observability'"),
        "source_obs_index_activation_call":"activateVertexObservabilityCore()" in obs_index_text,
        "source_obs_index_when_ready":"app.whenReady()" in obs_index_text,
        "source_core_start_method":"start(): void" in obs_core_text,
    }

    contexts={}
    for marker in (
        "activateVertexObservabilityCore",
        "observability_generation",
        "event_ray_bridge_started",
        "black-box.jsonl",
        "runtime_start",
    ):
        ctx=marker_context(bundle_text,marker)
        if ctx is not None:
            contexts[marker]=ctx

    check=node_check()

    paths={
        "user_data":{
            "path":str(USER_DATA),
            "exists":USER_DATA.exists(),
            "mtime_utc":iso_mtime(USER_DATA),
        },
        "observability_dir":{
            "path":str(OBS_DIR),
            "exists":OBS_DIR.exists(),
            "mtime_utc":iso_mtime(OBS_DIR),
        },
        "black_box":{
            "path":str(BLACK_BOX),
            "exists":BLACK_BOX.exists(),
            "mtime_utc":iso_mtime(BLACK_BOX),
            "bytes":BLACK_BOX.stat().st_size if BLACK_BOX.exists() else None,
        },
        "event_ray":{
            "path":str(EVENT_RAY),
            "exists":EVENT_RAY.exists(),
            "mtime_utc":iso_mtime(EVENT_RAY),
            "bytes":EVENT_RAY.stat().st_size if EVENT_RAY.exists() else None,
        },
    }

    if BLACK_BOX.exists():
        classification="OBSERVABILITY_BLACK_BOX_APPEARED_AFTER_PRIOR_PROBE"
        next_step="000078V4D_RUNTIME_ACTIVATION_RECHECK"
    elif proc_created_ms and bundle_mtime_ms and bundle_mtime_ms > proc_created_ms + 1000:
        classification="RUNNING_MAIN_PROCESS_PREDATES_CURRENT_OBSERVABILITY_BUNDLE"
        next_step="RESTART_SESSION_PORTAL_THEN_000078V4D_ACTIVATION_RECHECK"
    elif not activation_tokens["bundle_has_activate_symbol"] or not activation_tokens["bundle_has_when_ready"]:
        classification="OBSERVABILITY_ACTIVATION_PATH_MISSING_FROM_BUNDLE"
        next_step="000078V4D_BUILD_ACTIVATION_REPAIR"
    elif check["exit_code"] not in (0,None):
        classification="MAIN_BUNDLE_SYNTAX_INVALID"
        next_step="000078V4D_BUILD_REPAIR"
    elif not paths["user_data"]["exists"] or not paths["event_ray"]["exists"]:
        classification="RUNTIME_USERDATA_PATH_MISMATCH"
        next_step="000078V4D_USERDATA_PATH_DIAGNOSIS"
    else:
        classification="ACTIVATION_PRESENT_CURRENT_BUNDLE_NO_BLACK_BOX_PROBABLE_RUNTIME_START_EXCEPTION"
        next_step="000078V4D_BOOTSTRAP_SENTINEL_AND_EXCEPTION_CAPTURE"

    run_dir=ER/stamp()
    run_dir.mkdir(parents=True,exist_ok=True)
    rp=run_dir/"observability_runtime_startup_error_diagnosis_000078V4C.json"

    report={
        "schema":"vertex-session-portal/observability-runtime-startup-error-diagnosis/1",
        "generated_at":now().isoformat(),
        "main_process":proc,
        "main_process_created_ms":proc_created_ms,
        "bundle":{
            "path":str(BUNDLE),
            "exists":BUNDLE.exists(),
            "mtime_utc":iso_mtime(BUNDLE),
            "mtime_ms":bundle_mtime_ms,
            "bytes":BUNDLE.stat().st_size if BUNDLE.exists() else None,
            "node_check":check,
        },
        "bundle_newer_than_process":bool(
            proc_created_ms and bundle_mtime_ms and bundle_mtime_ms > proc_created_ms + 1000
        ),
        "activation_tokens":activation_tokens,
        "marker_contexts":contexts,
        "runtime_paths":paths,
        "user_data_acl":acl_snapshot(USER_DATA),
        "recent_runtime_logs":find_recent_logs(),
        "classification":classification,
        "next":next_step,
        "scientific_boundary":{
            "source_contains_core":True,
            "build_contains_core":activation_tokens["bundle_has_observability_generation"],
            "runtime_black_box_active":BLACK_BOX.exists(),
            "runtime_root_cause_identified":classification not in {
                "ACTIVATION_PRESENT_CURRENT_BUNDLE_NO_BLACK_BOX_PROBABLE_RUNTIME_START_EXCEPTION"
            },
        },
        "mutation":{
            "production_source_mutated":False,
            "running_process_mutated":False,
            "build_artifact_mutated":False,
            "user_data_mutated":False,
            "event_ray_mutated":False,
        },
    }
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    print(f"MAIN_PROCESS_PID={proc.get('ProcessId') if isinstance(proc,dict) else None}")
    print(f"MAIN_PROCESS_CREATED_MS={proc_created_ms}")
    print(f"BUNDLE_MTIME_MS={bundle_mtime_ms}")
    print(f"BUNDLE_NEWER_THAN_PROCESS={str(report['bundle_newer_than_process']).upper()}")
    print(f"BUNDLE_NODE_CHECK_EXIT={check['exit_code']}")
    for k,v in activation_tokens.items():
        print(f"{k.upper()}={v}")
    print(f"USER_DATA_EXISTS={str(paths['user_data']['exists']).upper()}")
    print(f"OBSERVABILITY_DIR_EXISTS={str(paths['observability_dir']['exists']).upper()}")
    print(f"BLACK_BOX_EXISTS={str(paths['black_box']['exists']).upper()}")
    print(f"EVENT_RAY_EXISTS={str(paths['event_ray']['exists']).upper()}")
    print(f"RECENT_RUNTIME_LOGS={len(report['recent_runtime_logs'])}")
    for i,row in enumerate(report["recent_runtime_logs"][:20],1):
        print(f"RECENT_LOG_{i} PATH={row['path']} MTIME={row['mtime_utc']} BYTES={row['bytes']}")
    print(f"CLASSIFICATION={classification}")
    print(f"NEXT={next_step}")
    print("PRODUCTION_MUTATION=FALSE")
    print("PROCESS_MUTATION=FALSE")
    print("BUILD_MUTATION=FALSE")
    print(f"EVIDENCE={rp}")
    print("OBSERVABILITY_RUNTIME_STARTUP_ERROR_DIAGNOSIS_000078V4C_RUN=PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
