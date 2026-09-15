from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import traceback

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

ROOT = Path(__file__).resolve().parent.parent

OWNER = ROOT / "src" / "main" / "ipc" / "register-vertex-shell-ipc.ts"
NERVE = ROOT / "src" / "main" / "shell" / "vxs" / "vera-vxs-vra-direct-http-nerve.ts"
AUTHORITY = ROOT / "src" / "main" / "shell" / "vxs" / "vera-vxs-human-authority.ts"
INTERFACE = ROOT / "src" / "main" / "shell" / "vxs" / "vera-vxs-interface.ts"
CLIENT = ROOT / "scripts" / "vra_vxs_direct_client.py"
E2E = ROOT / "scripts" / "vra_vxs_direct_http_e2e_000089V4.ts"

IMPORT_MARKER = "// VRA_VXS_DIRECT_HTTP_NERVE_000089V4_IMPORT"
CALL_MARKER = "// VRA_VXS_DIRECT_HTTP_NERVE_000089V4_REGISTER"

backups = {}
stage = "PREFLIGHT"

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())

def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".000089V4.tmp")
    tmp.write_bytes(data)
    os.replace(str(tmp), str(path))

def run(cmd: list[str], timeout: int = 300, env_extra=None):
    env = dict(os.environ)
    env["ELECTRON_DISABLE_SECURITY_WARNINGS"] = "true"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="backslashreplace",
        shell=False,
        timeout=timeout,
        env=env,
    )

def emit(label: str, text: str, limit: int = 22000) -> None:
    print(label + "=" + (text or "")[-limit:].replace("\r", "").replace("\n", " | "))

def resolve_node_npm():
    node = shutil.which("node.exe") or shutil.which("node")
    if not node:
        raise RuntimeError("NODE_NOT_FOUND")
    candidates = [Path(node).parent / "node_modules" / "npm" / "bin" / "npm-cli.js"]
    npm_cmd = shutil.which("npm.cmd") or shutil.which("npm")
    if npm_cmd:
        candidates.append(Path(npm_cmd).parent / "node_modules" / "npm" / "bin" / "npm-cli.js")
    npm_cli = next((p for p in candidates if p.is_file()), None)
    if npm_cli is None:
        raise RuntimeError("NPM_CLI_JS_NOT_FOUND")
    return str(Path(node)), str(npm_cli)

def patch_owner(text: str) -> str:
    text = re.sub(
        rf"(?m)^{re.escape(IMPORT_MARKER)}\s*\n"
        r"import \{ registerVeraVxsVraDirectHttpNerve \} "
        r"from '../shell/vxs/vera-vxs-vra-direct-http-nerve'\s*\n",
        "",
        text,
    )
    text = re.sub(
        rf"(?m)^[ \t]*{re.escape(CALL_MARKER)}\s*\n"
        r"[ \t]*registerVeraVxsVraDirectHttpNerve\([A-Za-z_$][A-Za-z0-9_$]*\)\s*;?\s*\n?",
        "",
        text,
    )

    import_block = (
        IMPORT_MARKER + "\n"
        + "import { registerVeraVxsVraDirectHttpNerve } "
        + "from '../shell/vxs/vera-vxs-vra-direct-http-nerve'\n"
    )
    text = import_block + text

    prod = re.search(
        r"(?m)^(?P<indent>[ \t]*)registerVeraVxsProductionIpc\("
        r"(?P<service>[A-Za-z_$][A-Za-z0-9_$]*)\)\s*;?\s*$",
        text,
    )
    if not prod:
        raise RuntimeError("PRODUCTION_VERA_VXS_REGISTRATION_NOT_FOUND")
    indent = prod.group("indent")
    service = prod.group("service")
    insert = (
        prod.group(0) + "\n"
        + indent + CALL_MARKER + "\n"
        + indent + f"registerVeraVxsVraDirectHttpNerve({service})"
    )
    text = text[:prod.start()] + insert + text[prod.end():]
    print("SHARED_VERTEX_SHELL_SERVICE_IDENTIFIER=" + service)
    return text

def rollback():
    ok = True
    for path, data in backups.items():
        try:
            atomic_write(path, data)
            same = path.read_bytes() == data
            print("ROLLBACK_OWNER_MATCH=" + str(same).lower())
            ok = ok and same
        except Exception as exc:
            print("ROLLBACK_ERROR=" + type(exc).__name__ + ":" + str(exc))
            ok = False
    print("TRANSACTION_ROLLBACK=" + ("PASS" if ok else "FAIL"))
    return ok

