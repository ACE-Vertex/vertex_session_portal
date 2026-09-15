from pathlib import Path
import os, json, subprocess, datetime

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REQUEST_ID = "5ca2a196-4c33-4d76-b582-e808607014bd"
REMOTE = "https://github.com/ACE-Vertex/vertex_session_portal.git"

print("VERTEX_VERA_VXS_BOOTSTRAP_RETURN_BOUNDARY_RAY_000069V3=BEGIN")
print("MODE=READ_ONLY_ASCII_SAFE")
print("REQUEST_ID=" + REQUEST_ID)
print("PROJECT_ROOT=" + str(ROOT))

def yesno(v):
    return "YES" if v else "NO"

def safe_text(path, limit=2000000):
    try:
        data = path.read_bytes()
        if len(data) > limit:
            data = data[-limit:]
        return data.decode("utf-8", errors="replace")
    except Exception as exc:
        return "__READ_ERROR__:" + repr(exc)

def run(cmd, cwd=None, timeout=20):
    try:
        cp = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "cmd": cmd,
            "exit": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-12000:],
        }
    except Exception as exc:
        return {"cmd": cmd, "error": repr(exc)}

# 1. Source markers currently on disk.
source_checks = {
    "BRIDGE_SOURCE": ROOT / "src/main/shell/vxs/vera-vxs-request-bridge.ts",
    "BOOTSTRAP_SOURCE": ROOT / "src/main/shell/vxs/vxs-git-bootstrap.ts",
    "DEV_SOURCE": ROOT / "src/main/shell/vxs/vxs-dev-capabilities.ts",
    "RENDERER_SOURCE": ROOT / "src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts",
}
for label, path in source_checks.items():
    text = safe_text(path)
    print(label + "_EXISTS=" + yesno(path.exists()))
    if path.exists():
        print(label + "_HAS_000068=" + yesno("VXS_GIT_BOOTSTRAP_000068V3" in text))
        print(label + "_HAS_TYPED_REQUEST=" + yesno("VERTEX_VXS_REQUEST/1" in text or "vertex-vxs-request:" in text or "git.bootstrap" in text))

# 2. Built-output marker visibility. This is observation only.
for dirname in ("out", "dist", "build"):
    base = ROOT / dirname
    print("BUILD_ROOT_" + dirname.upper() + "_EXISTS=" + yesno(base.exists()))
    if not base.exists():
        continue
    found = []
    visited = 0
    try:
        for p in base.rglob("*"):
            if visited >= 4000 or len(found) >= 20:
                break
            if not p.is_file():
                continue
            visited += 1
            if p.suffix.lower() not in {".js",".cjs",".mjs",".html",".map",".json"}:
                continue
            try:
                if p.stat().st_size > 8_000_000:
                    continue
            except Exception:
                continue
            text = safe_text(p, limit=8_000_000)
            if ("vertex-vxs-request:" in text or
                "VXS_GIT_BOOTSTRAP_000068V3" in text or
                "git.bootstrap" in text):
                found.append(str(p.relative_to(ROOT)))
        print("BUILD_ROOT_" + dirname.upper() + "_SCANNED_FILES=" + str(visited))
        print("BUILD_ROOT_" + dirname.upper() + "_MARKER_FILES=" + json.dumps(found, ensure_ascii=True))
    except Exception as exc:
        print("BUILD_ROOT_" + dirname.upper() + "_SCAN_ERROR=" + repr(exc))

# 3. Git durable state.
git_dir = ROOT / ".git"
print("GIT_DIR_EXISTS=" + yesno(git_dir.exists()))
git_commands = [
    ["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"],
    ["git", "-C", str(ROOT), "branch", "--show-current"],
    ["git", "-C", str(ROOT), "remote", "-v"],
    ["git", "-C", str(ROOT), "status", "--porcelain=v1", "-b"],
]
for cmd in git_commands:
    result = run(cmd, timeout=15)
    print("GIT_STATE=" + json.dumps(result, ensure_ascii=True))

# 4. Bound audit discovery under user-data roots.
targets = {
    "vera-vxs-request-audit.jsonl",
    "vxs-git-bootstrap-audit.jsonl",
    "auto-authorities.json",
}
roots = []
for key in ("APPDATA", "LOCALAPPDATA"):
    value = os.environ.get(key)
    if value:
        roots.append(Path(value))

skip_dirs = {
    "Cache","Code Cache","GPUCache","DawnCache","ShaderCache","Crashpad",
    "node_modules","Temp","tmp","logs","Service Worker","Network"
}
matches = []
for base in roots:
    if not base.exists():
        continue
    base_depth = len(base.parts)
    for current, dirs, files in os.walk(base):
        p = Path(current)
        depth = len(p.parts) - base_depth
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        if depth >= 6:
            dirs[:] = []
        for name in files:
            if name in targets:
                matches.append(Path(current) / name)
        if len(matches) >= 80:
            break

unique = []
seen = set()
for p in matches:
    s = str(p)
    if s not in seen:
        seen.add(s)
        unique.append(p)

print("AUDIT_FILE_COUNT=" + str(len(unique)))
for p in unique:
    print("AUDIT_FILE=" + str(p))
    text = safe_text(p, limit=4_000_000)
    if p.name == "auto-authorities.json":
        try:
            doc = json.loads(text)
            rows = doc.get("authorities", []) if isinstance(doc, dict) else []
            now = datetime.datetime.now(datetime.timezone.utc)
            summary = []
            for row in rows if isinstance(rows, list) else []:
                if not isinstance(row, dict):
                    continue
                expires = row.get("expires_utc")
                active = row.get("status") == "ACTIVE"
                try:
                    exp = datetime.datetime.fromisoformat(str(expires).replace("Z","+00:00"))
                    unexpired = exp > now
                except Exception:
                    unexpired = False
                summary.append({
                    "controller_session": row.get("controller_session"),
                    "allowed_sessions": row.get("allowed_sessions"),
                    "status": row.get("status"),
                    "expires_utc": expires,
                    "unexpired": unexpired,
                    "active_and_unexpired": bool(active and unexpired),
                })
            print("AUTO_AUTHORITY_SUMMARY=" + json.dumps(summary, ensure_ascii=True))
        except Exception as exc:
            print("AUTO_AUTHORITY_PARSE_ERROR=" + repr(exc))
    else:
        rows = []
        for line in text.splitlines():
            if REQUEST_ID not in line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                rows.append({"raw": line[-2000:]})
        print("REQUEST_AUDIT_MATCHES=" + json.dumps(rows, ensure_ascii=True))

# 5. Running process observation: establishes whether source-only changes may not yet be loaded.
ps = r"""
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -match 'electron|vertex|session' } |
  Select-Object Name,ProcessId,ExecutablePath,CommandLine |
  ConvertTo-Json -Depth 4 -Compress
"""
proc = run(["pwsh","-NoProfile","-Command",ps], timeout=30)
print("PROCESS_OBSERVATION=" + json.dumps(proc, ensure_ascii=True))

print("PRODUCTION_MUTATION=NONE")
print("GIT_INIT_EXECUTED=NO")
print("GIT_REMOTE_ADD_EXECUTED=NO")
print("GIT_ADD_EXECUTED=NO")
print("GIT_COMMIT_EXECUTED=NO")
print("GIT_PUSH_EXECUTED=NO")
print("NEXT=LOCATE_FIRST_DURABLE_BOUNDARY_BETWEEN_VERA_RENDERER_MAIN_VXS_GIT_AND_RESULT_RETURN")
print("VERTEX_VERA_VXS_BOOTSTRAP_RETURN_BOUNDARY_RAY_000069V3=PASS")
