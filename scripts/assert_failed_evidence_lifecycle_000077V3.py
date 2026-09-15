from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")

sync_path = ROOT / "src/main/vra-registry/auto-registry-workstation-sync.ts"
core_path = ROOT / "src/main/vra-registry/vra-registry-core.ts"
lane_path = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
browser_path = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts"
preload_path = ROOT / "src/preload/index.ts"
ipc_path = ROOT / "src/main/ipc/register-vra-dispatch-ipc.ts"

paths = [sync_path, core_path, lane_path, browser_path, preload_path, ipc_path]
for p in paths:
    if not p.exists():
        print("ASSERT=SOURCE_MISSING")
        print("PATH=" + str(p))
        raise SystemExit(10)

def read(p):
    return p.read_text(encoding="utf-8", errors="replace")

sync = read(sync_path)
core = read(core_path)
lane = read(lane_path)
browser = read(browser_path)
preload = read(preload_path)
ipc = read(ipc_path)

checks = [
    (
        "FAILED_IS_EARLY_TERMINAL_IN_SYNC",
        "record.state === 'RETURNED' || record.state === 'FAILED' || record.state === 'REJECTED'" in sync
    ),
    (
        "WORKSTATION_FAILURE_CALLS_REGISTRY_FAIL",
        "await core.fail(record.registryId)" in sync
    ),
    (
        "FAILED_IS_TERMINAL_IN_REGISTRY_CORE",
        "FAILED: []" in core
    ),
    (
        "RETURN_PATH_HAS_RENDERER_INFLIGHT_TRACKING",
        "evidenceInFlight" in lane and "VeraEvidenceReturnResult" in lane
    ),
    (
        "VERA_SESSION_HAS_EVIDENCE_DELIVERY_PATH",
        "deliverWorkstationEvidence" in browser and "VERA_EVIDENCE_RETURN_EVENT" in browser
    ),
    (
        "ACK_API_EXISTS_PRELOAD_TO_MAIN",
        "acknowledgeVraEvidenceDelivery" in preload
        and "workstation:vra-evidence-ack" in preload
        and "workstation:vra-evidence-ack" in ipc
        and "acknowledgeEvidenceDelivery" in ipc
    ),
]

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{name}={'PASS' if ok else 'FAIL'}")

if failed:
    print("ASSERT_RESULT=FAILED")
    print("FAILED_CHECKS=" + ",".join(failed))
    raise SystemExit(20)

print("ASSERT_RESULT=CONFIRMED")
print("INTERPRETATION=Execution FAILED is terminal in Registry while Evidence delivery/ACK is a separate live path.")
print("PRODUCTION_MUTATION=NONE")
raise SystemExit(0)
