from pathlib import Path
import re
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
MAINFRAME = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
MAIN_IPC = ROOT / "src/main/ipc/register-vra-dispatch-ipc.ts"
GATE = ROOT / "src/renderer/src/components/FirmwareChangeGate/FirmwareChangeGate.ts"
BRIDGE = ROOT / "src/renderer/src/components/FirmwareChangeGate/FirmwareDecisionBridge.ts"
REGISTRAR = ROOT / "src/main/firmware/FirmwareRegistrar.ts"
REGISTRAR_IPC = ROOT / "src/main/ipc/register-firmware-registrar-ipc.ts"
PRELOAD_ROOT = ROOT / "src/preload"
SRC = ROOT / "src"

MAINFRAME_IMPORT = "import '../FirmwareChangeGate/FirmwareDecisionBridge'"
REGISTRAR_IMPORT = "import { registerFirmwareRegistrarIpc } from './register-firmware-registrar-ipc'"
REGISTRAR_CALL = "registerFirmwareRegistrarIpc()"
PRELOAD_METHOD_NAME = "submitFirmwareChangeDecision"
PRELOAD_METHOD_IMPL = """submitFirmwareChangeDecision: (detail: unknown) =>
    ipcRenderer.invoke('firmware:submit-change-decision', detail),"""
PRELOAD_METHOD_TYPE = "submitFirmwareChangeDecision: (detail: unknown) => Promise<unknown>"

def emit(s=""):
    print(str(s).encode("ascii", "backslashreplace").decode("ascii"))

def fail(message, code):
    emit("FIRMWARE_REGISTRAR_CONTROL_PLANE=FAIL " + message)
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
        emit("STDOUT_TAIL=" + cp.stdout[-16000:].replace("\r", " ").replace("\n", "\\n"))
    if cp.stderr:
        emit("STDERR_TAIL=" + cp.stderr[-16000:].replace("\r", " ").replace("\n", "\\n"))
    return cp.returncode

for required in (MAINFRAME, MAIN_IPC, GATE, BRIDGE, REGISTRAR, REGISTRAR_IPC):
    if not required.exists():
        fail("missing required file: " + str(required), 2)

preload_candidates = []
for path in PRELOAD_ROOT.rglob("*.ts"):
    text = path.read_text(encoding="utf-8", errors="replace")
    if "exposeInMainWorld" in text and "vertexPortal" in text:
        preload_candidates.append((path, text))

if len(preload_candidates) != 1:
    fail("expected exactly one vertexPortal preload exposure, found " + str(len(preload_candidates)), 3)

PRELOAD, preload_original = preload_candidates[0]
emit("PRELOAD=" + PRELOAD.relative_to(ROOT).as_posix())

variable = re.search(
    r"contextBridge\.exposeInMainWorld\(\s*['\"]vertexPortal['\"]\s*,\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\)",
    preload_original,
    re.S,
)
if not variable:
    fail("named vertexPortal API object not found", 4)

api_name = variable.group(1)
obj_match = re.search(
    rf"(?:const|let|var)\s+{re.escape(api_name)}(?P<annotation>\s*:[^=]+)?\s*=\s*\{{",
    preload_original,
    re.S,
)
if not obj_match:
    fail("vertexPortal API object definition not found", 5)

annotation = (obj_match.group("annotation") or "").strip()
if not annotation:
    fail("vertexPortal API has no explicit type annotation", 6)

type_names = [
    name for name in re.findall(r"\b[A-Z][A-Za-z0-9_$]*\b", annotation)
    if name not in {"Readonly", "Partial", "Record", "Promise", "Array"}
]
if not type_names:
    fail("vertexPortal API type name unresolved", 7)

