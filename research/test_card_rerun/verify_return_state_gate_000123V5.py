from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

JOB_ID = 'job-vera05-test-card-redispatch-roundtrip-770e76a6-a4e4-482e-8f57-96779ca0b5f9'
ARTIFACT_ID = 'vertex-session-portal-test-card-redispatch-roundtrip-smoke-000121V5'
BASE = "http://127.0.0.1:47832"

def get_json(url: str):
    try:
        with urllib.request.urlopen(url, timeout=2.5) as r:
            return r.status, json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None

def deep(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur

print("VERTEX_RETURN_STATE_GATE_000123V5=BEGIN")
print("MODE=READ_ONLY")
print("TARGET_JOB_ID=" + JOB_ID)

appdata = os.environ.get("APPDATA")
portal_meta = None
meta_path = None
if appdata:
    root = Path(appdata) / "vertex-session-portal" / "vra-dispatch"
    if root.exists():
        hits = []
        for p in root.glob("*.meta.json"):
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(obj, dict) and obj.get("job_id") == JOB_ID:
                hits.append((p, obj))
        if len(hits) == 1:
            meta_path, portal_meta = hits[0]
        elif len(hits) > 1:
            print("CLASSIFICATION=PORTAL_META_DUPLICATE")
            sys.exit(25)

job_status, job_json = get_json(f"{BASE}/v1/jobs/{JOB_ID}")
evidence_status, evidence_json = get_json(f"{BASE}/v1/jobs/{JOB_ID}/evidence")

ws_return = (
    deep(evidence_json, "evidence", "evidence_return_state")
    or deep(evidence_json, "evidence_return_state")
)
ws_returned_at = (
    deep(evidence_json, "evidence", "evidence_returned_at")
    or deep(evidence_json, "evidence_returned_at")
)
ws_artifact = (
    deep(job_json, "job", "artifact_id")
    or deep(job_json, "artifact_id")
    or deep(job_json, "job", "record", "artifact_id")
)
portal_return = portal_meta.get("workstation_evidence_return_state") if portal_meta else None
portal_kind = portal_meta.get("card_kind") if portal_meta else None
portal_artifact = portal_meta.get("artifact_id") if portal_meta else None

print(f"WORKSTATION_JOB_HTTP={job_status}")
print(f"WORKSTATION_EVIDENCE_HTTP={evidence_status}")
print(f"WORKSTATION_ARTIFACT_ID={ws_artifact}")
print(f"WORKSTATION_RETURN_STATE={ws_return}")
print(f"WORKSTATION_RETURNED_AT={ws_returned_at}")
print(f"PORTAL_META_PATH={meta_path}")
print(f"PORTAL_CARD_KIND={portal_kind}")
print(f"PORTAL_ARTIFACT_ID={portal_artifact}")
print(f"PORTAL_RETURN_STATE={portal_return}")
print("MUTATING_HTTP=ZERO")
print("ACK_EXECUTED=NO")
print("RERUN_EXECUTED=NO")

if job_status is None or evidence_status is None:
    print("CLASSIFICATION=WORKSTATION_OFFLINE_OR_UNREACHABLE")
    sys.exit(23)

if ws_artifact not in (None, ARTIFACT_ID) or portal_artifact not in (None, ARTIFACT_ID):
    print("CLASSIFICATION=IDENTITY_MISMATCH_FAIL_CLOSED")
    sys.exit(26)

if portal_kind != "TEST":
    print("CLASSIFICATION=TEST_IDENTITY_NOT_DURABLE")
    sys.exit(27)

if ws_return == "RETURNED" and portal_return == "RETURNED":
    print("CLASSIFICATION=READY_FOR_TEST_RERUN_UI_CHECK")
    print("VERTEX_RETURN_STATE_GATE_000123V5=PASS")
    sys.exit(0)

if ws_return == "RETURNED" and portal_return != "RETURNED":
    print("CLASSIFICATION=WORKSTATION_RETURNED_PORTAL_RECONCILIATION_PENDING")
    sys.exit(21)

if ws_return == "RETURN_QUEUED":
    print("CLASSIFICATION=PORTAL_ACK_STILL_REQUIRED")
    sys.exit(22)

print("CLASSIFICATION=UNEXPECTED_RETURN_STATE")
sys.exit(24)
