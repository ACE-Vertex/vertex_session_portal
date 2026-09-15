from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "store": ROOT / "src/main/vra/vra-dispatch-destination-store.ts",
    "ipc": ROOT / "src/main/ipc/register-vra-dispatch-destination-ipc.ts",
    "preload": ROOT / "src/preload/index.ts",
    "main": ROOT / "src/main/index.ts",
    "service": ROOT / "src/main/vra/vra-dispatch-service.ts",
    "control": ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchDestinationControl.ts",
    "mainframe": ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts",
    "css": ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css",
}

def text(name):
    p = FILES[name]
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
    print("=== VERTEX SESSION PORTAL / GLOBAL DISPATCH DESTINATION VERIFY 000046 ===")
    failures = []

    store = text("store")
    ipc = text("ipc")
    preload = text("preload")
    main_ts = text("main")
    service = text("service")
    control = text("control")
    mainframe = text("mainframe")
    css = text("css")

    check("DEFAULT_OLD_WORKS_RECEIVING_BAY",
          r"G:\\Vertex_Project\\Development\\_incoming" in store, failures)
    check("GLOBAL_USERDATA_PERSISTENCE",
          "app.getPath('userData')" in store and "vra-dispatch-destination.json" in store,
          failures)
    check("NATIVE_DIRECTORY_PICKER",
          "dialog.showOpenDialog" in store and "'openDirectory'" in store, failures)
    check("IPC_GET", "vertex:vra-dispatch-destination:get" in ipc, failures)
    check("IPC_CHOOSE", "vertex:vra-dispatch-destination:choose" in ipc, failures)
    check("IPC_REGISTERED", "registerVraDispatchDestinationIpc()" in main_ts, failures)
    check("PRELOAD_BRIDGE",
          "vertexDispatchDestination" in preload and
          "vertex:vra-dispatch-destination:choose" in preload,
          failures)
    check("SERVICE_USES_CONFIGURED_DESTINATION",
          "getVraDispatchDestination()" in service and
          "VERTEX_VRA_DISPATCH_DESTINATION_000046_SERVICE" in service,
          failures)
    check("DISPATCH_CONTROL_IMPORTED",
          "VraDispatchDestinationControl" in mainframe, failures)
    check("CONTROL_PATCHES_DISPATCH_LANE",
          "vertex-vra-dispatch-lane" in control and
          "data-vra-dispatch-destination-control" in control,
          failures)
    check("CONTROL_FINDS_RELOAD",
          "looksLikeReload" in control and "reload.insertAdjacentElement('afterend', button)" in control,
          failures)
    check("CONTROL_GLOBAL_NOT_PER_CARD",
          "querySelectorAll<LaneElement>('vertex-vra-dispatch-lane')" in control and
          "cardId" not in control,
          failures)
    check("CONTROL_STYLE_PRESENT",
          "data-vra-dispatch-destination-control" in css, failures)

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
    print("VERTEX_SESSION_PORTAL_GLOBAL_DISPATCH_DESTINATION_000046=PASS")

if __name__ == "__main__":
    main()
