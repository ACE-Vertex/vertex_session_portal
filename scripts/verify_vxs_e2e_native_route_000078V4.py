from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "scripts" / "e2e_vxs_native_route_000078V4.ts"
SERVICE = ROOT / "src" / "main" / "shell" / "vertex-shell-service.ts"
REGISTRY = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-command-registry.ts"
RESOLVER = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-provider-resolver.ts"
DESCRIPTOR = ROOT / "runtime" / "vxs" / "native" / "providers" / "vxs-native-observer.json"


def run(args, cwd=ROOT, timeout=240, env=None):
    return subprocess.run(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=timeout,
        env=env,
    )


def fail(stage: str, code: int, proc=None, extra: str = "") -> int:
    print("VXS_E2E_VERIFY=FAIL")
    print("STAGE=" + stage)
    if extra:
        print(extra)
    if proc is not None:
        print("EXIT_CODE=" + str(proc.returncode))
        if proc.stdout:
            print("STDOUT=" + proc.stdout[-16000:].replace("\n", "\\n"))
        if proc.stderr:
            print("STDERR=" + proc.stderr[-16000:].replace("\n", "\\n"))
    return code


for path in (HARNESS, SERVICE, REGISTRY, RESOLVER, DESCRIPTOR):
    if not path.is_file():
        raise SystemExit(fail("FILE_LOOKUP", 20, extra="MISSING=" + str(path)))

# Build first so the current source integration must still be healthy.
npm_cmd = Path(r"C:\Program Files\nodejs\npm.cmd")
npm = str(npm_cmd) if npm_cmd.is_file() else shutil.which("npm")
if not npm:
    raise SystemExit(fail("NPM_LOOKUP", 21))

build = run([npm, "run", "build"], timeout=300)
if build.returncode != 0:
    raise SystemExit(fail("BUILD", 22, proc=build))

# Bundle the dedicated E2E harness against the actual TypeScript source.
node_exe = Path(r"C:\Program Files\nodejs\node.exe")
node = str(node_exe) if node_exe.is_file() else shutil.which("node")
if not node:
    raise SystemExit(fail("NODE_LOOKUP", 23))

esbuild = ROOT / "node_modules" / "esbuild" / "bin" / "esbuild"
if not esbuild.is_file():
    raise SystemExit(fail("ESBUILD_LOOKUP", 24, extra="EXPECTED=" + str(esbuild)))

e2e_root = ROOT / "runtime" / "vxs" / "e2e" / "000078V4"
app_root = e2e_root / "app"
bundle = app_root / "main.cjs"
package_json = app_root / "package.json"

if e2e_root.exists():
    shutil.rmtree(e2e_root, ignore_errors=True)
app_root.mkdir(parents=True, exist_ok=True)

bundle_proc = run([
    node,
    str(esbuild),
    str(HARNESS),
    "--bundle",
    "--platform=node",
    "--format=cjs",
    "--external:electron",
    "--outfile=" + str(bundle),
], timeout=180)

if bundle_proc.returncode != 0 or not bundle.is_file():
    shutil.rmtree(e2e_root, ignore_errors=True)
    raise SystemExit(fail("HARNESS_BUNDLE", 25, proc=bundle_proc))

package_json.write_text(
    json.dumps({
        "name": "vxs-e2e-native-route-smoke",
        "version": "0.0.0-test",
        "main": "main.cjs",
        "private": True,
    }, indent=2),
    encoding="utf-8",
)

electron = ROOT / "node_modules" / "electron" / "dist" / "electron.exe"
if not electron.is_file():
    shutil.rmtree(e2e_root, ignore_errors=True)
    raise SystemExit(fail("ELECTRON_LOOKUP", 26, extra="EXPECTED=" + str(electron)))

env = os.environ.copy()
env["VXS_E2E_ROOT"] = str(ROOT)
env["ELECTRON_DISABLE_SECURITY_WARNINGS"] = "true"

try:
    e2e = run([str(electron), str(app_root)], cwd=ROOT, timeout=120, env=env)
