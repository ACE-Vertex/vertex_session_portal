from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

REQUIRED = [
    "package.json",
    "electron.vite.config.ts",
    "src/main/index.ts",
    "src/main/storage/workstation-db.ts",
    "src/preload/index.ts",
    "src/renderer/index.html",
    "src/renderer/src/components/MainFrame/MainFrame.ts",
    "src/renderer/src/components/VeraSession/VeraSession.ts",
    "src/renderer/src/components/SearchVera/SearchVera.ts",
    "src/renderer/src/components/Explorer/Explorer.ts",
    "src/renderer/src/control/control-channel.ts",
    "docs/ARCHITECTURE.md",
    "docs/BUILD_RULES.md",
]

def run(cmd: list[str], marker: str) -> None:
    print("RUN=" + " ".join(cmd))
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="backslashreplace",
        shell=False,
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n")
    print(f"{marker}_EXIT={proc.returncode}")
    if proc.returncode != 0:
        raise RuntimeError(f"{marker}_FAILED")

def main() -> int:
    print("VERTEX SESSION PORTAL / BOOTSTRAP VERIFY 000012")
    print(f"ROOT={ROOT}")

    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        print("MISSING=" + ",".join(missing))
        print("VERTEX_SESSION_PORTAL_BOOTSTRAP_000012=FAIL")
        return 2

    pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert pkg["name"] == "vertex-session-portal"
    assert pkg["devDependencies"]["electron"] == "44.2.0"
    assert pkg["dependencies"]["better-sqlite3"] == "13.0.3"

    print("PROJECT_STRUCTURE=PASS")
    print("SQLITE_LOCAL_LAYER=DECLARED")
    print("DEFAULT_MAIN_VERA=3")
    print("DEFAULT_SEARCH_VERA=1")
    print("MAX_ACTIVE_VERA=5")
    print("SESSION_MIN_WIDTH=600")
    print("SESSION_PRIORITY_TARGET=1200")
    print("MSSQL_SESSION_PORTAL_DB_REQUIRED=NO")

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        print("NODE_TOOLCHAIN=NOT_FOUND")
        print("VERTEX_SESSION_PORTAL_BOOTSTRAP_000012=FAIL")
        return 3

    print(f"NPM={npm}")
    try:
        run([npm, "install"], "NPM_INSTALL")
        run([npm, "run", "typecheck"], "TYPECHECK")
        run([npm, "run", "build"], "BUILD")
    except Exception as exc:
        print(f"ERROR={exc}")
        print("VERTEX_SESSION_PORTAL_BOOTSTRAP_000012=FAIL")
        return 4

    print("VERTEX_SESSION_PORTAL_BOOTSTRAP_000012=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
