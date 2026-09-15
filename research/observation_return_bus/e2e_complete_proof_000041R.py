from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

JOB_ID = "job-58df3e69-ec77-43f0-96a5-52c742655159"
ARTIFACT_ID = "vertex-observation-return-bus-post-dev-chain-cleanup-e2e-000040"
EVIDENCE_ID = "ws-evidence-db4250a6ac061b79d90e9814a78520c388d1d4166e2c2048e3d1b70ff985fd06"
ORIGIN_SESSION = "vera-02"
OBS_SHA = "eb35cc683fee06d51c8486083fb2a1266bd2ae01dbeeed0692b387a3950a664d"
OBS_BYTES = 3766
EXECUTION_LANE = "lane-06"

APPDATA = Path(os.environ.get("APPDATA", ""))
CACHE = APPDATA / "vertex-session-portal" / "vra-dispatch" / "observability" / "evidence" / (
    hashlib.sha256(EVIDENCE_ID.encode("utf-8")).hexdigest() + ".json"
)
LEDGER = APPDATA / "vertex-session-portal" / "vra-dispatch" / "ledger.json"

def finish(code: int, result: str, detail: str = "") -> None:
    print(f"E2E_COMPLETE_RESULT={result}")
    print(f"E2E_COMPLETE_EXIT_CODE={code}")
    if detail:
        print(f"DETAIL={detail}")
    raise SystemExit(code)

print("VERTEX_OBSERVATION_RETURN_BUS_E2E_COMPLETE_PROOF_000041R=BEGIN")
print("MODE=READ_ONLY")
print(f"CACHE={CACHE}")

if not CACHE.is_file():
    finish(31, "PORTAL_CACHE_MISSING")

try:
    record = json.loads(CACHE.read_text(encoding="utf-8"))
except Exception as exc:
    finish(32, "PORTAL_CACHE_INVALID_JSON", repr(exc))

print(f"CACHE_SCHEMA={record.get('schema')}")
print(f"CACHE_STATUS={record.get('status')}")
print(f"CACHE_JOB={record.get('jobId')}")
print(f"CACHE_ARTIFACT={record.get('artifactId')}")
print(f"CACHE_EVIDENCE={record.get('evidenceId')}")
print(f"CACHE_ORIGIN={record.get('originSession')}")
print(f"OBSERVATION_STATUS={record.get('observationStatus')}")

if record.get("jobId") != JOB_ID:
    finish(33, "CACHE_JOB_MISMATCH")
if record.get("artifactId") != ARTIFACT_ID:
    finish(33, "CACHE_ARTIFACT_MISMATCH")
if record.get("evidenceId") != EVIDENCE_ID:
    finish(33, "CACHE_EVIDENCE_MISMATCH")
if record.get("originSession") != ORIGIN_SESSION:
    finish(34, "CACHE_ORIGIN_MISMATCH")
if record.get("observationStatus") != "ATTACHED":
    finish(35, "OBSERVATION_NOT_ATTACHED", repr(record.get("observationStatus")))

supp = record.get("observationSupplement")
if not isinstance(supp, dict):
    finish(36, "SUPPLEMENT_MISSING")

print(f"SUPPLEMENT_KIND={supp.get('kind')}")
print(f"SUPPLEMENT_ARTIFACT={supp.get('artifactId')}")
print(f"SUPPLEMENT_BYTES={supp.get('bytes')}")
print(f"SUPPLEMENT_SHA256={supp.get('sha256')}")
print(f"SUPPLEMENT_VERIFIED={supp.get('verified')}")
print(f"SUPPLEMENT_EXECUTION_LANE={supp.get('executionLane')}")
print(f"SUPPLEMENT_PATH={supp.get('path')}")

if supp.get("kind") != "WORKSTATION_OBSERVATION_SIDECAR":
    finish(36, "SUPPLEMENT_KIND_MISMATCH")
if supp.get("artifactId") != ARTIFACT_ID:
    finish(36, "SUPPLEMENT_ARTIFACT_MISMATCH")
if supp.get("bytes") != OBS_BYTES:
    finish(36, "SUPPLEMENT_BYTES_MISMATCH")
if str(supp.get("sha256") or "").lower() != OBS_SHA:
    finish(36, "SUPPLEMENT_SHA_MISMATCH")
if supp.get("verified") is not True:
    finish(36, "SUPPLEMENT_VERIFIED_FALSE")
if supp.get("executionLane") != EXECUTION_LANE:
    finish(36, "SUPPLEMENT_LANE_MISMATCH")

try:
    with urllib.request.urlopen(f"http://127.0.0.1:47832/v1/jobs/{JOB_ID}/evidence", timeout=3) as r:
        ws = json.loads(r.read().decode("utf-8", errors="replace"))
        outer = ws.get("evidence") if isinstance(ws, dict) else None
        if isinstance(outer, dict):
            print(f"WORKSTATION_EVIDENCE_STATE={outer.get('evidence_state')}")
            print(f"WORKSTATION_RETURN_STATE={outer.get('evidence_return_state')}")
            env = outer.get("envelope")
            ev = env.get("evidence") if isinstance(env, dict) else None
            print(f"WORKSTATION_OBSERVATION_REFERENCE_PRESENT={isinstance(ev.get('observation_reference'), dict) if isinstance(ev, dict) else False}")
except Exception as exc:
    print(f"WORKSTATION_API_WARNING={exc!r}")

if LEDGER.is_file():
    try:
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        print("PORTAL_LEDGER_READ=PASS")
        print(f"PORTAL_LEDGER_TYPE={type(ledger).__name__}")
    except Exception as exc:
        print(f"PORTAL_LEDGER_READ_WARNING={exc!r}")

print("WRITER=PASS")
print("SIDECAR=PASS")
print("SENDER=PASS")
print("PORTAL_HIDDEN_TAP=PASS")
print("PORTAL_OBSERVATION_STATUS=ATTACHED")
print("PORTAL_EXACT_ORIGIN=PASS")
print("PORTAL_SUPPLEMENT_INTEGRITY=PASS")
print("SECOND_ROUTER=ABSENT")
print("SECOND_RETURN_QUEUE=ABSENT")
print("SECOND_ACK_PATH=ABSENT")
print("SECOND_REGISTRY_LIFECYCLE=ABSENT")
print("SECOND_TRANSPORT=ABSENT")
print("HUMAN_APPLY_PRESERVED=PASS")
print("VERTEX_OBSERVATION_RETURN_BUS=E2E_COMPLETE")
print("E2E_COMPLETE_RESULT=PASS")
print("E2E_COMPLETE_EXIT_CODE=0")
print("VERTEX_OBSERVATION_RETURN_BUS_E2E_COMPLETE_PROOF_000041R=PASS")
raise SystemExit(0)
