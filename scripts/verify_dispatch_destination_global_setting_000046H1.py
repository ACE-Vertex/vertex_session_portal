from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "store": ROOT / "src/main/vra/vra-dispatch-destination-store.ts",
    "ipc": ROOT / "src/main/ipc/register-vra-dispatch-destination-ipc.ts",
    "policy": ROOT / "src/main/vra/vra-download-destination-policy.ts",
    "preload": ROOT / "src/preload/index.ts",
    "main": ROOT / "src/main/index.ts",
    "control": ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchDestinationControl.ts",
    "mainframe": ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts",
    "css": ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css",
}

def text(name):
    path = FILES[name]
    return path.read_text(encoding="utf-8") if path.exists() else ""

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
    print("=== VERTEX SESSION PORTAL / GLOBAL VRA DOWNLOAD DESTINATION VERIFY 000046H1 ===")
    failures = []

    store = text("store")
    ipc = text("ipc")
    policy = text("policy")
    preload = text("preload")
    main_ts = text("main")
    control = text("control")
    mainframe = text("mainframe")
    css = text("css")

    check("DEFAULT_OLD_WORKS_RECEIVING_BAY",
          r"G:\\Vertex_Project\\Development\\_incoming" in store, failures)
    check("GLOBAL_USERDATA_PERSISTENCE",
          "app.getPath('userData')" in store and
          "vra-dispatch-destination.json" in store,
          failures)
    check("NATIVE_DIRECTORY_PICKER",
          "dialog.showOpenDialog" in store and "'openDirectory'" in store,
          failures)
    check("IPC_GET", "vertex:vra-dispatch-destination:get" in ipc, failures)
    check("IPC_CHOOSE", "vertex:vra-dispatch-destination:choose" in ipc, failures)
    check("IPC_REGISTERED",
          "registerVraDispatchDestinationIpc()" in main_ts, failures)
    check("DOWNLOAD_POLICY_REGISTERED",
          "registerVraDownloadDestinationPolicy()" in main_ts, failures)
    check("PRELOAD_BRIDGE",
          "vertexDispatchDestination" in preload and
          "vertex:vra-dispatch-destination:choose" in preload,
          failures)

    check("VRA_ONLY_DOWNLOAD_POLICY",
          "getFilename().toLowerCase().endsWith('.vra')" in policy,
          failures)
    check("WILL_DOWNLOAD_POLICY",
          "'will-download'" in policy and "item.setSavePath(target)" in policy,
          failures)
    check("PORTABLE_PATH_INDEPENDENT",
          "getVraDispatchDestination()" in policy and
          "process.cwd" not in policy and
          "app.getAppPath" not in policy,
          failures)
    check("OLD_HANDLER_OVERRIDE_FALLBACK",
          "moveCompletedDownload(actualPath, configured)" in policy,
          failures)
    check("POLICY_REBINDS_LAST",
          "removeListener('will-download', previous)" in policy and
          "targetSession.on('will-download', handler)" in policy,
          failures)

    check("DISPATCH_CONTROL_IMPORTED",
          "VraDispatchDestinationControl" in mainframe, failures)
    check("CONTROL_PATCHES_DISPATCH_LANE",
          "vertex-vra-dispatch-lane" in control and
          "data-vra-dispatch-destination-control" in control,
          failures)
    check("CONTROL_FINDS_RELOAD",
          "looksLikeReload" in control and
          "reload.insertAdjacentElement('afterend', button)" in control,
          failures)
    check("CONTROL_SURVIVES_RERENDER",
          "MutationObserver" in control and "queueMicrotask" in control,
          failures)
    check("CONTROL_GLOBAL_NOT_PER_CARD",
          "cardId" not in control, failures)
    check("CONTROL_STYLE_PRESENT",
          "data-vra-dispatch-destination-control" in css,
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
    print("DESTINATION_OWNER=ELECTRON_WILL_DOWNLOAD")
    print("PER_CARD_DESTINATION=NO")
    print("PER_VERA_DESTINATION=NO")
    print("VERTEX_SESSION_PORTAL_GLOBAL_VRA_DOWNLOAD_DESTINATION_000046H1=PASS")

if __name__ == "__main__":
    main()