except subprocess.TimeoutExpired:
    shutil.rmtree(e2e_root, ignore_errors=True)
    raise SystemExit(fail("E2E_TIMEOUT", 30))

marker = None
for line in e2e.stdout.splitlines():
    if line.startswith("VXS_E2E_RESULT="):
        marker = line.split("=", 1)[1]

if e2e.returncode != 0:
    shutil.rmtree(e2e_root, ignore_errors=True)
    raise SystemExit(fail("E2E_PROCESS", 31, proc=e2e))

if not marker:
    shutil.rmtree(e2e_root, ignore_errors=True)
    raise SystemExit(fail("E2E_MARKER", 32, proc=e2e))

try:
    report = json.loads(marker)
except Exception as exc:
    shutil.rmtree(e2e_root, ignore_errors=True)
    raise SystemExit(fail("E2E_JSON", 33, extra=f"ERROR={type(exc).__name__}:{exc}"))

if report.get("schema") != "vertex-vxs/e2e-native-route-smoke-1":
    shutil.rmtree(e2e_root, ignore_errors=True)
    raise SystemExit(fail("E2E_SCHEMA", 34))

if report.get("state") != "PASS":
    shutil.rmtree(e2e_root, ignore_errors=True)
    raise SystemExit(fail("E2E_STATE", 35, extra=json.dumps(report, ensure_ascii=False)))

if report.get("path_poisoned") is not True:
    shutil.rmtree(e2e_root, ignore_errors=True)
    raise SystemExit(fail("PATH_POISON_PROOF", 36))

cases = report.get("cases") or []
if len(cases) != 4:
    shutil.rmtree(e2e_root, ignore_errors=True)
    raise SystemExit(fail("CASE_COUNT", 37, extra="FOUND=" + str(len(cases))))

for index, case in enumerate(cases):
    if case.get("exitCode") != 0:
        shutil.rmtree(e2e_root, ignore_errors=True)
        raise SystemExit(fail("CASE_EXIT", 40 + index, extra=json.dumps(case, ensure_ascii=False)))
    if case.get("providerNative") is not True:
        shutil.rmtree(e2e_root, ignore_errors=True)
        raise SystemExit(fail("CASE_PROVIDER", 50 + index, extra=json.dumps(case, ensure_ascii=False)))
    if case.get("nativeSchema") is not True:
        shutil.rmtree(e2e_root, ignore_errors=True)
        raise SystemExit(fail("CASE_NATIVE_SCHEMA", 60 + index, extra=json.dumps(case, ensure_ascii=False)))
    if case.get("routeEvidence") is not True:
        shutil.rmtree(e2e_root, ignore_errors=True)
        raise SystemExit(fail("CASE_ROUTE_EVIDENCE", 70 + index, extra=json.dumps(case, ensure_ascii=False)))

backends = [str(case.get("backend") or "") for case in cases]
organs = [str(case.get("organ") or "") for case in cases]

print("VXS_E2E_VERIFY=PASS")
print("BUILD=PASS")
print("HARNESS_BUNDLE=PASS")
print("ELECTRON_MAIN_PROCESS=PASS")
print("VERTEX_SHELL_SERVICE_EXECUTE=PASS")
print("COMMAND_COUNT=" + str(len(cases)))
print("COMMAND_1=vxs system observe")
print("COMMAND_2=vxs fs exists <package.json>")
print("COMMAND_3=vxs fs meta <package.json>")
print("COMMAND_4=vxs fs list <src/main/shell/vxs>")
print("BACKENDS=" + ";".join(backends))
print("ORGANS=" + ";".join(organs))
print("PROVIDER_NATIVE_ALL=true")
print("NATIVE_SCHEMA_ALL=true")
print("PATH_POISONED=true")
print("PWSH_PATH_AVAILABLE=false")
print("POWERSHELL_FALLBACK_REQUIRED=false")
print("NORMAL_ROUTE_E2E=PASS")

# Test artifacts are disposable.
shutil.rmtree(e2e_root, ignore_errors=True)
raise SystemExit(0)
