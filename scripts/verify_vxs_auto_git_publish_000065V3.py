from pathlib import Path
import subprocess
import sys

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REG = ROOT / "src/main/shell/vxs/vxs-command-registry.ts"
DEV = ROOT / "src/main/shell/vxs/vxs-dev-capabilities.ts"
PUB = ROOT / "src/main/shell/vxs/vxs-git-auto-publish.ts"

def fail(message: str) -> None:
    print(f"FAIL={message}")
    raise SystemExit(1)

for path in (REG, DEV, PUB):
    if not path.exists():
        fail(f"MISSING:{path}")

reg = REG.read_text(encoding="utf-8", errors="strict")
dev = DEV.read_text(encoding="utf-8", errors="strict")
pub = PUB.read_text(encoding="utf-8", errors="strict")

checks = {
    "REG_MARKER": "// VXS_AUTO_GIT_PUBLISH_000065V3" in reg,
    "DEV_MARKER": "// VXS_AUTO_GIT_PUBLISH_000065V3" in dev,
    "PUB_MARKER": "// VXS_AUTO_GIT_PUBLISH_000065V3" in pub,
    "DEV_IMPORT": "planVxsAutoGitMutation" in dev,
    "DEV_COMMIT": "subcommand === 'commit'" in dev,
    "DEV_PUSH": "subcommand === 'push'" in dev,
    "DEV_PUBLISH": "subcommand === 'publish'" in dev,
    "HELP_PUBLISH": "vxs git publish <vera-01..vera-05> <message>" in dev,
    "AUTO_LEDGER": "auto-authorities.json" in pub,
    "AUTO_LEDGER_SCHEMA": "vertex-session-portal/auto-authority-ledger-1" in pub,
    "AUTO_ACTIVE": "AUTO_AUTHORITY_NOT_ACTIVE" in pub,
    "AUTO_EXPIRED": "AUTO_AUTHORITY_EXPIRED" in pub,
    "AUTO_SCOPE": "AUTO_AUTHORITY_SESSION_OUT_OF_SCOPE" in pub,
    "AUTO_EPOCH": "AUTO_AUTHORITY_EPOCH_CHANGED" in pub,
    "PORTAL_RESTART_SAFE_SOURCE": "app.getPath('userData')" in pub,
    "GITHUB_ONLY": "NON_GITHUB_REMOTE_FORBIDDEN" in pub,
    "NO_FORCE_LITERAL": "--force" not in pub,
    "NO_REMOTE_MUTATION": "remote set-url" not in pub and "remote add" not in pub,
    "DRY_RUN": "'push', '--dry-run'" in pub,
    "REMOTE_VERIFY": "REMOTE_HEAD_VERIFY_FAILED" in pub,
    "REMOTE_DRIFT_GUARD": "REMOTE_HEAD_CHANGED_DURING_OPERATION" in pub,
    "HEAD_DRIFT_GUARD": "HEAD_DRIFT" in pub,
    "WORKTREE_DRIFT_GUARD": "WORKTREE_DRIFT" in pub,
    "CONFLICT_GUARD": "MERGE_CONFLICT_PRESENT" in pub,
    "STAGED_GUARD": "PREEXISTING_STAGED_CHANGES_FORBIDDEN" in pub,
    "SENSITIVE_PATH_GUARD": "SENSITIVE_PATH_STAGED" in pub,
    "INDEX_RECOVERY": "INDEX_RECOVERY" in pub,
    "AUDIT": "vxs-git-publish-audit.jsonl" in pub,
    "LOCK": "vxs-git-publish.lock" in pub,
    "AUTHORITY_RECHECKS": pub.count("Assert-AutoAuthority") >= 4,
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
print("GIT_ADD_EXECUTED=NO")
print("GIT_COMMIT_EXECUTED=NO")
print("GIT_PUSH_EXECUTED=NO")
print("VXS_AUTO_GIT_PUBLISH_000065V3=PASS")
raise SystemExit(0)
