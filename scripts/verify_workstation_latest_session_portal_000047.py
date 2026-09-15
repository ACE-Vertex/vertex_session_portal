from pathlib import Path
import hashlib
import json

DEV = Path(r"G:\Vertex_Project\Development")
SRC = DEV / "vertex_session_portal"
WORKSTATION = DEV / "vertex_workstation"
DEST = WORKSTATION / "SESSION_PORTAL_LATEST"
EXE = DEST / "Vertex Session Portal.exe"
LAUNCHER = WORKSTATION / "START_SESSION_PORTAL_LATEST.cmd"
MANIFEST = DEST / "build-manifest.json"
SHA_FILE = DEST / "Vertex Session Portal.exe.sha256.txt"

def check(name, ok, failures):
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=== VERTEX SESSION PORTAL / WORKSTATION LATEST VERIFY 000047 ===")
    failures = []

    check("LATEST_DIR_PRESENT", DEST.exists(), failures)
    check("LATEST_EXE_PRESENT", EXE.exists(), failures)
    check("LATEST_LAUNCHER_PRESENT", LAUNCHER.exists(), failures)
    check("LATEST_MANIFEST_PRESENT", MANIFEST.exists(), failures)
    check("LATEST_SHA_PRESENT", SHA_FILE.exists(), failures)

    if EXE.exists() and MANIFEST.exists() and SHA_FILE.exists():
        digest = sha256(EXE)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        check("MANIFEST_CHANNEL_LATEST", manifest.get("channel") == "LATEST", failures)
        check("MANIFEST_FIVE_WINDOW", manifest.get("five_window_verified") is True, failures)
        check("MANIFEST_DISPATCH_SETTING", manifest.get("dispatch_destination_setting_verified") is True, failures)
        check("MANIFEST_DISPATCH_STAGING_FIRST", manifest.get("dispatch_staging_first_verified") is True, failures)
        check("MANIFEST_DISPATCH_HUMAN_EXPORT", manifest.get("dispatch_human_export_verified") is True, failures)
        check("MANIFEST_VRA_CAPTURE_OWNER", manifest.get("vra_capture_owner") == "VRA_DISPATCH_SERVICE_ONLY", failures)
        check("MANIFEST_DISPATCH_FLOW", manifest.get("dispatch_flow") == "CHATGPT_TO_STAGING_TO_DISPATCH_BAY_TO_HUMAN_EXPORT_OR_WORKS", failures)
        check("MANIFEST_SHA_MATCH", manifest.get("exe_sha256") == digest, failures)
        check("SHA_FILE_MATCH", digest in SHA_FILE.read_text(encoding="utf-8"), failures)

    scaler = SRC / "src/renderer/src/components/VeraWindowScaler/VeraWindowScaler.ts"
    dispatch = SRC / "src/renderer/src/components/VraDispatchLane/VraDispatchDestinationControl.ts"
    dispatch_service = SRC / "src/main/vra/vra-dispatch-service.ts"
    dispatch_policy = SRC / "src/main/vra/vra-download-destination-policy.ts"

    check(
        "SOURCE_MAX_FIVE",
        scaler.exists() and "const MAX_COUNT = 5" in scaler.read_text(encoding="utf-8"),
        failures,
    )
    check(
        "SOURCE_DISPATCH_SETTING_AFTER_RELOAD",
        dispatch.exists() and "reload.insertAdjacentElement('afterend', button)" in dispatch.read_text(encoding="utf-8"),
        failures,
    )
    service_text = dispatch_service.read_text(encoding="utf-8") if dispatch_service.exists() else ""
    policy_text = dispatch_policy.read_text(encoding="utf-8") if dispatch_policy.exists() else ""
    check(
        "SOURCE_DISPATCH_STAGING_FIRST",
        "item.setSavePath(stagedPath)" in service_text,
        failures,
    )
    check(
        "SOURCE_DISPATCH_HUMAN_EXPORT",
        "exportCard(cardId: string): string" in service_text,
        failures,
    )
    check(
        "SOURCE_DISPATCH_POLICY_PASSIVE",
        "capture owner = VraDispatchService" in policy_text and "item.setSavePath(target)" not in policy_text,
        failures,
    )

    if failures:
        print("FAILURES=" + ",".join(failures))
        raise SystemExit(2)

    print("CANONICAL_LATEST_EXE=" + str(EXE))
    print("CANONICAL_LATEST_LAUNCHER=" + str(LAUNCHER))
    print("VERTEX_SESSION_PORTAL_WORKSTATION_LATEST_VERIFY_000047=PASS")

if __name__ == "__main__":
    main()
