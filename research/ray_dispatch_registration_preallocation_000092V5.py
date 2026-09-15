from __future__ import annotations

from pathlib import Path
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
WORKSTATION = Path(r"G:\Vertex_Project\Development\vertex_workstation")
INCOMING = Path(r"G:\Vertex_Project\Development\_incoming")
TARGET_ARTIFACT = "vertex-session-portal-observability-core-foundation-000091V5H1R3"
PORT = 47832

PORTAL_SOURCE = [
    PORTAL / "src/main/vra/vra-dispatch-service.ts",
    PORTAL / "src/main/ipc/register-vra-dispatch-ipc.ts",
    PORTAL / "src/main/workstation/workstation-client.ts",
    PORTAL / "src/main/workstation/workstation-process-controller.ts",
    PORTAL / "src/shared/contracts.ts",
]

WORKSTATION_SOURCE = [
    WORKSTATION / "headless/src/main.rs",
    WORKSTATION / "headless/src/server_adapter.rs",
    WORKSTATION / "headless/src/job_api.rs",
    WORKSTATION / "headless/src/persistent_job_registry.rs",
    WORKSTATION / "headless/src/core_bridge.rs",
    WORKSTATION / "src-tauri/src/manifest_gate.rs",
    WORKSTATION / "src-tauri/src/work_dispatcher.rs",
    WORKSTATION / "src-tauri/src/lane_scheduler.rs",
    WORKSTATION / "src-tauri/src/lane_manager.rs",
]

TEXT_EXT = {
    ".json", ".txt", ".log", ".md", ".pending", ".state", ".meta", ".sidecar",
    ".ts", ".rs", ".toml"
}
MAX_FILE = 2 * 1024 * 1024
MAX_FILES = 25_000

def safe_text(path: Path) -> str | None:
    try:
        if not path.is_file():
            return None
        if path.stat().st_size > MAX_FILE:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

def print_block(label: str, path: Path, needles: list[str], context: int = 3) -> None:
    text = safe_text(path)
    if text is None:
        print(f"SOURCE={label}|MISSING_OR_UNREADABLE|{path}")
        return
    lines = text.splitlines()
    hits: list[int] = []
    for i, line in enumerate(lines):
        low = line.lower()
        if any(n.lower() in low for n in needles):
            hits.append(i)
    print(f"SOURCE={label}|FILE={path}|HITS={len(hits)}")
    emitted = set()
    for hit in hits[:30]:
        lo = max(0, hit - context)
        hi = min(len(lines), hit + context + 1)
        key = (lo, hi)
        if key in emitted:
            continue
        emitted.add(key)
        print(f"--- {label}:L{lo+1}-L{hi} ---")
        for idx in range(lo, hi):
            print(f"{idx+1:05d}: {lines[idx][:500]}")

def bounded_search(root: Path, needle: str, skip: set[str]) -> list[tuple[Path, str]]:
    results: list[tuple[Path, str]] = []
    seen = 0
    if not root.exists():
        return results
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            seen += 1
            if seen > MAX_FILES:
                return results
            path = Path(base) / name
            if path.suffix.lower() not in TEXT_EXT and "metadata" not in name.lower() and "evidence" not in name.lower():
                continue
            text = safe_text(path)
            if text is None or needle not in text:
                continue
            # bounded compact excerpt around first hit
            pos = text.find(needle)
            lo = max(0, pos - 900)
            hi = min(len(text), pos + len(needle) + 2200)
            results.append((path, text[lo:hi]))
            if len(results) >= 80:
                return results
    return results

def json_candidates(hits: list[tuple[Path, str]]) -> list[tuple[Path, dict[str, Any]]]:
    out: list[tuple[Path, dict[str, Any]]] = []
    for path, _ in hits:
        text = safe_text(path)
        if text is None:
            continue
        try:
            data = json.loads(text)
        except Exception:
            continue
        if isinstance(data, dict):
            out.append((path, data))
    return out

def deep_find(obj: Any, names: set[str]) -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    queue: list[tuple[str, Any]] = [("$", obj)]
    seen = 0
    while queue and seen < 5000:
        p, cur = queue.pop(0)
        seen += 1
        if isinstance(cur, dict):
            for k, v in cur.items():
                np = f"{p}.{k}"
                if k in names:
                    found.append((np, v))
                if isinstance(v, (dict, list)):
                    queue.append((np, v))
        elif isinstance(cur, list):
            for i, v in enumerate(cur[:500]):
                if isinstance(v, (dict, list)):
                    queue.append((f"{p}[{i}]", v))
    return found