type_declarations = []
for path in SRC.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in {".ts", ".tsx", ".d.ts"}:
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    for type_name in type_names:
        patterns = [
            re.compile(rf"(?:export\s+)?interface\s+{re.escape(type_name)}(?:\s+extends\s+[^{{]+)?\s*\{{", re.S),
            re.compile(rf"(?:export\s+)?type\s+{re.escape(type_name)}(?:\s*<[^>]+>)?\s*=\s*\{{", re.S),
            re.compile(rf"(?:export\s+)?type\s+{re.escape(type_name)}(?:\s*<[^>]+>)?\s*=\s*Readonly\s*<\s*\{{", re.S),
        ]
        for pattern in patterns:
            m = pattern.search(text)
            if m:
                type_declarations.append((type_name, path, text, m))
                break

unique = {}
for item in type_declarations:
    unique[(item[0], str(item[1]))] = item
type_declarations = list(unique.values())

if len(type_declarations) != 1:
    fail("expected exactly one vertexPortal API type declaration, found " + str(len(type_declarations)), 8)

type_name, API_TYPE_FILE, api_type_original, api_type_match = type_declarations[0]
emit("API_TYPE=" + type_name)
emit("API_TYPE_FILE=" + API_TYPE_FILE.relative_to(ROOT).as_posix())

existing_originals = {
    MAINFRAME: MAINFRAME.read_text(encoding="utf-8"),
    MAIN_IPC: MAIN_IPC.read_text(encoding="utf-8"),
    PRELOAD: preload_original,
    API_TYPE_FILE: api_type_original,
}

def restore_existing():
    for path, text in existing_originals.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    emit("PATCHED_EXISTING_FILES_RESTORE=PASS")

if run(["npm.cmd", "run", "typecheck"]) != 0:
    fail("baseline typecheck failed; no integration applied", 9)
if run(["npm.cmd", "run", "build"]) != 0:
    fail("baseline build failed; no integration applied", 10)

