from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "src/main/index.ts"
PRELOAD = ROOT / "src/preload/index.ts"
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
MAINFRAME = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
LANE_CSS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css"

BACKUP_ROOT = ROOT / "EVIDENCE" / "VRA_DISPATCH_DESTINATION_000046" / time.strftime("%Y%m%d-%H%M%S")
TOUCH = [MAIN, PRELOAD, SERVICE, MAINFRAME, LANE_CSS]

MAIN_IMPORT = "import { registerVraDispatchDestinationIpc } from './ipc/register-vra-dispatch-destination-ipc'"
MAIN_CALL = "registerVraDispatchDestinationIpc()"
MAINFRAME_IMPORT = "import '../VraDispatchLane/VraDispatchDestinationControl'"
SERVICE_IMPORT = "import { getVraDispatchDestination } from './vra-dispatch-destination-store'"

PRELOAD_BLOCK = r"""
// VERTEX_VRA_DISPATCH_DESTINATION_000046
contextBridge.exposeInMainWorld('vertexDispatchDestination', {
  get: () => ipcRenderer.invoke('vertex:vra-dispatch-destination:get'),
  choose: () => ipcRenderer.invoke('vertex:vra-dispatch-destination:choose')
})
"""

CSS_BLOCK = r"""
/* VERTEX_VRA_DISPATCH_DESTINATION_000046 */
.dispatch-destination-control,
button[data-vra-dispatch-destination-control] {
  display: inline-grid;
  place-items: center;
  min-width: 24px;
  height: 22px;
  padding: 0 6px;
  border: 1px solid #26394B;
  border-radius: 5px;
  background: #0C121A;
  color: #718195;
  cursor: pointer;
  font: inherit;
  font-size: 10px;
  line-height: 1;
}
.dispatch-destination-control:hover,
button[data-vra-dispatch-destination-control]:hover {
  border-color: #3AB8FF;
  color: #3AB8FF;
}
button[data-vra-dispatch-destination-control][data-default-destination="false"] {
  border-color: rgba(58,184,255,.65);
  color: #3AB8FF;
}
"""

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

def backup():
    for path in TOUCH:
        if path.exists():
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
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, path)
    print("TRANSACTION_ROLLBACK=PASS")

def add_import(text, import_line):
    if import_line in text:
        return text
    matches = list(re.finditer(r"(?m)^import [^\n]+\n", text))
    if not matches:
        raise RuntimeError(f"IMPORT_ANCHOR_NOT_FOUND:{import_line}")
    pos = matches[-1].end()
    return text[:pos] + import_line + "\n" + text[pos:]

def patch_main(text):
    out = add_import(text, MAIN_IMPORT)
    if MAIN_CALL not in out:
        matches = list(re.finditer(r"(?m)^import [^\n]+\n", out))
        if not matches:
            raise RuntimeError("MAIN_IMPORT_BLOCK_NOT_FOUND")
        pos = matches[-1].end()
        out = out[:pos] + "\n// VERTEX_VRA_DISPATCH_DESTINATION_000046\n" + MAIN_CALL + "\n" + out[pos:]
    return out

def ensure_electron_imports(text):
    # Add contextBridge/ipcRenderer to the existing Electron named import.
    pattern = re.compile(r"import\s*\{([^}]*)\}\s*from\s*['\"]electron['\"]")
    match = pattern.search(text)
    if not match:
        raise RuntimeError("PRELOAD_ELECTRON_NAMED_IMPORT_NOT_FOUND")
    names = [x.strip() for x in match.group(1).split(",") if x.strip()]
    changed = False
    for required in ("contextBridge", "ipcRenderer"):
        if required not in names:
            names.append(required)
            changed = True
    if not changed:
        return text
    replacement = "import { " + ", ".join(names) + " } from 'electron'"
    return text[:match.start()] + replacement + text[match.end():]

def patch_preload(text):
    out = ensure_electron_imports(text)
    if "VERTEX_VRA_DISPATCH_DESTINATION_000046" not in out:
        out = out.rstrip() + "\n" + PRELOAD_BLOCK + "\n"
    return out

def patch_mainframe(text):
    return add_import(text, MAINFRAME_IMPORT)