def main():
    global stage

    for path in (OWNER, NERVE, AUTHORITY, INTERFACE, CLIENT, E2E):
        if not path.is_file():
            raise RuntimeError("REQUIRED_FILE_MISSING:" + str(path))

    stage = "BACKUP_OWNER"
    backups[OWNER] = OWNER.read_bytes()
    print("OWNER_PREFLIGHT_SHA256=" + sha(OWNER))

    stage = "PATCH_OWNER"
    patched = patch_owner(OWNER.read_text(encoding="utf-8"))
    atomic_write(OWNER, patched.encode("utf-8"))
    print("OWNER_POSTPATCH_SHA256=" + sha(OWNER))

    stage = "STATIC_GUARDS"
    owner = OWNER.read_text(encoding="utf-8")
    nerve = NERVE.read_text(encoding="utf-8")
    interface = INTERFACE.read_text(encoding="utf-8")
    authority = AUTHORITY.read_text(encoding="utf-8")
    client = CLIENT.read_text(encoding="utf-8")

    checks = {
        "OWNER_SHARED_SERVICE_IMPORT": "registerVeraVxsVraDirectHttpNerve" in owner,
        "OWNER_SHARED_SERVICE_CALL": CALL_MARKER in owner,
        "LOOPBACK_HOST": "127.0.0.1" in nerve,
        "PRODUCTION_PORT_47834": "47834" in nerve,
        "HTTP_POST_EXECUTE": "/v1/execute" in nerve,
        "HTTP_HEALTH": "/health" in nerve,
        "HUMAN_GATE_CHECK": "isVeraVxsHumanFullAccessGranted()" in nerve,
        "TYPED_INTERFACE_REUSE": "executeVeraVxsRequest(service" in nerve,
        "NO_NEW_VERTEX_SHELL_SERVICE": "new VertexShellService" not in nerve,
        "REQUEST_SIZE_BOUND": "MAX_BODY_BYTES" in nerve,
        "COMMAND_SIZE_BOUND": "MAX_COMMAND_CHARS" in nerve,
        "ORIGIN_SUFFIX_GUARD": "VERA_VXS_DIRECT_ORIGIN_MISMATCH" in nerve,
        "SINGLE_FLIGHT_GUARD": "VERA_VXS_DIRECT_BUSY" in nerve,
        "NO_CORS_ENABLE": "access-control-allow-origin" not in nerve.lower(),
        "AUTH_PROCESS_SCOPE_PRESERVED": "persistence: 'PROCESS'" in authority,
        "INTERFACE_HUMAN_GATE_PRESERVED": "VERA_VXS_HUMAN_GATE_REQUIRED" in interface,
        "CLIENT_TARGET_LOOPBACK": "http://127.0.0.1:47834/v1/execute" in client,
    }

    for name, passed in checks.items():
        print(name + "=" + ("PASS" if passed else "FAIL"))
        if not passed:
            raise RuntimeError("STATIC_GUARD_FAILED:" + name)

    if owner.count(CALL_MARKER) != 1:
        raise RuntimeError("DIRECT_NERVE_REGISTER_COUNT_INVALID")
    if owner.count("registerVeraVxsVraDirectHttpNerve(") != 1:
        raise RuntimeError("DIRECT_NERVE_CALL_COUNT_INVALID")

    stage = "PYTHON_CLIENT_SYNTAX"
    compile(CLIENT.read_text(encoding="utf-8"), str(CLIENT), "exec")
    print("PYTHON_CLIENT_SYNTAX=PASS")

    stage = "BUILD"
    node, npm_cli = resolve_node_npm()
    build = run([node, npm_cli, "run", "build"], timeout=360)
    emit("BUILD_STDOUT", build.stdout)
    emit("BUILD_STDERR", build.stderr)
    if build.returncode != 0:
        raise RuntimeError("NPM_BUILD_FAILED:" + str(build.returncode))
    print("NPM_BUILD=PASS")

    stage = "E2E_BUNDLE"
    esbuild = ROOT / "node_modules" / "esbuild" / "bin" / "esbuild"
    if not esbuild.is_file():
        raise RuntimeError("ESBUILD_JS_CLI_NOT_FOUND")
    runtime_dir = ROOT / "runtime" / "vxs" / "vra-direct-nerve-000089V4"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    bundle = runtime_dir / "e2e.cjs"
    bund = run([
        node,
        str(esbuild),
        str(E2E),
        "--bundle",
        "--platform=node",
        "--format=cjs",
        "--external:electron",
        "--outfile=" + str(bundle),
    ], timeout=120)
    emit("E2E_BUNDLE_STDOUT", bund.stdout)
    emit("E2E_BUNDLE_STDERR", bund.stderr)
    if bund.returncode != 0 or not bundle.is_file():
        raise RuntimeError("E2E_BUNDLE_FAILED")

    stage = "ELECTRON_E2E"
    electron = ROOT / "node_modules" / "electron" / "dist" / "electron.exe"
    if not electron.is_file():
        raise RuntimeError("ELECTRON_EXE_NOT_FOUND")
    e2e = run([str(electron), str(bundle)], timeout=150)
    emit("E2E_STDOUT", e2e.stdout)
    emit("E2E_STDERR", e2e.stderr)
    print("E2E_EXIT=" + str(e2e.returncode))
    if e2e.returncode != 0:
        raise RuntimeError("E2E_PROCESS_FAILED:" + str(e2e.returncode))

    required = (
        "VRA_VXS_DIRECT_HTTP_NERVE_E2E=PASS",
        "LOOPBACK_ONLY=true",
        "LOCKED_REJECT=PASS",
        "FULL_VXS=PASS",
        "FULL_POWERSHELL=PASS",
        "RELOCK_REJECT=PASS",
        "SECOND_EXECUTOR=false",
        "PRODUCTION_PORT=47834",
    )
    for token in required:
        if token not in e2e.stdout:
            raise RuntimeError("E2E_TOKEN_MISSING:" + token)

    stage = "RECEIPT"
    receipt_path = ROOT / "runtime" / "vxs" / "vera-vxs" / "vra-vxs-direct-http-nerve-000089V4.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "vertex-vxs/vra-direct-http-nerve-receipt-1",
        "artifact_id": "vertex-session-portal-vra-vxs-direct-http-nerve-000089V4",
        "transport": {
            "host": "127.0.0.1",
            "port": 47834,
            "execute_path": "/v1/execute",
            "health_path": "/health",
            "cors_enabled": False,
        },
        "authority": {
            "human_gate": "AUTH/FULL",
            "locked_reject": True,
            "process_scoped": True,
            "cryptographic_authentication": False,
        },
        "routing": {
            "typed_interface": "executeVeraVxsRequest",
            "executor": "shared VertexShellService",
            "second_executor": False,
        },
        "verification": {
            "build": True,
            "locked_reject": True,
            "full_vxs": True,
            "full_powershell": True,
            "relock_reject": True,
        },
        "sha256": {
            "owner": sha(OWNER),
            "nerve": sha(NERVE),
            "client": sha(CLIENT),
        },
    }
    atomic_write(
        receipt_path,
        json.dumps(receipt, ensure_ascii=False, indent=2).encode("utf-8"),
    )
    print("RECEIPT_PATH=" + str(receipt_path))
    print("RECEIPT_SHA256=" + sha(receipt_path))

    print("VRA_VXS_DIRECT_HTTP_NERVE_000089V4=PASS")
    print("VRA_TO_VXS_DIRECT_NERVE=INSTALLED")
    print("LOOPBACK_ONLY=true")
    print("HUMAN_GATE_REQUIRED=true")
    print("AUTH_FULL_REQUIRED=true")
    print("SHARED_VERTEX_SHELL_SERVICE=true")
    print("SECOND_EXECUTOR=false")
    print("DIRECT_VXS=PASS")
    print("DIRECT_POWERSHELL=PASS")
    print("PORTAL_RESTART_REQUIRED_FOR_PRODUCTION_LISTENER=true")
    print("CRYPTOGRAPHIC_AUTHENTICATION=false")
    return 0

def wrapper():
    global stage
    try:
        return main()
    except BaseException as exc:
        print("VRA_VXS_DIRECT_HTTP_NERVE_000089V4=FAIL")
        print("FAILURE_STAGE=" + stage)
        print("EXCEPTION_TYPE=" + type(exc).__name__)
        print("EXCEPTION_MESSAGE=" + str(exc))
        print("TRACEBACK_BEGIN")
        traceback.print_exc(file=sys.stdout)
        print("TRACEBACK_END")
        rollback()
        return 97

if __name__ == "__main__":
    raise SystemExit(wrapper())
