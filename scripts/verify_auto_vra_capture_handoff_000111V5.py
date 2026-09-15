from __future__ import annotations
from pathlib import Path
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
BRIDGE = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts"
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
NPM = Path(r"C:\Program Files\nodejs\npm.cmd")

def emit(v):
    print(str(v).encode("ascii", errors="backslashreplace").decode("ascii"), flush=True)

def check(name, ok):
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def run_npm(*args):
    p = subprocess.run(
        [str(NPM), *args], cwd=ROOT, text=True, capture_output=True,
        errors="replace", timeout=240, shell=False
    )
    emit(f"EXIT={p.returncode}")
    if p.stdout:
        emit("STDOUT_TAIL=" + p.stdout[-18000:].replace("\r", ""))
    if p.stderr:
        emit("STDERR_TAIL=" + p.stderr[-18000:].replace("\r", ""))
    return p.returncode

def main():
    emit("=== AUTO VRA CAPTURE HANDOFF 000111V5 ===")
    emit("FLOW=VRA_ARTIFACT_MARKER -> LINK_CLICK -> WILL_DOWNLOAD -> CAPTURE -> AUTO_AUTHORITY -> WORKSTATION")
    emit("DOM_POLICY=MARKER_BOUNDED_ONLY")
    emit("BLOCKED_RESULT=NON_TERMINAL_PROGRESS")

    b = BRIDGE.read_text(encoding="utf-8", errors="replace")
    s = SERVICE.read_text(encoding="utf-8", errors="replace")

    ok = True
    ok &= check("VRA_ARTIFACT_PROTOCOL",
        "[VERTEX_VRA_ARTIFACT/1]" in b
        and "[/VERTEX_VRA_ARTIFACT/1]" in b
        and "vertex-vra-artifact/1" in b)
    ok &= check("AUTO_TASK_INSTRUCTS_VRA_HANDOFF",
        "[VERTEX AUTO VRA HANDOFF CONTRACT]" in b
        and "HumanへVRAリンクのクリックや発注クリックを要求しないでください" in b)
    ok &= check("STRICT_SOURCE_AND_FILENAME",
        "AUTO_VRA_SOURCE_MISMATCH" in b
        and "AUTO_VRA_FILENAME_INVALID" in b
        and "AUTO_VRA_ARTIFACT_ID_INVALID" in b)
    ok &= check("MARKER_BOUNDED_PROBE",
        "function autoVraArtifactProbeScript(): string" in b
        and "VRA_ARTIFACT_START" in b
        and "AUTO_VRA_DOM_READ_IS_MARKER_BOUNDED_ONLY" in b)
    ok &= check("SAME_MESSAGE_LINK_RESOLUTION",
        "node.querySelectorAll('a[href]')" in b
        and "VRA_LINK_AMBIGUOUS" in b
        and "VRA_MARKER_NOT_FOUND" in b)
    ok &= check("USER_GESTURE_DOWNLOAD_COMMIT",
        "autoVraArtifactClickScript(" in b
        and "true" in b
        and "VRA_LINK_CLICKED" in b)
    ok &= check("OLD_ARTIFACT_BASELINE",
        "autoVraBaselines" in b
        and "await seedAutoVraBaselines(authority.allowed_sessions)" in b
        and "Anything already visible is never auto-downloaded" in b)
    ok &= check("ACTIVE_AUTHORITY_REQUIRED",
        "function authorityForSession(source: string)" in b
        and "autoVraExecutionContext(" in b
        and "context.authority_id !== lease.authority_id" in b)
    ok &= check("AUTO_VRA_RECEIPT_DEDUPE",
        "AUTO_VRA_RECEIPT_KEY" in b
        and "receipts.has(logical)" in b
        and "saveStringSet(AUTO_VRA_RECEIPT_KEY" in b)
    ok &= check("BLOCKED_RESULT_CONTEXT_HELD",
        "BLOCKED is a progress return, not terminal completion" in b
        and "BLOCKED_RESULT_PRESERVES_AUTO_TASK_CONTEXT" in b
        and "item.resultStatus === 'BLOCKED'" in b)
    ok &= check("DONE_FAILED_TERMINAL_STILL_PRESENT",
        "clearAutoTaskContext(sourceOfResult, item.dispatchId)" in b
        and "saveResultReceipts(done)" in b)
    ok &= check("RESULT_MARKER_BOUNDARY_PRESERVED",
        "RESULT_DOM_READ_IS_MARKER_BOUNDED_ONLY" in b)
    ok &= check("000109_MAIN_AUTO_DISPATCH_PRESERVED",
        "private reconcileAutoAuthorizedStagedCards(): void" in s
        and "Human AUTO arm is the execution authority grant" in s)
    ok &= check("WILL_DOWNLOAD_CAPTURE_OWNER_PRESERVED",
        "ONE AND ONLY owner of .vra `will-download` capture" in s
        and "target.on('will-download'" in s)
    ok &= check("IMMUTABLE_ORIGIN_CAPTURE_PRESERVED",
        "const origin = this.captureOrigin(webContents)" in s
        and "VRA_ORIGIN_UNRESOLVED" in s)
    ok &= check("WORKSTATION_LANE_AUTHORITY_PRESERVED",
        "Never assign allocatedLane here. Final Lane Allocation Authority is Workstation." in s)

    if not ok:
        return 21

    emit("RUN=npm run typecheck")
    if run_npm("run", "typecheck") != 0:
        return 30

    emit("RUN=npm run build")
    if run_npm("run", "build") != 0:
        return 31

    emit("AUTO_VRA_CAPTURE_HANDOFF=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