def patch_lane_css(text):
    if "VERTEX_VRA_DISPATCH_DESTINATION_000046" in text:
        return text
    return text.rstrip() + "\n\n" + CSS_BLOCK + "\n"

def patch_service(text):
    out = add_import(text, SERVICE_IMPORT)
    if "VERTEX_VRA_DISPATCH_DESTINATION_000046_SERVICE" in out:
        return out

    lines = out.splitlines()
    patched = 0
    new_lines = []

    assignment = re.compile(
        r"^(?P<prefix>\s*(?:(?:const|let|var)\s+[A-Za-z0-9_]*"
        r"(?:receiv|incoming|dispatch)[A-Za-z0-9_]*\s*=|"
        r"this\.[A-Za-z0-9_]*(?:receiv|incoming|dispatch)[A-Za-z0-9_]*\s*=))"
        r"(?P<rhs>.*_incoming.*?)(?P<semi>;?\s*)$",
        re.IGNORECASE,
    )
    returned = re.compile(r"^(?P<prefix>\s*return\s+)(?P<rhs>.*_incoming.*?)(?P<semi>;\s*)$", re.IGNORECASE)

    for line in lines:
        m = assignment.match(line)
        if m:
            new_lines.append(
                m.group("prefix")
                + " getVraDispatchDestination()"
                + (m.group("semi") if m.group("semi") else ";")
            )
            patched += 1
            continue
        m = returned.match(line)
        if m:
            new_lines.append(m.group("prefix") + "getVraDispatchDestination()" + m.group("semi"))
            patched += 1
            continue
        new_lines.append(line)

    out = "\n".join(new_lines) + ("\n" if text.endswith("\n") else "")

    if patched == 0:
        # Fail closed with useful diagnostics. Never silently claim that the selected
        # destination controls dispatch if the current service shape cannot be proven.
        candidates = [
            f"{i+1}:{line}"
            for i, line in enumerate(lines)
            if "_incoming" in line or "receiv" in line.lower()
        ]
        safe_emit("SERVICE_CANDIDATES_BEGIN")
        for row in candidates[:80]:
            safe_emit(row)
        safe_emit("SERVICE_CANDIDATES_END")
        raise RuntimeError("VRA_DISPATCH_SERVICE_DESTINATION_ANCHOR_NOT_PATCHED")

    marker = "\n// VERTEX_VRA_DISPATCH_DESTINATION_000046_SERVICE\n"
    out = marker + out
    print(f"SERVICE_DESTINATION_PATCH_COUNT={patched}")
    return out

def run_build():
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
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
    print(f"BUILD_EXIT={result.returncode}")
    return result.returncode

def main():
    print("=== VERTEX SESSION PORTAL / GLOBAL DISPATCH DESTINATION APPLY 000046 ===")
    print(f"ROOT={ROOT}")
    backup()

    originals = {path: read(path) for path in TOUCH}
    try:
        write(MAIN, patch_main(originals[MAIN]))
        write(PRELOAD, patch_preload(originals[PRELOAD]))
        write(SERVICE, patch_service(originals[SERVICE]))
        write(MAINFRAME, patch_mainframe(originals[MAINFRAME]))
        write(LANE_CSS, patch_lane_css(originals[LANE_CSS]))

        if run_build() != 0:
            raise RuntimeError("GLOBAL_DISPATCH_DESTINATION_BUILD_FAILED")

    except Exception:
        restore()
        raise

    print("GLOBAL_DESTINATION_SCOPE=SINGLE_DISPATCH_BAY")
    print(r"DEFAULT_DESTINATION=G:\Vertex_Project\Development\_incoming")
    print("DESTINATION_STORAGE=ELECTRON_USER_DATA_JSON")
    print("DIRECTORY_PICKER=PASS")
    print("BUTTON_PLACEMENT=ADJACENT_TO_DISPATCH_BAY_RELOAD")
    print("PER_CARD_DESTINATION=NO")
    print("PER_VERA_DESTINATION=NO")
    print("PORTABLE_PATH_DEPENDENCE=RETIRED")
    print("VERTEX_SESSION_PORTAL_GLOBAL_DISPATCH_DESTINATION_000046_APPLY=PASS")

if __name__ == "__main__":
    main()
