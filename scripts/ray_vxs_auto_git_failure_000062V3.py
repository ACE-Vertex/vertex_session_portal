from pathlib import Path
import json
import os
import subprocess
import sys

# Make every emitted line safe even on Windows cp932 consoles/loggers.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

def atext(value):
    if value is None:
        return ""
    text = str(value)
    return text.encode("ascii", "backslashreplace").decode("ascii")

def emit(key, value=""):
    print(atext(key) + ("=" + atext(value) if value != "" else ""))

def emit_json(key, obj):
    # ensure_ascii=True guarantees ASCII-only JSON.
    print(atext(key) + "=" + json.dumps(obj, ensure_ascii=True, separators=(",", ":")))

def run(cmd, cwd=None, timeout=30):
    try:
        cp = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            shell=False,
        )
        out = (cp.stdout or b"").decode("utf-8", "replace")
        err = (cp.stderr or b"").decode("utf-8", "replace")
        return {
            "cmd": cmd,
            "cwd": str(cwd) if cwd else None,
            "exit": cp.returncode,
            "stdout": out[-24000:],
            "stderr": err[-12000:],
        }
    except Exception as exc:
        return {
            "cmd": cmd,
            "cwd": str(cwd) if cwd else None,
            "error": type(exc).__name__ + ":" + str(exc),
        }

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
WORKSTATION = Path(r"G:\Vertex_Project\Development\vertex_workstation")

FAILED_LOGS = [
    (
        "000060_STDOUT",
        Path(r"G:\Vertex_Project\Development\vertex_workstation\runtime\lanes\lane-06\logs\stage-vertex-vxs-auto-git-commit-push-integration-ray-000060V3-1789372178696-534\verify\000-stdout.log"),
    ),
    (
        "000060_STDERR",
        Path(r"G:\Vertex_Project\Development\vertex_workstation\runtime\lanes\lane-06\logs\stage-vertex-vxs-auto-git-commit-push-integration-ray-000060V3-1789372178696-534\verify\000-stderr.log"),
    ),
    (
        "000061_STDOUT",
        Path(r"G:\Vertex_Project\Development\vertex_workstation\runtime\lanes\lane-06\logs\stage-vertex-vxs-auto-git-failure-ray-000061V3-1789372356054-538\verify\000-stdout.log"),
    ),
    (
        "000061_STDERR",
        Path(r"G:\Vertex_Project\Development\vertex_workstation\runtime\lanes\lane-06\logs\stage-vertex-vxs-auto-git-failure-ray-000061V3-1789372356054-538\verify\000-stderr.log"),
    ),
]

emit("VERTEX_VXS_AUTO_GIT_FAILURE_RAY_000062V3", "BEGIN")
emit("MODE", "READ_ONLY_ASCII_SAFE")

# Exact failure evidence first.
for label, path in FAILED_LOGS:
    emit(label + "_PATH", path)
    emit(label + "_EXISTS", "YES" if path.exists() else "NO")
    if path.exists():
        try:
            data = path.read_bytes()
            text = data.decode("utf-8", "replace")
            emit(label + "_BYTES", len(data))
            emit_json(label + "_TAIL", {"text": text[-40000:]})
        except Exception as exc:
            emit(label + "_READ_ERROR", type(exc).__name__ + ":" + str(exc))

# Resolve VXS using both native PATH and PowerShell command discovery.
for cmd in [
    ["where.exe", "vxs"],
    ["where.exe", "vxs.exe"],
    ["where.exe", "vxs.cmd"],
    ["pwsh", "-NoProfile", "-Command", "Get-Command vxs -All -ErrorAction SilentlyContinue | Select-Object CommandType,Name,Source,Definition | ConvertTo-Json -Depth 4"],
    ["pwsh", "-Command", "Get-Command vxs -All -ErrorAction SilentlyContinue | Select-Object CommandType,Name,Source,Definition | ConvertTo-Json -Depth 4"],
]:
    emit_json("VXS_RESOLVE", run(cmd, timeout=20))

# Probe only read-only VXS surfaces. Use PowerShell so functions/aliases can also resolve.
probe_lines = [
    "vxs --version",
    "vxs --help",
    "vxs capabilities --json",
    "vxs policy --json",
    "vxs selftest --json",
    "vxs git help",
    "vxs github help",
]
for root in [PORTAL, WORKSTATION]:
    emit("ROOT", str(root) + "|EXISTS=" + ("YES" if root.exists() else "NO"))
    if not root.exists():
        continue
    for line in probe_lines:
        cmd = ["pwsh", "-Command", line]
        emit_json("VXS_PROBE", run(cmd, cwd=root, timeout=40))

# Bounded source search for live Git/GitHub + AUTO authority anchors.
roots = [
    PORTAL / "src",
    PORTAL / "scripts",
    WORKSTATION / "headless" / "src",
    WORKSTATION / "src-tauri" / "src",
    WORKSTATION / "scripts",
]
needles = [
    "github",
    "git push",
    "git commit",
    "AUTO",
    "HUMAN_APPLY",
    "capabilities",
    "vxs git",
    "vxs github",
]
allowed = {".ts", ".tsx", ".js", ".mjs", ".cjs", ".rs", ".py", ".ps1", ".json", ".md", ".toml"}

for root in roots:
    if not root.exists():
        continue
    emit("SOURCE_ROOT", root)
    emitted = 0
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "target", "out", "dist", "build", "runtime", "EVIDENCE"}]
            for name in filenames:
                p = Path(dirpath) / name
                if p.suffix.lower() not in allowed:
                    continue
                try:
                    if p.stat().st_size > 1_000_000:
                        continue
                    text = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                low = text.lower()
                matched = [n for n in needles if n.lower() in low]
                if not matched:
                    continue
                emit_json("SOURCE_FILE", {"path": str(p), "matched": matched})
                for idx, line in enumerate(text.splitlines(), 1):
                    if any(n.lower() in line.lower() for n in matched):
                        emit_json("SOURCE_LINE", {"path": str(p), "line": idx, "text": line[:800]})
                        emitted += 1
                        if emitted >= 160:
                            break
                if emitted >= 160:
                    break
            if emitted >= 160:
                break
    except Exception as exc:
        emit("SOURCE_SEARCH_ERROR", type(exc).__name__ + ":" + str(exc))
    emit("SOURCE_LINES_EMITTED", emitted)

# Read-only git state only. No add/commit/push.
for root in [PORTAL, WORKSTATION]:
    if not (root / ".git").exists():
        emit("GIT_ROOT", str(root) + "|NO_REPOSITORY")
        continue
    for cmd in [
        ["git", "status", "--short", "--branch"],
        ["git", "branch", "--show-current"],
        ["git", "remote", "-v"],
        ["git", "rev-parse", "HEAD"],
        ["git", "config", "--get", "remote.origin.url"],
    ]:
        emit_json("GIT_STATE", run(cmd, cwd=root, timeout=20))

emit("PRODUCTION_MUTATION", "NONE")
emit("GIT_COMMIT_EXECUTED", "NO")
emit("GIT_PUSH_EXECUTED", "NO")
emit("VERTEX_VXS_AUTO_GIT_FAILURE_RAY_000062V3", "PASS")
raise SystemExit(0)
