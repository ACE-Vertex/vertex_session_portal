from pathlib import Path
import subprocess
import sys

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SYNC = ROOT / "src/main/vra-registry/auto-registry-workstation-sync.ts"
CORE = ROOT / "src/main/vra-registry/vra-registry-core.ts"

OLD_SYNC = "if (record.state === 'RETURNED' || record.state === 'FAILED' || record.state === 'REJECTED') {"
NEW_SYNC = "if (record.state === 'RETURNED' || record.state === 'REJECTED') {"

OLD_CORE = "FAILED: [],"
NEW_CORE = "FAILED: ['EVIDENCE_AVAILABLE'],"

def emit(s=""):
    print(str(s).encode("ascii", "backslashreplace").decode("ascii"))

def die(msg, code=1):
    emit("REPAIR_STATUS=FAILED")
    emit("DETAIL=" + msg)
    raise SystemExit(code)

def run_typecheck():
    cp = subprocess.run(
        ["npm.cmd", "run", "typecheck"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    emit(f"TYPECHECK_EXIT={cp.returncode}")
    if cp.stdout:
        emit("TYPECHECK_STDOUT_TAIL=" + cp.stdout[-6000:].replace("\r", " ").replace("\n", "\\n"))
    if cp.stderr:
        emit("TYPECHECK_STDERR_TAIL=" + cp.stderr[-6000:].replace("\r", " ").replace("\n", "\\n"))
    return cp.returncode

emit("FAILED_EVIDENCE_RETURN_LIFECYCLE_REPAIR_000078V3=BEGIN")

for p in (SYNC, CORE):
    if not p.exists():
        die("SOURCE_MISSING:" + str(p), 10)

sync_before = SYNC.read_text(encoding="utf-8")
core_before = CORE.read_text(encoding="utf-8")

# Fail closed on unexpected source drift.
if sync_before.count(OLD_SYNC) != 1:
    die(f"SYNC_ANCHOR_COUNT={sync_before.count(OLD_SYNC)}", 11)
if core_before.count(OLD_CORE) != 1:
    die(f"CORE_ANCHOR_COUNT={core_before.count(OLD_CORE)}", 12)

# Preserve failure tracking and return lifecycle anchors.
required_sync_anchors = [
    "await core.fail(record.registryId)",
    "observation.workstationJobState === 'FAILED'",
    "observation.workstationJobState === 'REJECTED'",
    "observation.workstationJobState === 'ROLLED_BACK'",
]
for anchor in required_sync_anchors:
    if anchor not in sync_before:
        die("SYNC_REQUIRED_ANCHOR_MISSING:" + anchor, 13)

required_core_anchors = [
    "EVIDENCE_AVAILABLE: ['RETURN_QUEUED', 'FAILED']",
    "RETURN_QUEUED: ['RETURNED', 'FAILED']",
    "RETURNED: []",
]
for anchor in required_core_anchors:
    if anchor not in core_before:
        die("CORE_REQUIRED_ANCHOR_MISSING:" + anchor, 14)

sync_after = sync_before.replace(OLD_SYNC, NEW_SYNC, 1)
core_after = core_before.replace(OLD_CORE, NEW_CORE, 1)

changed = False
try:
    SYNC.write_text(sync_after, encoding="utf-8", newline="\n")
    CORE.write_text(core_after, encoding="utf-8", newline="\n")
    changed = True

    # Post-write assertions.
    sync_now = SYNC.read_text(encoding="utf-8")
    core_now = CORE.read_text(encoding="utf-8")

    assertions = {
        "FAILED_REMOVED_FROM_EARLY_TERMINAL": NEW_SYNC in sync_now and OLD_SYNC not in sync_now,
        "FAILED_CAN_ADVANCE_TO_EVIDENCE_AVAILABLE": NEW_CORE in core_now and OLD_CORE not in core_now,
        "FAILURE_TRACKING_PRESERVED": "await core.fail(record.registryId)" in sync_now,
        "RETURN_QUEUE_PATH_PRESERVED": "EVIDENCE_AVAILABLE: ['RETURN_QUEUED', 'FAILED']" in core_now,
        "RETURNED_PATH_PRESERVED": "RETURN_QUEUED: ['RETURNED', 'FAILED']" in core_now,
    }

    for name, ok in assertions.items():
        emit(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError("POST_WRITE_ASSERTION_FAILED:" + name)

    if run_typecheck() != 0:
        raise RuntimeError("TYPECHECK_FAILED")

    emit("REPAIR_SCOPE=2_FILES")
    emit("EXECUTION_FAILURE_TRACKING=PRESERVED")
    emit("EVIDENCE_RETURN_LIFECYCLE=DECOUPLED_FROM_FAILED_TERMINAL")
    emit("RUNTIME_RESTART_REQUIRED=YES")
    emit("REPAIR_STATUS=SUCCEEDED")
    emit("FAILED_EVIDENCE_RETURN_LIFECYCLE_REPAIR_000078V3=PASS")
    raise SystemExit(0)

except SystemExit:
    raise
except Exception as e:
    if changed:
        try:
            SYNC.write_text(sync_before, encoding="utf-8", newline="\n")
            CORE.write_text(core_before, encoding="utf-8", newline="\n")
            emit("SELF_ROLLBACK=RESTORED_BOTH_SOURCE_FILES")
        except Exception as rollback_error:
            emit("SELF_ROLLBACK=FAILED")
            emit("SELF_ROLLBACK_DETAIL=" + repr(rollback_error))
    die(type(e).__name__ + ":" + str(e), 20)
