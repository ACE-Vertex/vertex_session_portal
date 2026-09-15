#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SRC_MAIN = ROOT / "src" / "main" / "index.ts"
OBS_CORE = ROOT / "src" / "main" / "observability" / "vertex-observability-core.ts"
OBS_INDEX = ROOT / "src" / "main" / "observability" / "index.ts"
ER = ROOT / "EVIDENCE" / "OBSERVABILITY_RUNTIME_ENTRYPOINT_DIAGNOSIS_000078V4B"

OBS_MARKERS = [
    "VERTEX_OBSERVABILITY_CORE_000078V4",
    "observability_generation",
    "event_ray_bridge_started",
    "black-box.jsonl",
]
EVENT_RAY_MARKERS = [
    "focus-scroll-event-ray.jsonl",
    "event_ray_started",
    "ime_submit_collision_candidate",
]
CANDIDATE_DIRS = ["out","dist","build","release",".vite","app","resources"]

def stamp():
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def sha256(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def file_meta(path: Path):
    if not path.exists():
        return {"exists":False,"path":str(path)}
    st=path.stat()
    return {
        "exists":True,
        "path":str(path),
        "bytes":st.st_size,
        "mtime_utc":dt.datetime.fromtimestamp(st.st_mtime,dt.timezone.utc).isoformat(),
        "sha256":sha256(path) if st.st_size <= 50*1024*1024 else None,
    }

def read_text_limited(path: Path, max_bytes=20*1024*1024):
    try:
        if path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8",errors="replace")
    except Exception:
        return None

def package_info():
    p=ROOT/"package.json"
    if not p.exists():
        return {"exists":False}
    try:
        d=json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as e:
        return {"exists":True,"parse_error":str(e),"meta":file_meta(p)}
    return {
        "exists":True,
        "meta":file_meta(p),
        "name":d.get("name"),
        "version":d.get("version"),
        "main":d.get("main"),
        "scripts":d.get("scripts"),
        "type":d.get("type"),
    }

def config_scan():
    patterns=[
        "electron.vite.config.ts","electron.vite.config.js","electron-vite.config.ts",
        "electron-vite.config.js","vite.config.ts","vite.config.js",
        "electron-builder.yml","electron-builder.yaml","electron-builder.json",
    ]
    rows=[]
    for name in patterns:
        p=ROOT/name
        if not p.exists():
            continue
        text=read_text_limited(p,2*1024*1024) or ""
        interesting=[]
        for raw in text.splitlines():
            s=raw.strip()
            if any(k.lower() in s.lower() for k in (
                "entry","outdir","main","build","asar","files","directories","src/main"
            )):
                interesting.append(s[:500])
        rows.append({"path":str(p),"meta":file_meta(p),"interesting_lines":interesting[:80]})
    return rows

def process_snapshot():
    ps = "$root='G:\\Vertex_Project\\Development\\vertex_session_portal'; Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'electron|vertex.*portal' -or ($_.CommandLine -and $_.CommandLine -match 'vertex_session_portal|vertex-session-portal') } | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Depth 4 -Compress"
    p=subprocess.run(
        ["powershell.exe","-NoProfile","-Command",ps],
        capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=20
    )
    raw=p.stdout.strip()
    parsed=[]
    if raw:
        try:
            obj=json.loads(raw)
            parsed=obj if isinstance(obj,list) else [obj]
        except Exception:
            parsed=[]
    rows=[]
    root_l=str(ROOT).lower()
    for x in parsed:
        cmd=x.get("CommandLine")
        exe=x.get("ExecutablePath")
        cmd_l=(cmd or "").lower()
        exe_l=(exe or "").lower()
        rows.append({
            "pid":x.get("ProcessId"),
            "ppid":x.get("ParentProcessId"),
            "name":x.get("Name"),
            "executable_path":exe,
            "command_line":cmd,
            "creation_date":x.get("CreationDate"),
            "command_mentions_project_root":root_l in cmd_l,
            "electron_node_modules_runtime":"node_modules\\electron" in exe_l or "node_modules/electron" in exe_l,
            "looks_packaged":(
                bool(exe)
                and "node_modules\\electron" not in exe_l
                and "node_modules/electron" not in exe_l
                and str(x.get("Name") or "").lower() != "powershell.exe"
            ),
        })
    return {"exit_code":p.returncode,"stderr":p.stderr[-4000:],"rows":rows}

def candidate_files():
    files=[]
    seen=set()
    for dirname in CANDIDATE_DIRS:
        base=ROOT/dirname
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            pdir=Path(dirpath)
            try:
                depth=len(pdir.relative_to(base).parts)
            except Exception:
                depth=99
            if depth >= 7:
                dirnames[:] = []
            dirnames[:] = [d for d in dirnames if d.lower() not in {
                "node_modules",".git","cache","code cache","gpucache"
            }]
            for fn in filenames:
                p=pdir/fn
                if p.suffix.lower() not in {".js",".cjs",".mjs",".asar",".json"}:
                    continue
                key=str(p).lower()
                if key in seen:
                    continue
                seen.add(key)
                files.append(p)
                if len(files)>=5000:
                    return files
    return files

def marker_scan(files):
    matches=[]
    asars=[]
    for p in files:
        if p.suffix.lower()==".asar":
            asars.append(file_meta(p))
            continue
        text=read_text_limited(p)
        if text is None:
            continue
        obs=[m for m in OBS_MARKERS if m in text]
        ray=[m for m in EVENT_RAY_MARKERS if m in text]
        if obs or ray:
            matches.append({
                "path":str(p),
                "meta":file_meta(p),
                "observability_markers":obs,
                "event_ray_markers":ray,
            })
    matches.sort(
        key=lambda r:(
            1 if r["observability_markers"] else 0,
            1 if r["event_ray_markers"] else 0,
            r["meta"].get("mtime_utc",""),
        ),
        reverse=True,
    )
    return matches,asars

def source_entrypoint_check():
    main_text=read_text_limited(SRC_MAIN) or ""
    obs_index_text=read_text_limited(OBS_INDEX) or ""
    core_text=read_text_limited(OBS_CORE) or ""
    return {
        "src_main":file_meta(SRC_MAIN),
        "obs_core":file_meta(OBS_CORE),
        "obs_index":file_meta(OBS_INDEX),
        "src_main_has_observability_import":"import './observability'" in main_text,
        "src_main_import_count":main_text.count("import './observability'"),
        "obs_index_auto_activates":"activateVertexObservabilityCore()" in obs_index_text,
        "obs_index_waits_when_ready":"app.whenReady()" in obs_index_text,
        "core_has_generation":"000078V4" in core_text,
        "core_has_black_box":"black-box.jsonl" in core_text,
    }

def classify(src, package, processes, matches, asars):
    obs_build=[m for m in matches if m["observability_markers"]]
    ray_build=[m for m in matches if m["event_ray_markers"]]
    ray_without_obs=[m for m in matches if m["event_ray_markers"] and not m["observability_markers"]]
    proc_rows=processes["rows"]
    dev=[p for p in proc_rows if p["command_mentions_project_root"]]
    packaged=[p for p in proc_rows if p["looks_packaged"]]

    package_main=str(package.get("main") or "")
    package_main_path=(ROOT/package_main).resolve() if package_main else None
    package_main_exists=bool(package_main_path and package_main_path.exists())
    package_main_has_obs=False
    package_main_has_ray=False
    if package_main_exists:
        text=read_text_limited(package_main_path) or ""
        package_main_has_obs=any(x in text for x in OBS_MARKERS)
        package_main_has_ray=any(x in text for x in EVENT_RAY_MARKERS)

    if not src["src_main_has_observability_import"] or not src["core_has_generation"]:
        classification="SOURCE_INSTALL_NOT_PRESENT"
        next_step="000078V4C_SOURCE_INSTALL_REPAIR"
    elif package_main_exists and package_main_has_ray and not package_main_has_obs:
        classification="ACTIVE_BUILD_STALE_EVENT_RAY_PRESENT_OBSERVABILITY_MISSING"
        next_step="000078V4C_REBUILD_RUNNING_MAIN_BUNDLE"
    elif ray_without_obs and not obs_build:
        classification="BUILD_ARTIFACT_STALE_EVENT_RAY_PRESENT_OBSERVABILITY_MISSING"
        next_step="000078V4C_REBUILD_RUNNING_MAIN_BUNDLE"
    elif obs_build and not dev and packaged:
        classification="SOURCE_AND_BUILD_HAVE_CORE_PACKAGED_RUNTIME_PATH_MISMATCH"
        next_step="000078V4C_PACKAGED_RUNTIME_PATH_DIAGNOSIS"
    elif obs_build:
        classification="BUILD_CONTAINS_CORE_RUNTIME_DID_NOT_START_IT"
        next_step="000078V4C_RUNTIME_STARTUP_ERROR_DIAGNOSIS"
    elif asars and packaged:
        classification="PACKAGED_ASAR_RUNTIME_REQUIRES_BUILD_OWNERSHIP_CONFIRMATION"
        next_step="000078V4C_PACKAGED_BUILD_DIAGNOSIS"
    elif dev:
        classification="DEV_RUNTIME_BUILD_ENTRYPOINT_AMBIGUOUS"
        next_step="000078V4C_DEV_BUNDLE_ENTRYPOINT_DIAGNOSIS"
    else:
        classification="RUNTIME_ENTRYPOINT_AMBIGUOUS"
        next_step="000078V4C_RUNTIME_ENTRYPOINT_DIAGNOSIS"

    return {
        "classification":classification,
        "next":next_step,
        "derived":{
            "package_main":package_main or None,
            "package_main_path":str(package_main_path) if package_main_path else None,
            "package_main_exists":package_main_exists,
            "package_main_has_observability":package_main_has_obs,
            "package_main_has_event_ray":package_main_has_ray,
            "observability_build_match_count":len(obs_build),
            "event_ray_build_match_count":len(ray_build),
            "event_ray_without_observability_count":len(ray_without_obs),
            "dev_process_candidate_count":len(dev),
            "packaged_process_candidate_count":len(packaged),
            "asar_candidate_count":len(asars),
        }
    }

def main():
    print("=== VERTEX SESSION PORTAL / OBSERVABILITY RUNTIME ENTRYPOINT DIAGNOSIS 000078V4B ===")
    if not ROOT.exists():
        print("PROJECT_ROOT=FAIL")
        return 2

    src=source_entrypoint_check()
    package=package_info()
    configs=config_scan()
    processes=process_snapshot()
    files=candidate_files()
    matches,asars=marker_scan(files)
    decision=classify(src,package,processes,matches,asars)

    run_dir=ER/stamp()
    run_dir.mkdir(parents=True,exist_ok=True)
    rp=run_dir/"observability_runtime_entrypoint_diagnosis_000078V4B.json"
    report={
        "schema":"vertex-session-portal/observability-runtime-entrypoint-diagnosis/1",
        "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "source":src,
        "package":package,
        "configs":configs,
        "process_snapshot":processes,
        "candidate_file_count":len(files),
        "marker_matches":matches[:100],
        "asar_candidates":asars[:50],
        **decision,
        "scientific_boundary":{
            "observability_source_installed":bool(
                src["src_main_has_observability_import"] and src["core_has_generation"]
            ),
            "observability_runtime_active":False,
            "runtime_entrypoint_root_cause_identified":decision["classification"] not in {
                "RUNTIME_ENTRYPOINT_AMBIGUOUS",
                "DEV_RUNTIME_BUILD_ENTRYPOINT_AMBIGUOUS"
            },
        },
        "mutation":{
            "production_source_mutated":False,
            "running_process_mutated":False,
            "build_artifact_mutated":False,
            "event_ray_mutated":False,
            "black_box_mutated":False,
        },
    }
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    d=decision["derived"]
    print(f"SRC_MAIN_HAS_OBSERVABILITY_IMPORT={str(src['src_main_has_observability_import']).upper()}")
    print(f"CORE_GENERATION_000078V4_PRESENT={str(src['core_has_generation']).upper()}")
    print(f"PACKAGE_MAIN={d['package_main']}")
    print(f"PACKAGE_MAIN_PATH={d['package_main_path']}")
    print(f"PACKAGE_MAIN_EXISTS={str(d['package_main_exists']).upper()}")
    print(f"PACKAGE_MAIN_HAS_EVENT_RAY={str(d['package_main_has_event_ray']).upper()}")
    print(f"PACKAGE_MAIN_HAS_OBSERVABILITY={str(d['package_main_has_observability']).upper()}")
    print(f"PROCESS_CANDIDATES={len(processes['rows'])}")
    for i,p in enumerate(processes["rows"][:20],1):
        print(
            f"PROCESS_{i} PID={p['pid']} NAME={p['name']} "
            f"CREATED={p['creation_date']} ROOT_IN_CMD={p['command_mentions_project_root']} "
            f"PACKAGED={p['looks_packaged']} EXE={p['executable_path']} "
            f"CMD={p['command_line']}"
        )
    print(f"CANDIDATE_BUILD_FILES_SCANNED={len(files)}")
    print(f"OBSERVABILITY_BUILD_MATCHES={d['observability_build_match_count']}")
    print(f"EVENT_RAY_BUILD_MATCHES={d['event_ray_build_match_count']}")
    print(f"EVENT_RAY_WITHOUT_OBSERVABILITY={d['event_ray_without_observability_count']}")
    for i,m in enumerate(matches[:20],1):
        print(
            f"MATCH_{i} PATH={m['path']} "
            f"OBS={','.join(m['observability_markers']) or '-'} "
            f"RAY={','.join(m['event_ray_markers']) or '-'}"
        )
    print(f"ASAR_CANDIDATES={d['asar_candidate_count']}")
    for i,a in enumerate(asars[:10],1):
        print(f"ASAR_{i} PATH={a['path']} MTIME={a.get('mtime_utc')} BYTES={a.get('bytes')}")
    print(f"CLASSIFICATION={decision['classification']}")
    print(f"NEXT={decision['next']}")
    print("PRODUCTION_MUTATION=FALSE")
    print("PROCESS_MUTATION=FALSE")
    print("BUILD_MUTATION=FALSE")
    print(f"EVIDENCE={rp}")
    print("OBSERVABILITY_RUNTIME_ENTRYPOINT_DIAGNOSIS_000078V4B_RUN=PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
