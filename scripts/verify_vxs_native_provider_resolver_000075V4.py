from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
NATIVE_PROVIDER = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-native-organ-provider.ts"
RESOLVER = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-provider-resolver.ts"
DESCRIPTOR = ROOT / "runtime" / "vxs" / "native" / "providers" / "vxs-native-observer.json"


def run(args, timeout=180):
    return subprocess.run(
        args,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=timeout,
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


for path in (NATIVE_PROVIDER, RESOLVER, DESCRIPTOR):
    if not path.is_file():
        print("VXS_WIRING=FAIL")
        print("STAGE=FILE_LOOKUP")
        print("MISSING=" + str(path))
        raise SystemExit(20)

try:
    descriptor = json.loads(DESCRIPTOR.read_text(encoding="utf-8-sig"))
except Exception as exc:
    print("VXS_WIRING=FAIL")
    print("STAGE=DESCRIPTOR_PARSE")
    print("ERROR=" + type(exc).__name__ + ":" + str(exc))
    raise SystemExit(21)

if descriptor.get("schema") != "vertex-vxs/native-provider-binding-1":
    print("VXS_WIRING=FAIL")
    print("STAGE=DESCRIPTOR_SCHEMA")
    raise SystemExit(22)

binary = Path(str((descriptor.get("binary") or {}).get("path") or ""))
if not binary.is_absolute():
    binary = ROOT / binary

if not binary.is_file():
    print("VXS_WIRING=FAIL")
    print("STAGE=BINARY_LOOKUP")
    print("EXPECTED=" + str(binary))
    raise SystemExit(23)

expected_sha = str((descriptor.get("binary") or {}).get("sha256") or "").lower()
actual_sha = sha256_file(binary)
if actual_sha != expected_sha:
    print("VXS_WIRING=FAIL")
    print("STAGE=BINARY_HASH")
    print("EXPECTED=" + expected_sha)
    print("ACTUAL=" + actual_sha)
    raise SystemExit(24)

provider_text = NATIVE_PROVIDER.read_text(encoding="utf-8")
resolver_text = RESOLVER.read_text(encoding="utf-8")

required_provider_tokens = [
    "vertex-vxs/native-provider-binding-1",
    "BINARY_HASH_MISMATCH",
    "CAPABILITY_UNSUPPORTED",
    "spawn(",
    "shell: false",
]
required_resolver_tokens = [
    "HUMAN_APPLY_REQUIRED",
    "route: 'NATIVE'",
    "route: 'POWERSHELL'",
    "powerShellFallback",
]

for token in required_provider_tokens:
    if token not in provider_text:
        print("VXS_WIRING=FAIL")
        print("STAGE=PROVIDER_STATIC_CONTRACT")
        print("MISSING_TOKEN=" + token)
        raise SystemExit(25)

for token in required_resolver_tokens:
    if token not in resolver_text:
        print("VXS_WIRING=FAIL")
        print("STAGE=RESOLVER_STATIC_CONTRACT")
        print("MISSING_TOKEN=" + token)
        raise SystemExit(26)

# Native permanent route smoke. No PowerShell involved.
system_proc = run([str(binary), "system"], timeout=30)
if system_proc.returncode != 0 or '"organ":"system"' not in system_proc.stdout:
    print("VXS_WIRING=FAIL")
    print("STAGE=NATIVE_SYSTEM_SMOKE")
    raise SystemExit(40)

fs_proc = run([str(binary), "fs-exists", str(NATIVE_PROVIDER)], timeout=30)
if fs_proc.returncode != 0 or '"organ":"filesystem"' not in fs_proc.stdout:
    print("VXS_WIRING=FAIL")
    print("STAGE=NATIVE_FILESYSTEM_SMOKE")
    raise SystemExit(41)

# Existing project must still typecheck/build after the resolver layer is installed.
npm_cmd = Path(r"C:\Program Files\nodejs\npm.cmd")
npm = str(npm_cmd) if npm_cmd.is_file() else shutil.which("npm")
if not npm:
    print("VXS_WIRING=FAIL")
    print("STAGE=NPM_LOOKUP")
    raise SystemExit(60)

typecheck = run([npm, "run", "typecheck"])
if typecheck.returncode != 0:
    print("VXS_WIRING=FAIL")
    print("STAGE=TYPECHECK")
    print("EXIT_CODE=" + str(typecheck.returncode))
    if typecheck.stdout:
        print("STDOUT=" + typecheck.stdout[-10000:].replace("\n", "\\n"))
    if typecheck.stderr:
        print("STDERR=" + typecheck.stderr[-10000:].replace("\n", "\\n"))
    raise SystemExit(61)

build = run([npm, "run", "build"], timeout=240)
if build.returncode != 0:
    print("VXS_WIRING=FAIL")
    print("STAGE=BUILD")
    print("EXIT_CODE=" + str(build.returncode))
    if build.stdout:
        print("STDOUT=" + build.stdout[-10000:].replace("\n", "\\n"))
    if build.stderr:
        print("STDERR=" + build.stderr[-10000:].replace("\n", "\\n"))
    raise SystemExit(62)

print("VXS_WIRING=PASS")
print("NATIVE_PROVIDER=" + str(NATIVE_PROVIDER))
print("RESOLVER=" + str(RESOLVER))
print("DESCRIPTOR=" + str(DESCRIPTOR))
print("BINARY=" + str(binary))
print("BINARY_SHA256=" + actual_sha)
print("NATIVE_SYSTEM_SMOKE=PASS")
print("NATIVE_FILESYSTEM_SMOKE=PASS")
print("TYPECHECK=PASS")
print("BUILD=PASS")
print("ROUTING=NATIVE_FIRST_POWER_SHELL_FALLBACK")
print("HUMAN_APPLY_AUTO_EXECUTION=BLOCKED")
print("POWERSHELL_USED_BY_SMOKE=false")
raise SystemExit(0)
