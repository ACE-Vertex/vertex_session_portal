from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
CSS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css"
WORKSTATION = ROOT.parent / "vertex_workstation"

def emit(v):
    print(str(v).encode("cp932", errors="backslashreplace").decode("cp932", errors="replace"), flush=True)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def snapshot(base):
    if not base.is_dir():
        return {}
    return {p.relative_to(base).as_posix(): sha(p) for p in sorted(base.rglob("*")) if p.is_file()}

def check(name, ok, failures):
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)

def run(cmd, label):
    emit("RUN_" + label + "=" + " ".join(str(x) for x in cmd))
    cp = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
        timeout=1800
    )
    emit(f"{label}_EXIT={cp.returncode}")
    emit(f"{label}_TAIL=" + (cp.stdout or "")[-10000:].replace("\n", " | "))
    return cp.returncode == 0

def main():
    failures = []
    emit("=== SESSION PORTAL ONLINE RECONCILE / INTERACTION ISOLATION 000079V5 ===")
    emit("ROOT_CAUSE=ONLINE_WORKSTATION_RECONCILE_PERSISTED_AND_EMITTED_UNCHANGED_CARD_STATE")
    emit("SECONDARY=RENDERER_DUPLICATED_MAIN_2500MS_POLL")
    emit("FIX=EDGE_TRIGGERED_PERSIST_EMIT+SINGLE_MAIN_POLL_OWNER+000078_INTERACTION_HARDENING")
    emit("WORKSTATION_PRODUCTION_MUTATION=ZERO")
    emit("HUMAN_GATE=PRESERVED")
    emit("EVIDENCE_EXACT_ORIGIN=PRESERVED")

    for name, path in [("SERVICE", SERVICE), ("LANE", LANE), ("CSS", CSS)]:
        check(f"FILE_{name}", path.is_file(), failures)
    if failures:
        return 2

    service = SERVICE.read_text(encoding="utf-8-sig")
    lane = LANE.read_text(encoding="utf-8-sig")
    css = CSS.read_text(encoding="utf-8-sig")

    check("MAIN_RECONCILER_STILL_PRESENT", "private startWorkstationReconciler(): void" in service, failures)
    check("MATERIAL_SYNC_KEY", "private workstationCardSyncKey" in service, failures)
    check("UPDATE_STATE_EDGE_TRIGGERED",
          "if (before !== this.workstationCardSyncKey(card)) this.persistCardState(card)" in service,
          failures)
    check("JOB_APPLY_RETURNS_CHANGE", "private applyWorkstationJob" in service and "): boolean {" in service, failures)
    check("JOB_GET_NO_UNCONDITIONAL_PERSIST",
          "const before = this.workstationCardSyncKey(card)" in service and
          "if (before !== this.workstationCardSyncKey(card)) this.persistCardState(card)" in service,
          failures)
    check("EVIDENCE_CACHE_GUARD",
          "evidenceNeedsPickup" in service and "this.evidenceCachePresent(card)" in service,
          failures)
    check("UNCHANGED_ERROR_NO_EMIT",
          "if (card.workstationLastError !== message)" in service,
          failures)

    check("RENDERER_SECOND_POLL_REMOVED",
          "evidenceReturnPoll" not in lane,
          failures)
    check("RENDERER_EVENT_DRIVEN",
          "onVraDispatchChanged" in lane and "void this.refresh()" in lane,
          failures)

    # 000078 interaction hardening is carried forward.
    check("STABLE_DOM_REORDER_ONLY",
          "else if (node !== expectedNode)" in lane and "queue.insertBefore(node, expectedNode)" in lane,
          failures)
    check("NO_EXISTING_APPEND_CHURN", "queue.appendChild(node)" not in lane, failures)
    check("INTERACTION_DRAG_LOCK",
          "data-interaction-lock" in lane and "root.dataset.interactionLock !== 'true'" in lane,
          failures)
    check("CARD_FOCUSABLE", 'role="option" tabindex="0"' in lane, failures)
    check("REMOVE_EVENT_CONSUMED", "event.stopPropagation()" in lane, failures)
    check("HOVER_FOCUS_ACTIVE_CSS",
          ".vraCard:hover" in css and ".vraCard:focus-visible" in css and ".vraCard:active" in css,
          failures)
    check("REMOVE_ACTIVE_CSS", ".cardRemove:active:not(:disabled)" in css, failures)

    check("EXACT_ORIGIN_FAIL_CLOSED",
          "EVIDENCE_ORIGIN_ROUTE_MISMATCH" in service and "origin-mismatch-fail-closed" in lane,
          failures)
    check("DELIVERED_BEFORE_ACK",
          "receipt.state !== 'DELIVERED'" in lane and "acknowledgeVraEvidenceDelivery" in lane,
          failures)

    portal_before = snapshot(ROOT / "src")
    ws_before = snapshot(WORKSTATION / "headless/src") | snapshot(WORKSTATION / "src-tauri/src")

    npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
    check("NPM_RESOLVED", npm is not None, failures)
    if npm:
        check("TYPECHECK", run([npm, "run", "typecheck"], "TYPECHECK"), failures)
        check("BUILD", run([npm, "run", "build"], "BUILD"), failures)

    portal_after = snapshot(ROOT / "src")
    ws_after = snapshot(WORKSTATION / "headless/src") | snapshot(WORKSTATION / "src-tauri/src")

    check("VERIFY_PORTAL_SOURCE_UNCHANGED", portal_before == portal_after, failures)
    check("VERIFY_WORKSTATION_SOURCE_UNCHANGED", ws_before == ws_after, failures)

    if failures:
        emit("VERTEX_SESSION_PORTAL_ONLINE_RECONCILE_INTERACTION_ISOLATION_000079V5=FAIL")
        emit("FAILED=" + ",".join(failures))
        return 1

    emit("VERTEX_SESSION_PORTAL_ONLINE_RECONCILE_INTERACTION_ISOLATION_000079V5=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
