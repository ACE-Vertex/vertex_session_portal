from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
WORKSTATION = ROOT.parent / "vertex_workstation"

def emit(v):
    print(str(v).encode("cp932", errors="backslashreplace").decode("cp932", errors="replace"), flush=True)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def snapshot(base):
    if not base.is_dir():
        return {}
    return {
        p.relative_to(base).as_posix(): sha(p)
        for p in sorted(base.rglob("*"))
        if p.is_file()
    }

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
    emit(f"{label}_TAIL=" + (cp.stdout or "")[-9000:].replace("\n", " | "))
    return cp.returncode == 0

def main():
    failures = []
    emit("=== SESSION PORTAL / RAY EVIDENCE PAYLOAD BRIDGE 000082V5 ===")
    emit("PURPOSE=RETURN_BOUNDED_VERIFICATION_BODY_TO_EXACT_VERA")
    emit("WORKSTATION_CONTRACT_MUTATION=ZERO")
    emit("WORKSTATION_PRODUCTION_MUTATION=ZERO")
    emit("HUMAN_GATE=PRESERVED")
    emit("READ_ONLY_EVIDENCE_BODY=YES")
    emit("MAX_EVIDENCE_BODY_BYTES=262144")

    check("SERVICE_PRESENT", SERVICE.is_file(), failures)
    if failures:
        return 2

    text = SERVICE.read_text(encoding="utf-8-sig")

    checks = {
        "BOUNDED_BODY_READER": "readBoundedVerificationEvidenceBody" in text,
        "REALPATH_CANONICALIZATION": "realpathSync" in text,
        "WORKSTATION_LANES_ROOT": "'vertex_workstation', 'runtime', 'lanes'" in text,
        "PATH_ESCAPE_FAIL_CLOSED": "PATH_OUTSIDE_WORKSTATION_LANES" in text,
        "RELATIVE_GUARD": "rel.startsWith('..')" in text and "isAbsolute(rel)" in text,
        "JSON_ONLY": "NON_JSON_EVIDENCE" in text,
        "SIZE_LIMIT_256K": "256 * 1024" in text,
        "READ_ONLY_FILE_READ": "readFileSync(candidate, 'utf8')" in text,
        "RETURN_PAYLOAD_APPENDS_BODY": "verificationBody ? ['', verificationBody]" in text,
        "EXACT_ORIGIN_RETURN_STILL_PRESENT": "EVIDENCE_ORIGIN_ROUTE_MISMATCH" in text,
        "HUMAN_GATE_TEXT_STILL_PRESENT": "Re-execution requires a new HUMAN_APPLY approval." in text,
        "NO_PROCESS_CONTROL": "taskkill" not in text.lower() and "kill(" not in text.lower(),
    }
    for name, ok in checks.items():
        check(name, ok, failures)

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
        emit("VERTEX_SESSION_PORTAL_RAY_EVIDENCE_PAYLOAD_BRIDGE_000082V5=FAIL")
        emit("FAILED=" + ",".join(failures))
        return 1

    emit("VERTEX_SESSION_PORTAL_RAY_EVIDENCE_PAYLOAD_BRIDGE_000082V5=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
