from pathlib import Path
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
DEV = ROOT / "src/main/shell/vxs/vxs-dev-capabilities.ts"
BOOT = ROOT / "src/main/shell/vxs/vxs-git-bootstrap.ts"
BRIDGE = ROOT / "src/main/shell/vxs/vera-vxs-request-bridge.ts"
RENDERER = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts"

def fail(message: str) -> None:
    print(f"FAIL={message}")
    raise SystemExit(1)

for path in (DEV, BOOT, BRIDGE, RENDERER):
    if not path.exists():
        fail(f"MISSING:{path}")

dev = DEV.read_text(encoding="utf-8", errors="strict")
boot = BOOT.read_text(encoding="utf-8", errors="strict")
bridge = BRIDGE.read_text(encoding="utf-8", errors="strict")
renderer = RENDERER.read_text(encoding="utf-8", errors="strict")

checks = {
    "DEV_MARKER": "VXS_GIT_BOOTSTRAP_000068V3" in dev,
    "DEV_IMPORT": "planVxsGitBootstrap" in dev,
    "DEV_ROUTE": "subcommand === 'bootstrap'" in dev,
    "DEV_HELP": "vxs git bootstrap <vera-01..vera-05> <github-origin-url>" in dev,
    "BOOT_MARKER": "VXS_GIT_BOOTSTRAP_000068V3" in boot,
    "BOOT_AUTO_LEDGER": "auto-authorities.json" in boot,
    "BOOT_AUTO_ACTIVE": "AUTO_AUTHORITY_NOT_ACTIVE" in boot,
    "BOOT_AUTO_EXPIRED": "AUTO_AUTHORITY_EXPIRED" in boot,
    "BOOT_AUTO_SCOPE": "AUTO_AUTHORITY_SESSION_OUT_OF_SCOPE" in boot,
    "BOOT_AUTO_EPOCH": "AUTO_AUTHORITY_EPOCH_CHANGED" in boot,
    "BOOT_REMOTE_EMPTY": "REMOTE_NOT_EMPTY" in boot,
    "BOOT_GITHUB_ONLY": "https://github\\.com/" in boot,
    "BOOT_INIT_MAIN": "@('init', '-b', 'main')" in boot,
    "BOOT_ORIGIN_ADD": "@('remote', 'add', 'origin'" in boot,
    "BOOT_ROOT_VERIFY": "BOOTSTRAP_ROOT_VERIFY_FAILED" in boot,
    "BOOT_BRANCH_VERIFY": "BOOTSTRAP_BRANCH_VERIFY_FAILED" in boot,
    "BOOT_ORIGIN_VERIFY": "BOOTSTRAP_ORIGIN_VERIFY_FAILED" in boot,
    "BOOT_ROLLBACK": "REMOVED_CREATED_GIT_METADATA" in boot,
    "BOOT_SHARED_LOCK": "vxs-git-publish.lock" in boot,
    "BOOT_AUDIT": "vxs-git-bootstrap-audit.jsonl" in boot,
    "BOOT_NO_PUSH": "@('push'" not in boot,
    "BOOT_NO_COMMIT": "@('commit'" not in boot,
    "BOOT_NO_STAGE_ALL": "@('add', '-A')" not in boot,
    "BOOT_NO_FORCE": "--force" not in boot,
    "BRIDGE_ACTION": "'git.publish' | 'git.bootstrap'" in bridge,
    "BRIDGE_BOOTSTRAP_ROUTE": "vxs git bootstrap ${request.origin_session} ${request.remote_url}" in bridge,
    "BRIDGE_REMOTE_REQUIRED": "VXS_REQUEST_REMOTE_URL_REQUIRED" in bridge,
    "BRIDGE_RAW_SHELL_ABSENT": "raw_command" not in bridge.lower(),
    "RENDERER_ACTION": "'git.publish' | 'git.bootstrap'" in renderer,
    "RENDERER_REMOTE_GUARD": "VXS_REQUEST_REMOTE_URL_INVALID" in renderer,
    "RENDERER_TYPED_PREFIX": "vertex-vxs-request:" in renderer,
}

for key, ok in checks.items():
    print(f"{key}={'PASS' if ok else 'FAIL'}")
    if not ok:
        fail(key)

cmd = ["npm.cmd", "run", "typecheck"]
print("RUN=" + " ".join(cmd))
cp = subprocess.run(
    cmd,
    cwd=ROOT,
    text=True,
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    timeout=180,
)
print(f"TYPECHECK_EXIT={cp.returncode}")
if cp.stdout:
    print("STDOUT_TAIL=" + cp.stdout[-12000:])
if cp.stderr:
    print("STDERR_TAIL=" + cp.stderr[-12000:])
if cp.returncode != 0:
    fail("TYPECHECK")

print("PRODUCTION_VERIFY_MUTATION=NONE")
print("GIT_INIT_EXECUTED=NO")
print("GIT_REMOTE_ADD_EXECUTED=NO")
print("GIT_ADD_EXECUTED=NO")
print("GIT_COMMIT_EXECUTED=NO")
print("GIT_PUSH_EXECUTED=NO")
print("VXS_GIT_BOOTSTRAP_000068V3=PASS")
raise SystemExit(0)
