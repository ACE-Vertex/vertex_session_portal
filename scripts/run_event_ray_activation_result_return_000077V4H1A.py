#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
ER = ROOT / "EVIDENCE" / "EVENT_RAY_ACTIVATION_INCIDENT_RECOVERY_000077V4H1"

def latest():
    xs = list(ER.rglob("event_ray_activation_incident_recovery_000077V4H1.json")) if ER.exists() else []
    return max(xs, key=lambda p: p.stat().st_mtime_ns) if xs else None

def main():
    print("=== VERTEX SESSION PORTAL / EVENT RAY ACTIVATION RESULT RETURN 000077V4H1A ===")
    rp = latest()
    if not rp:
        print("H1_EVIDENCE_PRESENT=FALSE")
        return 2

    d = json.loads(rp.read_text(encoding="utf-8-sig"))
    h2 = d.get("h2") or {}
    pp = d.get("process_probe") or {}
    lp = d.get("log_probe") or {}
    sci = d.get("scientific_boundary") or {}
    mut = d.get("mutation") or {}

    print(f"H1_EVIDENCE={rp}")
    print(f"H2_STATUS={h2.get('status')}")
    print(f"H2_MODULE_MTIME_UTC={h2.get('module_mtime_utc')}")
    print(f"PORTAL_PROCESS_CANDIDATES={len(pp.get('portal_candidates') or [])}")
    print(f"ALL_PORTAL_CANDIDATES_PREDATE_H2={pp.get('all_portal_candidates_predate_h2')}")
    print(f"POST_H2_PORTAL_CANDIDATE_EXISTS={pp.get('post_h2_portal_candidate_exists')}")

    for i, x in enumerate(pp.get("portal_candidates") or [], 1):
        print(
            f"PROCESS_{i} PID={x.get('pid')} CREATED={x.get('created_at_utc')} "
            f"PREDATES_H2={x.get('created_before_h2_module')} NAME={x.get('name')}"
        )

    print(f"EVENT_RAY_LOGS_FOUND={lp.get('found')}")
    for i, x in enumerate(lp.get("logs") or [], 1):
        print(
            f"LOG_{i} PATH={x.get('path')} MTIME={x.get('mtime_utc')} "
            f"BYTES={x.get('bytes')} STARTED={x.get('event_ray_started_seen')} "
            f"H2_EVENT={x.get('h2_event_seen')} RECORDS={x.get('tail_records')}"
        )

    print(f"INCIDENT_000077V4_CAPTURED={sci.get('incident_000077V4_captured')}")
    print(f"FOCUS_ROOT_CAUSE_IDENTIFIED={sci.get('focus_root_cause_identified')}")
    print(f"IME_SUBMIT_ROOT_CAUSE_IDENTIFIED={sci.get('ime_submit_root_cause_identified')}")
    print(f"SCROLL_BACKLASH_ROOT_CAUSE_IDENTIFIED={sci.get('scroll_backlash_root_cause_identified')}")

    print(f"PRODUCTION_SOURCE_MUTATED={mut.get('production_source_mutated')}")
    print(f"RUNNING_PROCESS_MUTATED={mut.get('running_process_mutated')}")
    print(f"EVENT_RAY_LOG_MUTATED={mut.get('event_ray_log_mutated')}")
    print(f"SESSION_PORTAL_RESTARTED={mut.get('session_portal_restarted')}")

    print(f"CLASSIFICATION={d.get('classification')}")
    print(f"NEXT={d.get('next')}")
    print("EVENT_RAY_ACTIVATION_RESULT_RETURN_000077V4H1A_RUN=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
