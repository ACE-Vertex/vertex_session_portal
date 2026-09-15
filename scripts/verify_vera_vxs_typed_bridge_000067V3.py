from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
DISPATCH = ROOT / "src/main/vra/vra-dispatch-service.ts"
RENDERER = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts"
BRIDGE = ROOT / "src/main/shell/vxs/vera-vxs-request-bridge.ts"
GIT = ROOT / "src/main/shell/vxs/vxs-git-auto-publish.ts"


def fail(code: str) -> None:
    print(f"FAIL={code}")
    raise SystemExit(1)


for path in (DISPATCH, RENDERER, BRIDGE, GIT):
    if not path.exists():
        fail(f"MISSING:{path}")

texts = {
    "dispatch": DISPATCH.read_text(encoding="utf-8", errors="strict"),
    "renderer": RENDERER.read_text(encoding="utf-8", errors="strict"),
    "bridge": BRIDGE.read_text(encoding="utf-8", errors="strict"),
    "git": GIT.read_text(encoding="utf-8", errors="strict"),
}

checks = {
    "DISPATCH_TYPED_TUNNEL": "VXS_REQUEST_COMMAND_PREFIX = 'vertex-vxs-request:'" in texts["dispatch"],
    "DISPATCH_BRIDGE_CALL": "dispatchVeraVxsRequest(cardId.slice(VXS_REQUEST_COMMAND_PREFIX.length))" in texts["dispatch"],
    "RENDERER_REQUEST_SCHEMA": "schema: 'vertex-vxs-request/1'" in texts["renderer"],
    "RENDERER_RESULT_SCHEMA": "schema: 'vertex-vxs-result/1'" in texts["renderer"],
    "RENDERER_AUTO_ONLY": "authorityForSession(source) !== null" in texts["renderer"],
    "RENDERER_BASELINE": "seedVxsRequestBaselines(authority.allowed_sessions)" in texts["renderer"],
    "RENDERER_STABLE_POLLS": "vxsRequestStable" in texts["renderer"] and "STABLE_POLLS_REQUIRED" in texts["renderer"],
    "RENDERER_RESULT_RETURN": "Result is queued back to the originating VERA." in texts["renderer"],
    "BRIDGE_MARKER": "VERA_TO_VXS_TYPED_BRIDGE_000067V3" in texts["bridge"],
    "BRIDGE_TYPED_ACTION_ONLY": "row.action !== 'git.publish'" in texts["bridge"],
    "BRIDGE_VXS_ONLY": "vxs git publish ${request.origin_session} ${request.message}" in texts["bridge"],
    "BRIDGE_NO_RAW_COMMAND_FIELD": "row.command" not in texts["bridge"] and "raw_shell" not in texts["bridge"],
    "BRIDGE_PROJECT_SCOPE": "VXS_REQUEST_PROJECT_ROOT_OUT_OF_SCOPE" in texts["bridge"],
    "BRIDGE_DEVELOPMENT_ROOT": r"G:\\Vertex_Project\\Development" in texts["bridge"],
    "BRIDGE_IDEMPOTENT": "IDEMPOTENT_SUCCEEDED" in texts["bridge"] and "INDETERMINATE" in texts["bridge"],
    "BRIDGE_ACCEPTED_BOUNDARY": "appendAudit(request, 'ACCEPTED'" in texts["bridge"],
    "BRIDGE_NONINTERACTIVE": "'-NonInteractive'" in texts["bridge"],
    "BRIDGE_TIMEOUT": "EXECUTION_TIMEOUT_MS" in texts["bridge"],
    "GIT_PUBLISH_PRESENT": "VXS_AUTO_GIT_PUBLISH_000065V3" in texts["git"],
    "GIT_AUTHORITY_CHECK": "AUTO_AUTHORITY_NOT_ACTIVE" in texts["git"],
    "GIT_REMOTE_VERIFY": "REMOTE_HEAD_VERIFY_FAILED" in texts["git"],
    "GIT_NO_FORCE": "--force" not in texts["git"],
}

for key, ok in checks.items():
    print(f"{key}={'PASS' if ok else 'FAIL'}")
    if not ok:
        fail(key)

for label, path in (("DISPATCH", DISPATCH), ("RENDERER", RENDERER), ("BRIDGE", BRIDGE), ("GIT", GIT)):
    print(f"{label}_SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}")

cmd = ["npm.cmd", "run", "typecheck"]
print("RUN=" + " ".join(cmd))
cp = subprocess.run(
    cmd,
    cwd=ROOT,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    timeout=240,
)
stdout = (cp.stdout or b"").decode("utf-8", "replace")
stderr = (cp.stderr or b"").decode("utf-8", "replace")
print(f"TYPECHECK_EXIT={cp.returncode}")
if stdout:
    print("STDOUT_TAIL=" + stdout[-12000:])
if stderr:
    print("STDERR_TAIL=" + stderr[-12000:])
if cp.returncode != 0:
    fail("TYPECHECK")

print("VERIFY_PRODUCTION_SOURCE_MUTATION=NONE")
print("VERIFY_GIT_ADD_EXECUTED=NO")
print("VERIFY_GIT_COMMIT_EXECUTED=NO")
print("VERIFY_GIT_PUSH_EXECUTED=NO")
print("VERA_TO_VXS_TYPED_BRIDGE_000067V3=PASS")
raise SystemExit(0)
