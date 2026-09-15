from pathlib import Path
import hashlib
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")

def emit(key, value=""):
    text = str(value).encode("ascii", "backslashreplace").decode("ascii")
    print(f"{key}={text}" if value != "" else key)

def emit_json(key, value):
    print(f"{key}=" + json.dumps(value, ensure_ascii=True, separators=(",", ":")))

def dump(label, path, max_bytes=2_000_000):
    emit(label + "_PATH", path)
    emit(label + "_EXISTS", "YES" if path.exists() else "NO")
    if not path.exists():
        return
    data = path.read_bytes()
    emit(label + "_BYTES", len(data))
    emit(label + "_SHA256", hashlib.sha256(data).hexdigest())
    if len(data) > max_bytes:
        emit(label + "_SKIPPED", "TOO_LARGE")
        return
    text = data.decode("utf-8", "replace")
    emit(label + "_BEGIN")
    for i, line in enumerate(text.splitlines(), 1):
        emit_json(label + "_LINE", {"line": i, "text": line})
    emit(label + "_END")

emit("VERTEX_VERA_TO_VXS_INGRESS_RAY_000066V3", "BEGIN")
emit("MODE", "READ_ONLY_ASCII_SAFE")
emit("PURPOSE", "PROVE_OR_LOCATE_EXISTING_VERA_TO_INTERNAL_VXS_COMMAND_INGRESS")

# Exact current shell/VXS execution owner.
dump("VERTEX_SHELL_SERVICE", ROOT / "src/main/shell/vertex-shell-service.ts")
dump("VXS_COMMAND_REGISTRY", ROOT / "src/main/shell/vxs/vxs-command-registry.ts")
dump("VXS_DEV_CAPABILITIES", ROOT / "src/main/shell/vxs/vxs-dev-capabilities.ts")
dump("VXS_GIT_AUTO_PUBLISH", ROOT / "src/main/shell/vxs/vxs-git-auto-publish.ts")

# Locate exact IPC/preload/renderer/session entry points that can submit shell/VXS commands.
needles = [
    "executeVxsCommand",
    "vertex-shell-service",
    "executionCommand",
    "writeShell",
    "shell.write",
    "shell:write",
    "shell:command",
    "runCommand",
    "VeraBrowserSession",
    "webContents",
    "vxs git",
]
allowed = {".ts", ".tsx", ".js", ".mjs", ".cjs"}

for base in [
    ROOT / "src/main",
    ROOT / "src/preload",
    ROOT / "src/renderer",
    ROOT / "src/shared",
]:
    if not base.exists():
        continue
    emit("SEARCH_ROOT", base)
    found = 0
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in {"node_modules", "out", "dist", "build"}]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() not in allowed:
                continue
            try:
                if path.stat().st_size > 1_500_000:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            low = text.lower()
            matched = [needle for needle in needles if needle.lower() in low]
            if not matched:
                continue
            emit_json("INGRESS_FILE", {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "matched": matched
            })
            for i, line in enumerate(text.splitlines(), 1):
                if any(needle.lower() in line.lower() for needle in matched):
                    emit_json("INGRESS_LINE", {
                        "path": str(path),
                        "line": i,
                        "text": line[:1000]
                    })
                    found += 1
                    if found >= 250:
                        break
            if found >= 250:
                break
        if found >= 250:
            break
    emit("INGRESS_LINES", found)

emit("PRODUCTION_MUTATION", "NONE")
emit("GIT_ADD_EXECUTED", "NO")
emit("GIT_COMMIT_EXECUTED", "NO")
emit("GIT_PUSH_EXECUTED", "NO")
emit("NEXT", "USE_EXISTING_INGRESS_IF_PRESENT_OTHERWISE_ADD_NARROW_TYPED_VERA_TO_VXS_BRIDGE")
emit("VERTEX_VERA_TO_VXS_INGRESS_RAY_000066V3", "PASS")
raise SystemExit(0)