try:
    mainframe = existing_originals[MAINFRAME]
    if MAINFRAME_IMPORT not in mainframe:
        anchor = "import '../FirmwareChangeGate/FirmwareChangeGate'"
        if anchor not in mainframe:
            fail("FirmwareChangeGate import anchor missing from MainFrame", 11)
        mainframe = mainframe.replace(anchor, anchor + "\n" + MAINFRAME_IMPORT, 1)
        MAINFRAME.write_text(mainframe, encoding="utf-8", newline="\n")

    main_ipc = existing_originals[MAIN_IPC]
    if REGISTRAR_IMPORT not in main_ipc:
        import_lines = list(re.finditer(r"^import .+$", main_ipc, re.M))
        if not import_lines:
            fail("Main IPC import block not found", 12)
        insert_at = import_lines[-1].end()
        main_ipc = main_ipc[:insert_at] + "\n" + REGISTRAR_IMPORT + main_ipc[insert_at:]

    if REGISTRAR_CALL not in main_ipc:
        handler = re.search(r"(?m)^(?P<indent>\s*)ipcMain\.handle\(", main_ipc)
        if not handler:
            fail("ipcMain.handle anchor not found", 13)
        insert_at = handler.start()
        indent = handler.group("indent")
        main_ipc = main_ipc[:insert_at] + indent + REGISTRAR_CALL + "\n\n" + main_ipc[insert_at:]

    MAIN_IPC.write_text(main_ipc, encoding="utf-8", newline="\n")

    api_type_text = existing_originals[API_TYPE_FILE]
    if PRELOAD_METHOD_NAME not in api_type_text:
        insert_at = api_type_match.end()
        api_type_text = (
            api_type_text[:insert_at]
            + "\n  " + PRELOAD_METHOD_TYPE + "\n"
            + api_type_text[insert_at:]
        )
        API_TYPE_FILE.write_text(api_type_text, encoding="utf-8", newline="\n")

    preload = existing_originals[PRELOAD]
    if PRELOAD_METHOD_NAME not in preload:
        current_obj = re.search(
            rf"(?:const|let|var)\s+{re.escape(api_name)}(?P<annotation>\s*:[^=]+)?\s*=\s*\{{",
            preload,
            re.S,
        )
        if not current_obj:
            fail("vertexPortal API object definition disappeared", 14)
        insert_at = current_obj.end()
        preload = preload[:insert_at] + "\n  " + PRELOAD_METHOD_IMPL + preload[insert_at:]
        PRELOAD.write_text(preload, encoding="utf-8", newline="\n")

    gate_text = GATE.read_text(encoding="utf-8", errors="replace")
    registrar_text = REGISTRAR.read_text(encoding="utf-8", errors="replace")
    bridge_text = BRIDGE.read_text(encoding="utf-8", errors="replace")
    main_ipc_text = MAIN_IPC.read_text(encoding="utf-8", errors="replace")
    preload_text = PRELOAD.read_text(encoding="utf-8", errors="replace")
    api_type_text = API_TYPE_FILE.read_text(encoding="utf-8", errors="replace")
    mainframe_text = MAINFRAME.read_text(encoding="utf-8", errors="replace")

    checks = {
        "GATE_DECISION_EVENT": "vertex:firmware-change-decision" in gate_text,
        "GATE_VALIDATION_SNAPSHOT": "validation: request.validation" in gate_text,
        "GATE_RED_CONFIRM": "redConfirmed:" in gate_text,
        "GATE_NO_DIRECT_IPC": "ipcRenderer" not in gate_text and ".invoke(" not in gate_text,
        "BRIDGE_LISTENER": "vertex:firmware-change-decision" in bridge_text,
        "PRELOAD_API_TYPE": PRELOAD_METHOD_NAME in api_type_text,
        "PRELOAD_TRUSTED_BRIDGE": PRELOAD_METHOD_NAME in preload_text,
        "MAIN_IPC_CHANNEL": "firmware:submit-change-decision" in REGISTRAR_IPC.read_text(encoding="utf-8"),
        "MAIN_REGISTRATION": REGISTRAR_CALL in main_ipc_text,
        "SIGNED_APPROVAL": "HMAC-SHA256" in registrar_text and "signed-approval-record-1" in registrar_text,
        "VALIDATOR_ENFORCED": "validator evidence is not all PASS" in registrar_text,
        "RED_TWO_STEP_ENFORCED": "RED firmware approval requires the second Human confirmation" in registrar_text,
        "ATOMIC_REGISTRY": "renameSync(temp, path)" in registrar_text,
        "VERSION_CONFLICT_GUARD": "Firmware Registry version conflict" in registrar_text,
        "HASH_CHAINED_JOURNAL": "previousHash" in registrar_text and "entryHash" in registrar_text,
        "MAINFRAME_BRIDGE_IMPORT": MAINFRAME_IMPORT in mainframe_text,
    }
    for name, ok in checks.items():
        emit(name + "=" + ("PASS" if ok else "FAIL"))
    if not all(checks.values()):
        raise RuntimeError("structural control-plane assertion failed")

    if run(["npm.cmd", "run", "typecheck"]) != 0:
        raise RuntimeError("post-integration typecheck failed")
    if run(["npm.cmd", "run", "build"]) != 0:
        raise RuntimeError("post-integration build failed")

except SystemExit:
    restore_existing()
    raise
except Exception as exc:
    restore_existing()
    fail("verification failed: " + str(exc), 20)

emit("BASELINE_TYPECHECK=PASS")
emit("BASELINE_BUILD=PASS")
emit("PRELOAD_API_TYPE_FIX=PASS")
emit("POST_INTEGRATION_TYPECHECK=PASS")
emit("POST_INTEGRATION_BUILD=PASS")
emit("SIGNED_APPROVAL_RECORD=INSTALLED")
emit("FIRMWARE_REGISTRAR=INSTALLED")
emit("REGISTRY_COMMIT=ATOMIC")
emit("REGISTRY_JOURNAL=HASH_CHAINED")
emit("FIRMWARE_REGISTRAR_CONTROL_PLANE=PASS")
raise SystemExit(0)
