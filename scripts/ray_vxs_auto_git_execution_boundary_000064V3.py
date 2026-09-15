from pathlib import Path
import json
import os
import sys
import hashlib

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SRC = ROOT / "src" / "main"

def emit(key, value=""):
    s = str(value).encode("ascii", "backslashreplace").decode("ascii")
    print(f"{key}={s}" if value != "" else key)

def emit_json(key, obj):
    print(f"{key}=" + json.dumps(obj, ensure_ascii=True, separators=(",", ":")))

def dump(label, path):
    emit(label + "_PATH", path)
    emit(label + "_EXISTS", "YES" if path.exists() else "NO")
    if not path.exists():
        return
    data = path.read_bytes()
    emit(label + "_BYTES", len(data))
    emit(label + "_SHA256", hashlib.sha256(data).hexdigest())
    text = data.decode("utf-8", "replace")
    emit(label + "_BEGIN")
    for i, line in enumerate(text.splitlines(), 1):
        emit_json(label + "_LINE", {"line": i, "text": line})
    emit(label + "_END")

emit("VERTEX_VXS_AUTO_GIT_EXECUTION_BOUNDARY_RAY_000064V3", "BEGIN")
emit("MODE", "READ_ONLY_ASCII_SAFE")

dump("VXS_COMMAND_REGISTRY", ROOT / "src/main/shell/vxs/vxs-command-registry.ts")
dump("VXS_DEV_CAPABILITIES", ROOT / "src/main/shell/vxs/vxs-dev-capabilities.ts")

needles = (
    "VxsCommandContext",
    "dispatchVxs",
    "executionCommand",
    "createVxsDevelopmentCommands",
    "vxs-command-registry",
)
allowed = {".ts", ".tsx", ".js", ".mjs", ".cjs"}
hits = []
for dirpath, dirnames, filenames in os.walk(SRC):
    dirnames[:] = [d for d in dirnames if d not in {"node_modules", "out", "dist", "build"}]
    for name in filenames:
        p = Path(dirpath) / name
        if p.suffix.lower() not in allowed:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        matched = [n for n in needles if n in text]
        if not matched:
            continue
        rows = []
        for i, line in enumerate(text.splitlines(), 1):
            if any(n in line for n in matched):
                rows.append({"line": i, "text": line})
        hits.append({
            "path": str(p),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "matched": matched,
            "rows": rows[:120],
        })

emit("REFERENCE_FILE_COUNT", len(hits))
for row in hits:
    emit_json("REFERENCE_FILE", row)

emit("PRODUCTION_MUTATION", "NONE")
emit("GIT_ADD_EXECUTED", "NO")
emit("GIT_COMMIT_EXECUTED", "NO")
emit("GIT_PUSH_EXECUTED", "NO")
emit("NEXT", "BUILD_PRODUCTION_COPY_REPLACEMENTS_FOR_AUTO_AUTHORIZED_VXS_GIT_COMMIT_PUSH")
emit("VERTEX_VXS_AUTO_GIT_EXECUTION_BOUNDARY_RAY_000064V3", "PASS")
raise SystemExit(0)
