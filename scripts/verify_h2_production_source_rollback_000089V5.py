from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "src" / "main" / "workstation" / "workstation-process-controller.ts"
DISPATCH = ROOT / "src" / "main" / "vra" / "vra-dispatch-service.ts"

EXPECTED_CONTROLLER_SHA = "64867a16c01db0138ca93cc91746224f566b04db71ef5e8ec3c80b657b76490e"
EXPECTED_DISPATCH_SHA = "8c5ba1e625c9bb44dc4ce72993e7f80b7094283cda3f5e72fb4bcd866a2b2653"

def emit(v):
    print(str(v).encode("cp932", errors="backslashreplace").decode("cp932", errors="replace"), flush=True)

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def check(name, ok, failures):
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)

def run(cmd, label, failures, timeout=900):
    emit("RUN_" + label + "=" + " ".join(cmd))
    cp = subprocess.run(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
        timeout=timeout,
    )
    emit(f"{label}_EXIT={cp.returncode}")
    emit(f"{label}_TAIL=" + (cp.stdout or "")[-10000:].replace("\n", " | "))
    if cp.returncode != 0:
        failures.append(label)
    return cp

def main():
    failures = []
    emit("=== SESSION PORTAL H2 PRODUCTION SOURCE ROLLBACK 000089V5 ===")
    emit(f"ROOT={ROOT}")
    emit("RESTORE_CONTROLLER_OWNER=000085V5")
    emit("RESTORE_DISPATCH_OWNER=000082V5")
    emit("H2_BUILD_OUTPUTS_LEFT_IN_PLACE=YES")
    emit("WORKSTATION_SOURCE_MUTATION=ZERO")

    check("CONTROLLER_PRESENT", CONTROLLER.is_file(), failures)
    check("DISPATCH_PRESENT", DISPATCH.is_file(), failures)

    if CONTROLLER.is_file():
        csha = sha256(CONTROLLER)
        ctext = CONTROLLER.read_text(encoding="utf-8")
        emit(f"CONTROLLER_SHA256={csha}")
        check("CONTROLLER_EXACT_PRE_H2_SHA", csha == EXPECTED_CONTROLLER_SHA, failures)
        check("H2_BUNDLED_CONTROLLER_HOOK_REMOVED", "resolveBundledWorkstationRuntime" not in ctext, failures)
        check("000085_RELEASE_EXE_PATH_PRESERVED", "join('release', 'vertex-workstation.exe')" in ctext, failures)
        check("WINDOWS_HIDE_PRESERVED", "windowsHide: true" in ctext, failures)
        check("SHELL_FALSE_PRESERVED", "shell: false" in ctext, failures)
        check("VALIDATED_LEGACY_REPLACE_PRESERVED", "replaceValidatedLegacyListener" in ctext, failures)

    if DISPATCH.is_file():
        dsha = sha256(DISPATCH)
        dtext = DISPATCH.read_text(encoding="utf-8")
        emit(f"DISPATCH_SHA256={dsha}")
        check("DISPATCH_EXACT_PRE_H2_SHA", dsha == EXPECTED_DISPATCH_SHA, failures)
        check("H2_BUNDLED_EVIDENCE_ROOT_REMOVED", "process.resourcesPath, 'workstation-server'" not in dtext, failures)
        check("EVIDENCE_PAYLOAD_BRIDGE_PRESERVED", "VERIFICATION EVIDENCE BODY" in dtext, failures)
        check("WORKSTATION_HTTP_CLIENT_PRESERVED", "WorkstationClient" in dtext, failures)
        check("HUMAN_APPROVAL_CONTRACT_PRESERVED", "humanApproval" in dtext or "human_approval" in dtext, failures)
        check("IMMUTABLE_ORIGIN_CONTRACT_PRESERVED", "originSession" in dtext and "originVera" in dtext, failures)

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        failures.append("NPM_NOT_FOUND")
    else:
        run([npm, "run", "typecheck"], "TYPECHECK", failures)
        run([npm, "run", "build"], "BUILD", failures)

    if failures:
        emit("ROLLBACK_VERIFY=FAIL")
        emit("FAILURES=" + ",".join(failures))
        return 1

    emit("ROLLBACK_VERIFY=PASS")
    emit("VERTEX_SESSION_PORTAL_H2_PRODUCTION_SOURCE_ROLLBACK_000089V5=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
