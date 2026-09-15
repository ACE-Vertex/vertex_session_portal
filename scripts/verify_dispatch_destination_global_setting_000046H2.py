from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""

def safe_emit(value, stream=None):
    stream = stream or sys.stdout
    enc = getattr(stream, "encoding", None) or "utf-8"
    out = str(value).encode(enc, errors="backslashreplace").decode(enc, errors="replace")
    stream.write(out)
    if out and not out.endswith("\n"):
        stream.write("\n")

def check(name, ok, failures):
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)

def main():
    print("=== VERTEX SESSION PORTAL / GLOBAL VRA DESTINATION VERIFY 000046H2 ===")
    failures = []

    main_ts = read("src/main/index.ts")
    preload = read("src/preload/index.ts")
    mainframe = read("src/renderer/src/components/MainFrame/MainFrame.ts")
    store = read("src/main/vra/vra-dispatch-destination-store.ts")
    ipc = read("src/main/ipc/register-vra-dispatch-destination-ipc.ts")
    bootstrap = read("src/main/vra/vra-dispatch-destination-bootstrap.ts")
    bridge = read("src/preload/vra-dispatch-destination-bridge.ts")
    policy = read("src/main/vra/vra-download-destination-policy.ts")
    control = read("src/renderer/src/components/VraDispatchLane/VraDispatchDestinationControl.ts")

    check("MAIN_SIDE_EFFECT_IMPORT_FIRST_LINE",
          main_ts.startswith("import './vra/vra-dispatch-destination-bootstrap'\n"),
          failures)
    check("PRELOAD_SIDE_EFFECT_IMPORT_FIRST_LINE",
          preload.startswith("import './vra-dispatch-destination-bridge'\n"),
          failures)
    check("MAINFRAME_SIDE_EFFECT_IMPORT_FIRST_LINE",
          mainframe.startswith("import '../VraDispatchLane/VraDispatchDestinationControl'\n"),
          failures)

    check("DEFAULT_OLD_WORKS_RECEIVING_BAY",
          r"G:\\Vertex_Project\\Development\\_incoming" in store, failures)
    check("GLOBAL_USERDATA_PERSISTENCE",
          "app.getPath('userData')" in store and "vra-dispatch-destination.json" in store,
          failures)
    check("NATIVE_DIRECTORY_PICKER",
          "dialog.showOpenDialog" in store and "'openDirectory'" in store,
          failures)
    check("IPC_CHANNELS",
          "vertex:vra-dispatch-destination:get" in ipc and
          "vertex:vra-dispatch-destination:choose" in ipc,
          failures)
    check("BOOTSTRAP_REGISTERS_IPC_AND_DOWNLOAD",
          "registerVraDispatchDestinationIpc()" in bootstrap and
          "registerVraDownloadDestinationPolicy()" in bootstrap,
          failures)
    check("PRELOAD_BRIDGE",
          "contextBridge.exposeInMainWorld('vertexDispatchDestination'" in bridge,
          failures)
    check("VRA_ONLY_DOWNLOAD_POLICY",
          "endsWith('.vra')" in policy and "item.setSavePath(target)" in policy,
          failures)
    check("DOWNLOAD_FALLBACK_RELOCATION",
          "moveCompletedDownload(actualPath, configured)" in policy,
          failures)
    check("CONTROL_NEXT_TO_RELOAD",
          "reload.insertAdjacentElement('afterend', button)" in control,
          failures)
    check("CONTROL_RERENDER_SURVIVAL",
          "MutationObserver" in control,
          failures)
    check("CONTROL_GLOBAL_ONLY",
          "cardId" not in control,
          failures)

    if failures:
        print("STATIC_FAILURES=" + ",".join(failures))
        raise SystemExit(2)

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
    check("BUILD", result.returncode == 0, failures)

    if failures:
        raise SystemExit(3)

    print("GLOBAL_DESTINATION_SCOPE=DISPATCH_BAY")
    print("PER_CARD_DESTINATION=NO")
    print("PER_VERA_DESTINATION=NO")
    print("VERTEX_SESSION_PORTAL_GLOBAL_VRA_DESTINATION_000046H2=PASS")

if __name__ == "__main__":
    main()
