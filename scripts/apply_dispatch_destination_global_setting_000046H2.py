from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "src/main/index.ts"
PRELOAD = ROOT / "src/preload/index.ts"
MAINFRAME = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"

BACKUP_ROOT = ROOT / "EVIDENCE" / "VRA_DISPATCH_DESTINATION_000046H2" / time.strftime("%Y%m%d-%H%M%S")
TOUCH = [MAIN, PRELOAD, MAINFRAME]

MAIN_IMPORT = "import './vra/vra-dispatch-destination-bootstrap'"
PRELOAD_IMPORT = "import './vra-dispatch-destination-bridge'"
MAINFRAME_IMPORT = "import '../VraDispatchLane/VraDispatchDestinationControl'"

def safe_emit(text, stream=None):
    stream = stream or sys.stdout
    if text is None:
        return
    enc = getattr(stream, "encoding", None) or "utf-8"
    value = str(text).encode(enc, errors="backslashreplace").decode(enc, errors="replace")
    stream.write(value)
    if value and not value.endswith("\n"):
        stream.write("\n")
    stream.flush()

def read(path):
    if not path.exists():
        raise RuntimeError(f"MISSING_REQUIRED_FILE:{path}")
    return path.read_text(encoding="utf-8")

def write(path, text):
    path.write_bytes(text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))

def prepend_side_effect_import(text, import_line):
    if import_line in text:
        return text
    # A complete side-effect import is valid before any existing import,
    # including before a multiline named import. This avoids H1's broken
    # "find last single-line import" insertion strategy.
    return import_line + "\n" + text

def backup():
    for path in TOUCH:
        rel = path.relative_to(ROOT)
        dest = BACKUP_ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    print(f"TRANSACTION_BACKUP={BACKUP_ROOT}")

def restore():
    for path in TOUCH:
        rel = path.relative_to(ROOT)
        source = BACKUP_ROOT / rel
        if source.exists():
            shutil.copy2(source, path)
    print("TRANSACTION_ROLLBACK=PASS")

def run_build(label):
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    print(f"{label}_RUN={npm} run build")
    result = subprocess.run(
        [npm, "run", "build"],
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
    print(f"{label}_EXIT={result.returncode}")
    return result.returncode

def main():
    print("=== VERTEX SESSION PORTAL / GLOBAL VRA DESTINATION APPLY 000046H2 ===")
    print(f"ROOT={ROOT}")
    print("H1_FAILURE=SIDE_EFFECT_CALL_INSERTED_INSIDE_MULTILINE_IMPORT")
    print("H2_PATCH=PREPEND_COMPLETE_SIDE_EFFECT_IMPORTS")

    # Prove the rolled-back baseline is still healthy before mutation.
    if run_build("BASELINE_BUILD") != 0:
        raise RuntimeError("BASELINE_BUILD_ALREADY_BROKEN")

    backup()
    originals = {path: read(path) for path in TOUCH}

    try:
        write(MAIN, prepend_side_effect_import(originals[MAIN], MAIN_IMPORT))
        write(PRELOAD, prepend_side_effect_import(originals[PRELOAD], PRELOAD_IMPORT))
        write(MAINFRAME, prepend_side_effect_import(originals[MAINFRAME], MAINFRAME_IMPORT))

        if run_build("PATCHED_BUILD") != 0:
            raise RuntimeError("GLOBAL_VRA_DESTINATION_H2_BUILD_FAILED")
    except Exception:
        restore()
        raise

    print("TRANSACTION_ROLLBACK=NOT_REQUIRED")
    print(r"DEFAULT_DESTINATION=G:\Vertex_Project\Development\_incoming")
    print("GLOBAL_DESTINATION_SCOPE=DISPATCH_BAY")
    print("BUTTON_POSITION=AFTER_RELOAD")
    print("PER_CARD_DESTINATION=NO")
    print("PER_VERA_DESTINATION=NO")
    print("DESTINATION_OWNER=ELECTRON_WILL_DOWNLOAD")
    print("PORTABLE_PATH_DEPENDENCE=RETIRED")
    print("VERTEX_SESSION_PORTAL_GLOBAL_VRA_DESTINATION_000046H2_APPLY=PASS")

if __name__ == "__main__":
    main()
