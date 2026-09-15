from pathlib import Path
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
MAIN = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
COMP = ROOT / "src/renderer/src/components/FirmwareChangeGate/FirmwareChangeGate.ts"
CSS = ROOT / "src/renderer/src/components/FirmwareChangeGate/FirmwareChangeGate.css"

IMPORT_ANCHOR = "import '../VraDispatchLane/VraDispatchLane'"
IMPORT_LINE = "import '../FirmwareChangeGate/FirmwareChangeGate'"
MOUNT_ANCHOR = "<vertex-vra-dispatch-lane></vertex-vra-dispatch-lane>"
MOUNT_LINE = "<vertex-firmware-change-gate></vertex-firmware-change-gate>"


def emit(s=""):
    print(str(s).encode("ascii", "backslashreplace").decode("ascii"))


def fail(message: str, code: int) -> None:
    emit("FIRMWARE_CHANGE_GATE_FINAL=FAIL " + message)
    raise SystemExit(code)


def run(command):
    cp = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=420,
    )
    emit("RUN=" + " ".join(command))
    emit("EXIT=" + str(cp.returncode))
    if cp.stdout:
        emit("STDOUT_TAIL=" + cp.stdout[-12000:].replace("\r", " ").replace("\n", "\\n"))
    if cp.stderr:
        emit("STDERR_TAIL=" + cp.stderr[-12000:].replace("\r", " ").replace("\n", "\\n"))
    return cp.returncode


for path in (MAIN, COMP, CSS):
    if not path.exists():
        fail("missing required file: " + str(path), 2)

component_text = COMP.read_text(encoding="utf-8", errors="replace")
required_markers = (
    "000151V3R2: exactOptionalPropertyTypes-safe approval packet model.",
    "customElements.define('vertex-firmware-change-gate'",
    "vertex:firmware-change-decision",
    "vertex:firmware-change-inspect",
    "ARM RED APPROVAL",
    "FINAL COMMIT",
)
for marker in required_markers:
    if marker not in component_text:
        fail("component marker missing: " + marker, 3)

if "ipcRenderer" in component_text or ".invoke(" in component_text:
    fail("GUI authority boundary violated", 4)

original = MAIN.read_text(encoding="utf-8")
next_text = original

if IMPORT_LINE not in next_text and IMPORT_ANCHOR not in next_text:
    fail("MainFrame import anchor missing", 5)
if MOUNT_LINE not in next_text and MOUNT_ANCHOR not in next_text:
    fail("MainFrame mount anchor missing", 6)

# Baseline verification proven by the preceding TEST diagnostic; repeat fail-closed.
if run(["npm.cmd", "run", "typecheck"]) != 0:
    fail("baseline typecheck failed; MainFrame untouched", 7)
if run(["npm.cmd", "run", "build"]) != 0:
    fail("baseline build failed; MainFrame untouched", 8)

if IMPORT_LINE not in next_text:
    next_text = next_text.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + "\n" + IMPORT_LINE, 1)
if MOUNT_LINE not in next_text:
    next_text = next_text.replace(MOUNT_ANCHOR, MOUNT_ANCHOR + "\n              " + MOUNT_LINE, 1)

changed = next_text != original
if changed:
    MAIN.write_text(next_text, encoding="utf-8", newline="\n")

try:
    if run(["npm.cmd", "run", "typecheck"]) != 0:
        raise RuntimeError("post-mount typecheck failed")
    if run(["npm.cmd", "run", "build"]) != 0:
        raise RuntimeError("post-mount build failed")

    final_text = MAIN.read_text(encoding="utf-8", errors="replace")
    checks = {
        "IMPORT": IMPORT_LINE in final_text,
        "MOUNT": MOUNT_LINE in final_text,
        "CUSTOM_ELEMENT": "customElements.define('vertex-firmware-change-gate'" in component_text,
        "NO_DIRECT_IPC": "ipcRenderer" not in component_text and ".invoke(" not in component_text,
        "RED_TWO_STEP": "ARM RED APPROVAL" in component_text and "FINAL COMMIT" in component_text,
        "DECISION_EVENT": "vertex:firmware-change-decision" in component_text,
        "DEEP_RAY_EVENT": "vertex:firmware-change-inspect" in component_text,
    }
    for name, ok in checks.items():
        emit(name + "=" + ("PASS" if ok else "FAIL"))
    if not all(checks.values()):
        raise RuntimeError("final structural assertion failed")

except Exception as exc:
    if changed:
        MAIN.write_text(original, encoding="utf-8", newline="\n")
        emit("MAINFRAME_RESTORE=PASS")
    fail("post-mount verification failed: " + str(exc), 9)

emit("BASELINE_TYPECHECK=PASS")
emit("BASELINE_BUILD=PASS")
emit("POST_MOUNT_TYPECHECK=PASS")
emit("POST_MOUNT_BUILD=PASS")
emit("MAINFRAME_PATCHED=" + ("YES" if changed else "ALREADY_PRESENT"))
emit("GUI_AUTHORITY_BOUNDARY=PASS")
emit("FIRMWARE_CHANGE_GATE_FINAL=PASS")
raise SystemExit(0)