def http_get(path: str) -> tuple[int | None, str]:
    url = f"http://127.0.0.1:{PORT}{path}"
    try:
        with urllib.request.urlopen(url, timeout=2.0) as response:
            body = response.read(512 * 1024).decode("utf-8", errors="replace")
            return int(response.status), body
    except urllib.error.HTTPError as exc:
        body = exc.read(512 * 1024).decode("utf-8", errors="replace")
        return int(exc.code), body
    except Exception as exc:
        return None, f"{type(exc).__name__}:{exc}"

def extract_job_ids(text: str) -> list[str]:
    return sorted(set(re.findall(r"\bjob-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text, re.I)))

def classify(
    incoming_present: bool,
    job_id: str | None,
    registration_values: list[Any],
    last_errors: list[Any],
    allocated_values: list[Any],
    http_job_status: int | None,
) -> tuple[str, str]:
    reg = " ".join(str(x) for x in registration_values if x is not None).upper()
    errors = " | ".join(str(x) for x in last_errors if x)
    allocated = [x for x in allocated_values if x not in (None, "", "NOT ALLOCATED")]

    if not incoming_present:
        return "PORTAL_ATOMIC_PUBLISH_OR_COMMIT_BOUNDARY", "Target VRA was not found in _incoming."
    if "BLOCKED" in reg or errors:
        return "PORTAL_HTTP_REGISTRATION_OR_WORKSTATION_REJECTION", errors or f"registration={reg}"
    if job_id and http_job_status == 404:
        return "WORKSTATION_JOB_REGISTRATION_NOT_DURABLE", "Portal has job identity but Workstation GET returned 404."
    if job_id and http_job_status is None:
        return "WORKSTATION_CONTROL_PLANE_UNAVAILABLE_OR_GET_FAILED", "Could not query the local Workstation job endpoint."
    if job_id and http_job_status == 200 and not allocated:
        return "WORKSTATION_REGISTERED_PRE_ALLOCATION", "Job is visible to Workstation but no allocated lane fact was found."
    if allocated:
        return "POST_ALLOCATION_FAILURE", f"allocated={allocated}"
    if incoming_present and not job_id:
        return "AFTER_PUBLISH_BEFORE_JOB_IDENTITY_RECOVERY", "Committed VRA exists but no durable job id was recovered from searched state."
    return "UNRESOLVED_PRE_ALLOCATION_BOUNDARY", f"registration={reg} errors={errors}"

def main() -> int:
    print("=== VERTEX RAY / DISPATCH -> REGISTRATION -> PRE-ALLOCATION 000092V5 ===")
    print(f"TARGET_ARTIFACT={TARGET_ARTIFACT}")
    print("MODE=READ_ONLY")
    print("PRODUCTION_MUTATION=NONE")
    print("HTTP_METHODS=GET_ONLY")
    print("NO_DOM_SCRAPE=TRUE")
    print()

    print("=== A. PORTAL SOURCE CONTROL PATH ===")
    for p in PORTAL_SOURCE:
        print_block(
            "PORTAL",
            p,
            [
                "publishToIncomingAtomic", "publishIncomingCommitSidecar",
                "reconcileWorkstationCard", "registerJob(", "workstationLastError",
                "workstationRegistration", "WorkstationHttpError", "jsonRequest(",
                "artifact_sha256", "humanApproval", "allocatedLane"
            ],
        )

    print()
    print("=== B. WORKSTATION INTAKE / REGISTRY / SCHEDULER PATH ===")
    for p in WORKSTATION_SOURCE:
        print_block(
            "WORKSTATION",
            p,
            [
                "post", "/v1/jobs", "register", "artifact_sha256", "human_approval",
                "origin_session", "incoming", "manifest", "scheduler", "allocate",
                "allocated_lane", "reject", "conflict", "statuscode", "bad_request"
            ],
        )

    print()
    print("=== C. TARGET ARTIFACT DURABLE TRACE ===")
    skip_portal = {".git", "node_modules", "out", "dist", "target"}
    skip_ws = {".git", "node_modules", "target", "ui"}

    portal_hits = bounded_search(PORTAL, TARGET_ARTIFACT, skip_portal)
    incoming_hits = bounded_search(INCOMING, TARGET_ARTIFACT, set())
    workstation_hits = bounded_search(WORKSTATION / "runtime", TARGET_ARTIFACT, skip_ws)

    print(f"PORTAL_HITS={len(portal_hits)}")
    for path, excerpt in portal_hits[:20]:
        print(f"PORTAL_HIT={path}")
        print(excerpt[:3200])

    print(f"INCOMING_HITS={len(incoming_hits)}")
    for path, excerpt in incoming_hits[:20]:
        print(f"INCOMING_HIT={path}")
        print(excerpt[:3200])

    print(f"WORKSTATION_RUNTIME_HITS={len(workstation_hits)}")
    for path, excerpt in workstation_hits[:30]:
        print(f"WORKSTATION_HIT={path}")
        print(excerpt[:3200])

    incoming_present = any(path.suffix.lower() == ".vra" or TARGET_ARTIFACT in path.name for path, _ in incoming_hits)
    print(f"INCOMING_COMMITTED={'YES' if incoming_present else 'NO'}")

    all_text = "\n".join(
        excerpt for _, excerpt in portal_hits + incoming_hits + workstation_hits
    )
    jobs = extract_job_ids(all_text)
    print(f"DISCOVERED_JOB_IDS={len(jobs)}")
    for job in jobs[:20]:
        print(f"JOB_ID={job}")

    print()
    print("=== D. DURABLE STATE FIELDS ===")
    jsons = json_candidates(portal_hits + workstation_hits)
    field_names = {
        "workstation_registration", "workstationRegistration",
        "workstation_last_error", "workstationLastError",
        "workstation_job_state", "workstationJobState",
        "allocated_lane", "allocatedLane",
        "job_id", "jobId",
        "human_approval", "humanApproval",
        "dispatch_phase", "dispatchPhase",
        "status",
    }
    registration_values: list[Any] = []
    last_errors: list[Any] = []
    allocated_values: list[Any] = []
    json_job_ids: list[str] = []

    for path, data in jsons:
        fields = deep_find(data, field_names)
        if not fields:
            continue
        print(f"STATE_FILE={path}")
        for key, value in fields[:80]:
            print(f"STATE={key}={value}")
            lk = key.lower()
            if "workstation_registration" in lk or "workstationregistration" in lk:
                registration_values.append(value)
            if "workstation_last_error" in lk or "workstationlasterror" in lk:
                last_errors.append(value)
            if "allocated_lane" in lk or "allocatedlane" in lk:
                allocated_values.append(value)
            if lk.endswith(".job_id") or lk.endswith(".jobid"):
                if isinstance(value, str) and value.startswith("job-"):
                    json_job_ids.append(value)

    candidate_jobs = list(dict.fromkeys(json_job_ids + jobs))
    job_id = candidate_jobs[0] if candidate_jobs else None

    print()
    print("=== E. LOCAL WORKSTATION GET PROBE ===")
    health_status, health_body = http_get("/v1/health")
    print(f"HEALTH_STATUS={health_status}")
    print(f"HEALTH_BODY={health_body[:4000]}")

    job_status: int | None = None
    if job_id:
        job_status, job_body = http_get(f"/v1/jobs/{job_id}")
        print(f"JOB_GET_ID={job_id}")
        print(f"JOB_GET_STATUS={job_status}")
        print(f"JOB_GET_BODY={job_body[:8000]}")
    else:
        print("JOB_GET=SKIPPED_NO_DURABLE_JOB_ID")

    print()
    print("=== F. RAY VERDICT ===")
    stage, reason = classify(
        incoming_present=incoming_present,
        job_id=job_id,
        registration_values=registration_values,
        last_errors=last_errors,
        allocated_values=allocated_values,
        http_job_status=job_status,
    )
    print(f"FAILURE_BOUNDARY={stage}")
    print(f"REASON={reason}")
    print(f"INCOMING_COMMITTED={incoming_present}")
    print(f"JOB_ID={job_id}")
    print(f"WORKSTATION_JOB_GET={job_status}")
    print(f"REGISTRATION_VALUES={registration_values}")
    print(f"LAST_ERRORS={last_errors}")
    print(f"ALLOCATED_VALUES={allocated_values}")
    print()
    print("RAY_COMPLETED=PASS")
    print("NOTE=Finding a failure is a successful Ray observation and does not fail VERIFY.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
