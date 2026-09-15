from __future__ import annotations

from pathlib import Path
import json
import re
import subprocess
import urllib.error
import urllib.request

JOB_ID = 'job-vera05-session-portal-final-ux-wordmark-autofit-000073V5'
ARTIFACT_ID = 'vertex-session-portal-final-ux-wordmark-autofit-000073V5'
BASE = "http://127.0.0.1:47832"
DEV_ROOT = Path(r"G:\Vertex_Project\Development")
WORKSTATION = DEV_ROOT / "vertex_workstation"
INCOMING = DEV_ROOT / "_incoming"
VRA = INCOMING / f"{ARTIFACT_ID}.vra"
META = INCOMING / f"{ARTIFACT_ID}.vra.meta.json"
REGISTRY = WORKSTATION / "runtime" / "headless" / "job-registry"

def emit(k, v):
    if isinstance(v, (dict, list)):
        v = json.dumps(v, ensure_ascii=False, sort_keys=True)
    text = f"{k}={v}"
    print(text.encode("cp932", errors="backslashreplace").decode("cp932", errors="replace"), flush=True)

def http_get(path):
    url = BASE + path
    try:
        with urllib.request.urlopen(url, timeout=3.0) as r:
            body = r.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = body
            return r.status, parsed
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return e.code, parsed
    except Exception as e:
        return 0, f"{type(e).__name__}:{e}"

def powershell(script):
    cmd = [
        "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-Command", script
    ]
    try:
        cp = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
        return cp.returncode, (cp.stdout or "").strip(), (cp.stderr or "").strip()
    except Exception as e:
        return 999, "", f"{type(e).__name__}:{e}"

def newest_registry():
    if not REGISTRY.is_dir():
        return None, None
    files = sorted(
        REGISTRY.glob("*.json"),
        key=lambda p: p.stat().st_mtime_ns,
        reverse=True,
    )
    for path in files[:20]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        return path, data
    return None, None

def search_runtime_job():
    runtime = WORKSTATION / "runtime" / "headless"
    hits = []
    if not runtime.is_dir():
        return hits
    for p in runtime.rglob("*.json"):
        try:
            if p.stat().st_size > 8 * 1024 * 1024:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if JOB_ID in text or ARTIFACT_ID in text:
            hits.append(str(p))
            if len(hits) >= 20:
                break
    return hits

print("=== VERTEX WORKSTATION READ-ONLY DISPATCH PIPELINE PROBE 000074V5 ===")
emit("MUTATION", "ZERO")
emit("JOB_ID", JOB_ID)
emit("ARTIFACT_ID", ARTIFACT_ID)

# Listener + process identity
rc, stdout, stderr = powershell(
    "$c=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 47832 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1;"
    "if($null -eq $c){'NO_LISTENER';exit 0};"
    "$p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$c.OwningProcess);"
    "[pscustomobject]@{Pid=$c.OwningProcess;ExecutablePath=$p.ExecutablePath;CommandLine=$p.CommandLine} | ConvertTo-Json -Compress"
)
emit("LISTENER_PS_EXIT", rc)
emit("LISTENER", stdout if stdout else "NONE")
if stderr:
    emit("LISTENER_STDERR", stderr)

# HTTP control plane
health_status, health = http_get("/v1/health")
safety_status, safety = http_get("/v1/safety")
job_status, job = http_get(f"/v1/jobs/{JOB_ID}")
evidence_status, evidence = http_get(f"/v1/jobs/{JOB_ID}/evidence")
emit("HEALTH_HTTP", health_status)
emit("HEALTH", health)
emit("SAFETY_HTTP", safety_status)
emit("SAFETY", safety)
emit("JOB_HTTP", job_status)
emit("JOB", job)
emit("EVIDENCE_HTTP", evidence_status)
emit("EVIDENCE", evidence)

# Filesystem publication boundary
emit("INCOMING_VRA_EXISTS", VRA.is_file())
emit("INCOMING_META_EXISTS", META.is_file())
if VRA.is_file():
    emit("INCOMING_VRA_SIZE", VRA.stat().st_size)
if META.is_file():
    try:
        meta = json.loads(META.read_text(encoding="utf-8"))
        emit("INCOMING_META", meta)
    except Exception as e:
        emit("INCOMING_META_PARSE_ERROR", f"{type(e).__name__}:{e}")

# Persistent registry
reg_path, reg = newest_registry()
emit("REGISTRY_FILE", str(reg_path) if reg_path else "NONE")
registry_job = None
if isinstance(reg, dict):
    jobs = reg.get("jobs")
    if isinstance(jobs, dict):
        registry_job = jobs.get(JOB_ID)
emit("REGISTRY_JOB_PRESENT", registry_job is not None)
if registry_job is not None:
    emit("REGISTRY_JOB", registry_job)

# Other durable runtime evidence mentioning this job
hits = search_runtime_job()
emit("RUNTIME_JOB_HIT_COUNT", len(hits))
for i, hit in enumerate(hits):
    emit(f"RUNTIME_JOB_HIT_{i+1}", hit)

# Deterministic classification
safety_state = None
if isinstance(safety, dict):
    s = safety.get("safety", safety)
    if isinstance(s, dict):
        safety_state = s.get("state")

job_obj = None
if isinstance(job, dict):
    j = job.get("job")
    if isinstance(j, dict):
        job_obj = j

job_state = job_obj.get("state") if isinstance(job_obj, dict) else None
lane = None
if isinstance(job_obj, dict):
    lane = job_obj.get("execution_lane") or job_obj.get("allocated_lane")

classification = "UNRESOLVED"
if health_status == 0:
    classification = "WORKSTATION_CONTROL_PLANE_OFFLINE"
elif safety_state and str(safety_state).upper() != "RUNNING":
    classification = f"SAFETY_BLOCKED_{str(safety_state).upper()}"
elif VRA.is_file() and META.is_file() and job_status == 404:
    classification = "PUBLISHED_TO_INCOMING_BUT_NOT_REGISTERED"
elif job_status == 200 and not lane and str(job_state).upper() in {"REGISTERED","DISPATCHED"}:
    classification = "REGISTERED_BUT_NOT_ALLOCATED"
elif job_status == 200 and str(job_state).upper() == "EXECUTING":
    classification = "EXECUTING"
elif evidence_status == 200:
    classification = "EVIDENCE_AVAILABLE_OR_RETURNABLE"
elif job_status == 200:
    classification = f"JOB_STATE_{job_state}"
elif not VRA.is_file():
    classification = "PORTAL_PUBLISH_NOT_OBSERVED"

emit("CLASSIFICATION", classification)
emit("READ_ONLY_PROBE_000074V5", "PASS")
