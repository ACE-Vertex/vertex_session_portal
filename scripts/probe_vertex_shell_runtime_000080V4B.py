#!/usr/bin/env python3
from pathlib import Path
import datetime as dt, json, os

USER_DATA=Path(os.environ.get("APPDATA",""))/"vertex-session-portal"
LOG=USER_DATA/"vertex-shell"/"host-bridge.jsonl"
HISTORY=USER_DATA/"vertex-shell"/"command-history.jsonl"
ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
BUNDLE=ROOT/"out"/"main"/"index.js"
ER=ROOT/"EVIDENCE"/"VERTEX_SHELL_RUNTIME_PROBE_000080V4B"

def rows(path):
    if not path.exists(): return []
    out=[]
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        try:
            obj=json.loads(line)
            if isinstance(obj,dict): out.append(obj)
        except Exception:
            pass
    return out

def main():
    log_rows=rows(LOG)
    started=[r for r in log_rows if r.get("event")=="vertex_shell_host_bridge_started"]
    attached=[r for r in log_rows if r.get("event")=="host_attached"]
    injected=[r for r in log_rows if r.get("event")=="host_ui_injected"]
    hotkey=[r for r in log_rows if r.get("event")=="global_hotkey_registration"]

    bundle_text=BUNDLE.read_text(encoding="utf-8",errors="replace") if BUNDLE.exists() else ""
    bundle_bridge="vertex_shell_host_bridge_started" in bundle_text

    runtime=bool(started and attached and injected)
    classification=(
      "VERTEX_SHELL_RUNTIME_ACTIVE"
      if runtime else
      "VERTEX_SHELL_BUNDLE_PRESENT_RUNTIME_NOT_YET_ACTIVE"
      if bundle_bridge else
      "VERTEX_SHELL_BUNDLE_NOT_UPDATED"
    )

    d=ER/dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    d.mkdir(parents=True,exist_ok=True)
    rp=d/"vertex_shell_runtime_probe_000080V4B.json"
    rp.write_text(json.dumps({
      "schema":"vertex-session-portal/vertex-shell-runtime-probe/1",
      "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
      "bundle_exists":BUNDLE.exists(),
      "bundle_bridge_marker":bundle_bridge,
      "bridge_log_exists":LOG.exists(),
      "bridge_started":len(started),
      "host_attached":len(attached),
      "host_injected":len(injected),
      "hotkey_registration_records":len(hotkey),
      "history_exists":HISTORY.exists(),
      "runtime_active":runtime,
      "classification":classification,
      "mutation":{"production_source":False,"running_process":False,"runtime_log":False}
    },ensure_ascii=False,indent=2),encoding="utf-8")

    print(f"BUNDLE_EXISTS={str(BUNDLE.exists()).upper()}")
    print(f"BUNDLE_VERTEX_SHELL_MARKER={str(bundle_bridge).upper()}")
    print(f"BRIDGE_LOG_EXISTS={str(LOG.exists()).upper()}")
    print(f"VERTEX_SHELL_HOST_BRIDGE_STARTED={len(started)}")
    print(f"HOST_ATTACHED={len(attached)}")
    print(f"HOST_UI_INJECTED={len(injected)}")
    print(f"HOTKEY_REGISTRATION_RECORDS={len(hotkey)}")
    print(f"COMMAND_HISTORY_EXISTS={str(HISTORY.exists()).upper()}")
    print(f"RUNTIME_ACTIVE={str(runtime).upper()}")
    print(f"CLASSIFICATION={classification}")
    print("PRODUCTION_MUTATION=FALSE")
    print("PROCESS_MUTATION=FALSE")
    print("RUNTIME_LOG_MUTATION=FALSE")
    print(f"EVIDENCE={rp}")
    print("VERTEX_SHELL_RUNTIME_PROBE_000080V4B_RUN=PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
