from pathlib import Path
import hashlib
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = PORTAL / "src/main/shell/vertex-shell-service.ts"
EXPECTED_SHA = "90e08991e40f77c86b1ff7b9c6605e4c3b3e186f145cea2982e4e2a245eba2a0"

failures = []

def ck(name, ok, detail=""):
    print(name + "=" + ("PASS" if ok else "FAIL") + ((" " + detail) if detail else ""))
    if not ok:
        failures.append(name)

ck("SERVICE_PRESENT", SERVICE.is_file())
text = SERVICE.read_text(encoding="utf-8") if SERVICE.is_file() else ""
sha = hashlib.sha256(SERVICE.read_bytes()).hexdigest() if SERVICE.is_file() else ""

ck("POST_PATCH_SHA", sha == EXPECTED_SHA, sha)
ck("MARKER", "VXS_BARE_HELP_ALIAS_000030" in text)
ck("BARE_VERSION_PRESERVED", "^(?:vxs\\s+)?--version$" in text)
ck("HELP_ALIAS_EXACT", "const vxsRegistryCommand = /^--help$/i.test(command)" in text)
ck("HELP_CANONICAL_TARGET", "? 'vxs --help'" in text)
ck("REGISTRY_USES_ALIAS", "executeVxsCommand(\n      vxsRegistryCommand," in text)
ck("ORIGINAL_COMMAND_HISTORY", "command: redactCommand(command)" in text)
ck("CLIPBOARD_000029_PRESERVED", "VXS_CLIPBOARD_OWNERSHIP_REPAIR_000029" in text)

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

cp = subprocess.run(
    ["npm.cmd", "run", "typecheck"],
    cwd=PORTAL,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=180,
)
print("TYPECHECK_EXIT=" + str(cp.returncode))
if cp.stdout:
    print("TYPECHECK_STDOUT_TAIL=" + " | ".join(cp.stdout.splitlines()[-20:]))
if cp.stderr:
    print("TYPECHECK_STDERR_TAIL=" + " | ".join(cp.stderr.splitlines()[-20:]))

if cp.returncode != 0:
    raise SystemExit(cp.returncode)

print("VXS_BARE_HELP_ALIAS_000030=PASS")
raise SystemExit(0)
