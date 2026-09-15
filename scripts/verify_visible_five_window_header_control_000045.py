from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "src/renderer/src/components/VeraWindowScaler/VeraWindowScaler.css"
TS = ROOT / "src/renderer/src/components/VeraWindowScaler/VeraWindowScaler.ts"
MAIN = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
BUILD_CURRENT = ROOT / "scripts/build_current_five_window_portable_000044.py"
CURRENT_EXE = ROOT / "release/current/VertexSessionPortal-current-win-x64/Vertex Session Portal.exe"

def safe_emit(text: str, stream=None) -> None:
    stream = stream or sys.stdout
    if text is None:
        return
    enc = getattr(stream, "encoding", None) or "utf-8"
    safe = str(text).encode(enc, errors="backslashreplace").decode(enc, errors="replace")
    stream.write(safe)
    if safe and not safe.endswith("\n"):
        stream.write("\n")
    stream.flush()

def check(name: str, ok: bool, failures: list[str]) -> None:
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)

def run(cmd):
    result = subprocess.run(
        [str(x) for x in cmd],
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
    return result.returncode

def main() -> None:
    print("=== VERTEX SESSION PORTAL / VISIBLE FIVE-WINDOW HEADER CONTROL VERIFY 000045 ===")
    print(f"ROOT={ROOT}")
    failures = []

    css = CSS.read_text(encoding="utf-8") if CSS.exists() else ""
    ts = TS.read_text(encoding="utf-8") if TS.exists() else ""
    main = MAIN.read_text(encoding="utf-8") if MAIN.exists() else ""

    check("SCALER_CSS_PRESENT", bool(css), failures)
    check("SCALER_TS_PRESENT", bool(ts), failures)
    check("HEADER_MOUNT_PRESENT",
          "<vertex-vera-window-scaler></vertex-vera-window-scaler>" in main,
          failures)
    check("VISIBLE_FIXED_HOST", "position: fixed;" in css, failures)
    check("VISIBLE_Z_INDEX", "z-index: 5000;" in css, failures)
    check("VISIBLE_HEADER_LEFT_ANCHOR", "left: 220px;" in css, failures)
    check("POINTER_EVENTS_ENABLED", "pointer-events: auto;" in css, failures)
    check("BUTTONS_3_4_5", "${[3, 4, 5].map" in ts, failures)
    check("MAX_WINDOW_COUNT_FIVE", "const MAX_COUNT = 5" in ts, failures)
    check("DEFAULT_WINDOW_COUNT_THREE", "const MIN_COUNT = 3" in ts, failures)

    if failures:
        print("STATIC_FAILURES=" + ",".join(failures))
        raise SystemExit(2)

    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    print(f"RUN={npm} run build")
    code = run([npm, "run", "build"])
    check("SOURCE_BUILD", code == 0, failures)

    if failures:
        raise SystemExit(3)

    if BUILD_CURRENT.exists():
        print(f"RUN={sys.executable} {BUILD_CURRENT.relative_to(ROOT)}")
        code = run([sys.executable, str(BUILD_CURRENT)])
        check("CURRENT_PORTABLE_REBUILD", code == 0, failures)
        check("CURRENT_PORTABLE_EXE_PRESENT", CURRENT_EXE.exists(), failures)
    else:
        failures.append("CURRENT_PORTABLE_BUILDER_NOT_FOUND")

    if failures:
        raise SystemExit(4)

    print(f"CANONICAL_CURRENT_EXE={CURRENT_EXE}")
    print("VERTEX_SESSION_PORTAL_VISIBLE_FIVE_WINDOW_HEADER_CONTROL_000045=PASS")

if __name__ == "__main__":
    main()
