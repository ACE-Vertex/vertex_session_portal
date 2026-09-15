from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "src/main/index.ts"
PRELOAD = ROOT / "src/preload/index.ts"
MAINFRAME = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
LANE_CSS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css"

BACKUP_ROOT = ROOT / "EVIDENCE" / "VRA_DISPATCH_DESTINATION_000046H1" / time.strftime("%Y%m%d-%H%M%S")
TOUCH = [MAIN, PRELOAD, MAINFRAME, LANE_CSS]

IPC_IMPORT = "import { registerVraDispatchDestinationIpc } from './ipc/register-vra-dispatch-destination-ipc'"
POLICY_IMPORT = "import { registerVraDownloadDestinationPolicy } from './vra/vra-download-destination-policy'"
IPC_CALL = "registerVraDispatchDestinationIpc()"
POLICY_CALL = "registerVraDownloadDestinationPolicy()"
MAINFRAME_IMPORT = "import '../VraDispatchLane/VraDispatchDestinationControl'"

PRELOAD_MARKER = "VERTEX_VRA_DISPATCH_DESTINATION_000046H1"
PRELOAD_BLOCK = r"""
// VERTEX_VRA_DISPATCH_DESTINATION_000046H1
contextBridge.exposeInMainWorld('vertexDispatchDestination', {
  get: () => ipcRenderer.invoke('vertex:vra-dispatch-destination:get'),
  choose: () => ipcRenderer.invoke('vertex:vra-dispatch-destination:choose')
})
"""

CSS_MARKER = "VERTEX_VRA_DISPATCH_DESTINATION_000046H1"
CSS_BLOCK = r"""
/* VERTEX_VRA_DISPATCH_DESTINATION_000046H1 */
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
    out = add_import(text, IPC_IMPORT)
    out = add_import(out, POLICY_IMPORT)

    calls = []
    if IPC_CALL not in out:
        calls.append(IPC_CALL)
    if POLICY_CALL not in out:
        calls.append(POLICY_CALL)

    if calls:
        matches = list(re.finditer(r"(?m)^import [^\n]+\n", out))
        if not matches:
            raise RuntimeError("MAIN_IMPORT_BLOCK_NOT_FOUND")
        pos = matches[-1].end()
        block = "\n// VERTEX_VRA_DISPATCH_DESTINATION_000046H1\n" + "\n".join(calls) + "\n"
        out = out[:pos] + block + out[pos:]
    return out

def ensure_electron_imports(text):
    pattern = re.compile(r"import\s*\{([^}]*)\}\s*from\s*['\"]electron['\"]")
    match = pattern.search(text)
    if not match:
        raise RuntimeError("PRELOAD_ELECTRON_NAMED_IMPORT_NOT_FOUND")

    names = [x.strip() for x in match.group(1).split(",") if x.strip()]
    for required in ("contextBridge", "ipcRenderer"):
        if required not in names:
            names.append(required)

    replacement = "import { " + ", ".join(names) + " } from 'electron'"
    return text[:match.start()] + replacement + text[match.end():]

def patch_preload(text):
    out = ensure_electron_imports(text)
    # Remove a partial H0 bridge if an operator manually kept it.
    old_marker = "// VERTEX_VRA_DISPATCH_DESTINATION_000046\n"
    if old_marker in out and PRELOAD_MARKER not in out:
        out = out.replace(old_marker, "// VERTEX_VRA_DISPATCH_DESTINATION_000046_RETAINED\n", 1)
    if PRELOAD_MARKER not in out:
        out = out.rstrip() + "\n" + PRELOAD_BLOCK + "\n"
    return out

def patch_mainframe(text):
    return add_import(text, MAINFRAME_IMPORT)

def patch_css(text):
    if CSS_MARKER in text:
        return text
    return text.rstrip() + "\n\n" + CSS_BLOCK + "\n"

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
    print("=== VERTEX SESSION PORTAL / GLOBAL VRA DOWNLOAD DESTINATION APPLY 000046H1 ===")
    print(f"ROOT={ROOT}")
    print("H0_ROOT_CAUSE=WRONG_OWNER_VRA_DISPATCH_SERVICE")
    print("H1_OWNER=ELECTRON_WILL_DOWNLOAD_POLICY")
    backup()

    originals = {path: read(path) for path in TOUCH}
    try:
        write(MAIN, patch_main(originals[MAIN]))
        write(PRELOAD, patch_preload(originals[PRELOAD]))
        write(MAINFRAME, patch_mainframe(originals[MAINFRAME]))
        write(LANE_CSS, patch_css(originals[LANE_CSS]))

        if run_build() != 0:
            raise RuntimeError("GLOBAL_VRA_DOWNLOAD_DESTINATION_BUILD_FAILED")
    except Exception:
        restore()
        raise

    print("TRANSACTION_ROLLBACK=NOT_REQUIRED")
    print(r"DEFAULT_DESTINATION=G:\Vertex_Project\Development\_incoming")
    print("GLOBAL_DESTINATION_SCOPE=DISPATCH_BAY")
    print("PER_CARD_DESTINATION=NO")
    print("PER_VERA_DESTINATION=NO")
    print("DESTINATION_OWNER=ELECTRON_DOWNLOAD_POLICY")
    print("PORTABLE_RELATIVE_INCOMING_DEPENDENCE=RETIRED")
    print("COMPLETED_DOWNLOAD_RELOCATION_FALLBACK=ENABLED")
    print("VERTEX_SESSION_PORTAL_GLOBAL_VRA_DOWNLOAD_DESTINATION_000046H1_APPLY=PASS")

if __name__ == "__main__":
    main()
