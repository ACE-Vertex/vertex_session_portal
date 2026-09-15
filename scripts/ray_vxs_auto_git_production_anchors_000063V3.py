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

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
WORKSTATION = Path(r"G:\Vertex_Project\Development\vertex_workstation")

def ascii_text(value):
    return str(value).encode("ascii", "backslashreplace").decode("ascii")

def emit(key, value=""):
    if value == "":
        print(ascii_text(key))
    else:
        print(ascii_text(key) + "=" + ascii_text(value))

def emit_json(key, obj):
    print(ascii_text(key) + "=" + json.dumps(obj, ensure_ascii=True, separators=(",", ":")))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump_file(label, path, max_bytes=2_000_000):
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
    for idx, line in enumerate(text.splitlines(), 1):
        emit_json(label + "_LINE", {"line": idx, "text": line})
    emit(label + "_END")

emit("VERTEX_VXS_AUTO_GIT_PRODUCTION_ANCHOR_RAY_000063V3", "BEGIN")
emit("MODE", "READ_ONLY_ASCII_SAFE")
emit("PURPOSE", "CAPTURE_EXACT_CURRENT_VXS_GIT_AND_AUTO_AUTHORITY_SOURCES_BEFORE_PRODUCTION_MUTATION")

portal_files = [
    ("VXS_REGISTRY", PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"),
    ("VXS_DEV", PORTAL / "src/main/shell/vxs/vxs-dev-capabilities.ts"),
    ("VXS_CAP_DISCOVERY", PORTAL / "src/main/shell/vxs/vxs-capability-discovery.ts"),
    ("VXS_AUTONOMY_FOUNDATION", PORTAL / "src/main/shell/vxs/vxs-autonomy-foundation-capabilities.ts"),
    ("VXS_AUTO_PREP", PORTAL / "src/main/shell/vxs/vxs-autonomous-preparation-capabilities.ts"),
    ("VRA_DISPATCH_SERVICE", PORTAL / "src/main/vra/vra-dispatch-service.ts"),
]

for label, path in portal_files:
    dump_file(label, path)

# Find the renderer-side AUTO Human Gate owner without guessing filename.
renderer_root = PORTAL / "src/renderer"
hits = []
if renderer_root.exists():
    for dirpath, dirnames, filenames in os.walk(renderer_root):
        dirnames[:] = [d for d in dirnames if d not in {"node_modules", "out", "dist", "build"}]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() not in {".ts", ".tsx", ".js", ".mjs", ".cjs"}:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if "grantAutoAuthority(" in text or "AUTO Human Gate ON" in text or "AUTO_AUTHORITY_KEY" in text:
                hits.append(p)

emit("AUTO_RENDERER_OWNER_COUNT", len(hits))
for i, path in enumerate(sorted(set(hits)), 1):
    dump_file(f"AUTO_RENDERER_OWNER_{i}", path)

# Capture exact Workstation Git design/verification assets currently present.
ws_scripts = [
    "verify_vxs_git_cli_adapter_design.py",
    "verify_vxs_git_cli_adapter_implementation.py",
    "verify_vxs_git_command_adapter_preparation.py",
    "verify_vxs_git_human_gate_boundary_design.py",
    "verify_vxs_git_mutation_adapter_design.py",
    "verify_vxs_git_mutation_approval_execution_flow_design.py",
    "verify_vxs_git_mutation_executor_boundary_design.py",
    "verify_vxs_git_mutation_smoke_test.py",
]
for name in ws_scripts:
    dump_file("WS_" + name.replace(".", "_").upper(), WORKSTATION / "scripts" / name)

# Record repository ownership facts. No git mutation.
for label, root in [("PORTAL", PORTAL), ("WORKSTATION", WORKSTATION)]:
    emit(label + "_ROOT", root)
    emit(label + "_DOT_GIT", "YES" if (root / ".git").exists() else "NO")

emit("PRODUCTION_MUTATION", "NONE")
emit("GIT_ADD_EXECUTED", "NO")
emit("GIT_COMMIT_EXECUTED", "NO")
emit("GIT_PUSH_EXECUTED", "NO")
emit("NEXT", "BUILD_CANONICAL_COPY_BASED_AUTO_GIT_MUTATION_CAPABILITY_FROM_CAPTURED_CURRENT_SOURCES")
emit("VERTEX_VXS_AUTO_GIT_PRODUCTION_ANCHOR_RAY_000063V3", "PASS")
raise SystemExit(0)
