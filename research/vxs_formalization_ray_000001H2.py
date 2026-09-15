from __future__ import print_function

import os
import pathlib
import sys
import traceback

ROOT = pathlib.Path(r"G:\Vertex_Project\Development\vertex_session_portal")

TERMS = (
    "VERTEX SHELL",
    "Vertex Shell",
    "vertex shell",
    "vertex-shell",
    "VertexShell",
    "vertexShell",
    "VSH",
    "vsh",
)

TEXT_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".vue", ".rs",
    ".html", ".css", ".scss", ".json", ".toml",
    ".md", ".txt", ".yml", ".yaml"
}

SKIP_DIRS = {
    "node_modules", "dist", "build", "target", ".git",
    ".cache", "runtime"
}

def safe(value):
    try:
        text = str(value)
    except Exception:
        text = repr(value)
    return text.encode("ascii", "backslashreplace").decode("ascii")

def emit(key, value):
    print(safe(key) + "=" + safe(value))

def inspect_file(path, rows):
    if not path.is_file():
        return
    if path.suffix.lower() not in TEXT_EXTS:
        return

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        rows.append(("READ_ERROR", str(path), 0, type(exc).__name__, str(exc)))
        return

    try:
        rel = path.relative_to(ROOT)
    except Exception:
        rel = path

    for line_no, line in enumerate(text.splitlines(), 1):
        hits = [term for term in TERMS if term in line]
        if hits:
            rows.append(("MATCH", str(rel).replace("\\", "/"), line_no, ",".join(hits), line.strip()[:500]))

try:
    emit("VXS_RAY_SCHEMA", "vertex-session-portal/vxs-formalization-ray-1")
    emit("PYTHON_VERSION", sys.version.replace("\n", " "))
    emit("STDOUT_ENCODING", getattr(sys.stdout, "encoding", None))
    emit("ROOT", ROOT)
    emit("MODE", "READ_ONLY_SOURCE_AUDIT")
    emit("PRODUCTION_MUTATION", "NONE")

    if not ROOT.is_dir():
        emit("VXS_RAY", "FAIL")
        emit("REASON", "TARGET_ROOT_MISSING")
        raise SystemExit(41)

    rows = []
    files_scanned = 0

    search_root = ROOT / "src"
    if search_root.is_dir():
        for base, dirs, files in os.walk(str(search_root)):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            base_path = pathlib.Path(base)
            for name in files:
                path = base_path / name
                if path.suffix.lower() in TEXT_EXTS:
                    files_scanned += 1
                    inspect_file(path, rows)

    for root_name in ("package.json", "electron.vite.config.ts"):
        path = ROOT / root_name
        if path.is_file():
            files_scanned += 1
            inspect_file(path, rows)

    emit("FILES_SCANNED", files_scanned)
    emit("ROW_COUNT", len(rows))

    match_count = 0
    read_error_count = 0

    for kind, rel, line_no, hits, text in rows:
        if kind == "MATCH":
            match_count += 1
            print(
                "MATCH|FILE=" + safe(rel)
                + "|LINE=" + safe(line_no)
                + "|TERMS=" + safe(hits)
                + "|TEXT=" + safe(text)
            )
        else:
            read_error_count += 1
            print(
                "READ_ERROR|FILE=" + safe(rel)
                + "|TYPE=" + safe(hits)
                + "|MESSAGE=" + safe(text)
            )

    emit("MATCH_COUNT", match_count)
    emit("READ_ERROR_COUNT", read_error_count)
    emit("RAY_COMPLETE", "YES")
    raise SystemExit(0)

except SystemExit:
    raise
except Exception as exc:
    emit("VXS_RAY", "FAIL")
    emit("ERROR_TYPE", type(exc).__name__)
    emit("ERROR_MESSAGE", exc)
    tb = traceback.format_exc()
    emit("TRACEBACK", tb)
    raise SystemExit(42)
