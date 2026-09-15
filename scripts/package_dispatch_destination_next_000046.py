from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scripts/build_current_five_window_portable_000044.py"
TEMP = ROOT / "scripts/_build_dispatch_destination_next_000046.py"

def safe_emit(value, stream=None):
    stream = stream or sys.stdout
    enc = getattr(stream, "encoding", None) or "utf-8"
    out = str(value).encode(enc, errors="backslashreplace").decode(enc, errors="replace")
    stream.write(out)
    if out and not out.endswith("\n"):
        stream.write("\n")

def main():
    print("=== VERTEX SESSION PORTAL / DISPATCH DESTINATION NEXT PACKAGE 000046 ===")
    if not BASE.exists():
        print("NEXT_PACKAGE=SKIP_000044_BUILDER_MISSING")
        return

    source = BASE.read_text(encoding="utf-8")
    old_root = 'ROOT / "release" / "current" / "VertexSessionPortal-current-win-x64"'
    new_root = 'ROOT / "release" / "next" / "VertexSessionPortal-next-win-x64"'
    old_smoke = 'ROOT / "release" / "_smoke" / "session-portal-current"'
    new_smoke = 'ROOT / "release" / "_smoke" / "session-portal-next-000046"'

    if old_root not in source:
        raise RuntimeError("000044_RELEASE_ROOT_ANCHOR_MISSING")

    source = source.replace(old_root, new_root, 1)
    if old_smoke in source:
        source = source.replace(old_smoke, new_smoke, 1)

    TEMP.write_text(source, encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, str(TEMP)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
        safe_emit(result.stdout, sys.stdout)
        if result.stderr:
            safe_emit(result.stderr, sys.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"NEXT_PACKAGE_FAILED:{result.returncode}")
    finally:
        TEMP.unlink(missing_ok=True)

    exe = ROOT / "release/next/VertexSessionPortal-next-win-x64/Vertex Session Portal.exe"
    if not exe.exists():
        raise RuntimeError("NEXT_PACKAGE_EXE_MISSING")
    print(f"NEXT_EXE={exe}")
    print("NEXT_PACKAGE=PASS")

if __name__ == "__main__":
    main()
