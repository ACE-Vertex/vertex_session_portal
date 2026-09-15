from pathlib import Path
import subprocess
import shutil
import sys

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REMOTE = "https://github.com/ACE-Vertex/vertex_session_portal.git"

def run(args, cwd=None, timeout=60):
    cp = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return cp.returncode, cp.stdout.strip(), cp.stderr.strip()

def fail(message, created_git=False):
    print("BOOTSTRAP_STATUS=FAILED")
    print("DETAIL=" + str(message).replace("\r", " ").replace("\n", " ")[:4000])
    if created_git:
        git_dir = ROOT / ".git"
        try:
            if git_dir.exists():
                shutil.rmtree(git_dir)
                print("ROLLBACK=REMOVED_CREATED_GIT_METADATA")
            else:
                print("ROLLBACK=NOT_NEEDED")
        except Exception as exc:
            print("ROLLBACK=FAILED")
            print("ROLLBACK_DETAIL=" + repr(exc))
    raise SystemExit(1)

print("VERTEX_SESSION_PORTAL_GIT_BOOTSTRAP_000071V3=BEGIN")
print("ROOT=" + str(ROOT))
print("REMOTE=" + REMOTE)

if not ROOT.exists() or not ROOT.is_dir():
    fail("PROJECT_ROOT_NOT_FOUND")

# Remote must still be empty before local bootstrap.
code, stdout, stderr = run(["git", "ls-remote", "--heads", "--tags", REMOTE], timeout=60)
if code != 0:
    fail("REMOTE_PROBE_FAILED: " + (stderr or stdout))
if stdout.strip():
    fail("REMOTE_NOT_EMPTY")

git_dir = ROOT / ".git"
created_git = False

if git_dir.exists():
    # Idempotent validation path only. Do not rewrite an existing repository.
    code, top, err = run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"])
    if code != 0:
        fail("EXISTING_GIT_INVALID: " + (err or top))
    code, branch, err = run(["git", "-C", str(ROOT), "branch", "--show-current"])
    if code != 0:
        fail("EXISTING_BRANCH_READ_FAILED: " + (err or branch))
    code, origin, err = run(["git", "-C", str(ROOT), "remote", "get-url", "origin"])
    if code != 0:
        fail("EXISTING_ORIGIN_MISSING: " + (err or origin))
    if Path(top).resolve() != ROOT.resolve():
        fail("EXISTING_GIT_ROOT_MISMATCH: " + top)
    if branch.strip() != "main":
        fail("EXISTING_BRANCH_NOT_MAIN: " + branch)
    if origin.strip().rstrip("/").lower() != REMOTE.rstrip("/").lower():
        fail("EXISTING_ORIGIN_MISMATCH: " + origin)
    print("BOOTSTRAP_STATUS=ALREADY_CONFIGURED")
    print("GIT_ROOT=" + top)
    print("BRANCH=" + branch)
    print("ORIGIN=" + origin)
    print("GIT_ADD_EXECUTED=NO")
    print("GIT_COMMIT_EXECUTED=NO")
    print("GIT_PUSH_EXECUTED=NO")
    raise SystemExit(0)

code, stdout, stderr = run(["git", "init", "-b", "main"], cwd=ROOT)
if code != 0:
    fail("GIT_INIT_FAILED: " + (stderr or stdout))
created_git = True

code, stdout, stderr = run(["git", "remote", "add", "origin", REMOTE], cwd=ROOT)
if code != 0:
    fail("REMOTE_ADD_FAILED: " + (stderr or stdout), created_git=True)

code, top, err = run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"])
if code != 0:
    fail("ROOT_VERIFY_FAILED: " + (err or top), created_git=True)

code, branch, err = run(["git", "-C", str(ROOT), "branch", "--show-current"])
if code != 0:
    fail("BRANCH_VERIFY_FAILED: " + (err or branch), created_git=True)

code, origin, err = run(["git", "-C", str(ROOT), "remote", "get-url", "origin"])
if code != 0:
    fail("ORIGIN_VERIFY_FAILED: " + (err or origin), created_git=True)

if Path(top).resolve() != ROOT.resolve():
    fail("ROOT_MISMATCH: " + top, created_git=True)
if branch.strip() != "main":
    fail("BRANCH_NOT_MAIN: " + branch, created_git=True)
if origin.strip().rstrip("/").lower() != REMOTE.rstrip("/").lower():
    fail("ORIGIN_MISMATCH: " + origin, created_git=True)

print("BOOTSTRAP_STATUS=SUCCEEDED")
print("GIT_ROOT=" + top)
print("BRANCH=" + branch)
print("ORIGIN=" + origin)
print("REMOTE_EMPTY_CONFIRMED=YES")
print("GIT_ADD_EXECUTED=NO")
print("GIT_COMMIT_EXECUTED=NO")
print("GIT_PUSH_EXECUTED=NO")
print("VERTEX_SESSION_PORTAL_GIT_BOOTSTRAP_000071V3=PASS")
raise SystemExit(0)
