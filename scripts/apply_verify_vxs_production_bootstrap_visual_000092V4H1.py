from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
HOST = ROOT / "src" / "main" / "shell" / "vertex-shell-host-bridge.ts"
OWNER = ROOT / "src" / "main" / "ipc" / "register-vertex-shell-ipc.ts"
NERVE = ROOT / "src" / "main" / "shell" / "vxs" / "vera-vxs-vra-direct-http-nerve.ts"
ACTIVITY = ROOT / "src" / "main" / "shell" / "vxs" / "vera-vxs-activity.ts"
E2E = ROOT / "scripts" / "vra_vxs_activity_visual_e2e_000092V4H1.ts"
OUT_MAIN = ROOT / "out" / "main" / "index.js"

IMPORT_MARKER = "// VXS_PRODUCTION_BOOTSTRAP_VISUAL_000092V4H1_IMPORT"
CALL_MARKER = "// VXS_PRODUCTION_BOOTSTRAP_VISUAL_000092V4H1_CALL"

stage = "PREFLIGHT"
host_backup: bytes | None = None
out_main_backup: bytes | None = None
out_main_existed = False

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())

def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".000092V4H1.tmp")
    tmp.write_bytes(data)
    os.replace(str(tmp), str(path))

def emit(label: str, text: str, limit: int = 32000) -> None:
    clean = (text or "").replace("\r", "")
    print(label + "=" + clean[-limit:].replace("\n", " | "))

def run(cmd: list[str], timeout: int = 420):
    env = dict(os.environ)
    env["ELECTRON_DISABLE_SECURITY_WARNINGS"] = "true"
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

def resolve_node_npm():
    node = shutil.which("node.exe") or shutil.which("node")
    if not node:
        raise RuntimeError("NODE_NOT_FOUND")
    candidates = [
        Path(node).parent / "node_modules" / "npm" / "bin" / "npm-cli.js",
    ]
    npm_cmd = shutil.which("npm.cmd") or shutil.which("npm")
    if npm_cmd:
        candidates.append(
            Path(npm_cmd).parent / "node_modules" / "npm" / "bin" / "npm-cli.js"
        )
    npm_cli = next((p for p in candidates if p.is_file()), None)
    if npm_cli is None:
        raise RuntimeError("NPM_CLI_JS_NOT_FOUND")
    return str(Path(node)), str(npm_cli)

def resolve_esbuild(node: str) -> tuple[str, str]:
    candidates = [
        ROOT / "node_modules" / "esbuild" / "bin" / "esbuild",
        ROOT / "node_modules" / "esbuild" / "bin" / "esbuild.js",
    ]
    tool = next((p for p in candidates if p.is_file()), None)
    if tool is None:
        raise RuntimeError("ESBUILD_NOT_FOUND")
    return node, str(tool)

def resolve_electron() -> str:
    candidates = [
        ROOT / "node_modules" / "electron" / "dist" / "electron.exe",
        ROOT / "node_modules" / "electron" / "dist" / "electron",
    ]
    electron = next((p for p in candidates if p.is_file()), None)
    if electron is None:
        raise RuntimeError("ELECTRON_BINARY_NOT_FOUND")
    return str(electron)

def remove_own_patch(text: str) -> str:
    text = re.sub(
        rf"(?m)^{re.escape(IMPORT_MARKER)}\s*\n"
        r"import\s+\{\s*registerVertexShellIpc\s*\}\s+"
        r"from\s+['\"]\.\.\/ipc\/register-vertex-shell-ipc['\"]\s*;?\s*\n",
        "",
        text,
    )
    text = re.sub(
        rf"(?m)^[ \t]*{re.escape(CALL_MARKER)}\s*\n"
        r"[ \t]*registerVertexShellIpc\([A-Za-z_$][A-Za-z0-9_$]*\)\s*;?\s*\n?",
        "",
        text,
    )
    return text

def service_constructor_candidates(text: str):
    pattern = re.compile(
        r"(?m)^(?P<indent>[ \t]*)"
        r"(?P<decl>(?:const|let|var)\s+"
        r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*"
        r"new\s+VertexShellService\s*\(\s*\)\s*;?)"
        r"[ \t]*$"
    )
    return list(pattern.finditer(text))

def broader_constructor_contexts(text: str):
    contexts = []
    for match in re.finditer(r"new\s+VertexShellService\s*\(", text):
        start = text.rfind("\n", 0, match.start()) + 1
        end = text.find("\n", match.end())
        if end < 0:
            end = len(text)
        contexts.append(text[start:end].strip())
    return contexts

def patch_host(text: str) -> tuple[str, str]:
    text = remove_own_patch(text)

    if "registerVertexShellIpc(" in text:
        unmanaged = [
            line.strip()
            for line in text.splitlines()
            if "registerVertexShellIpc(" in line
        ]
        raise RuntimeError(
            "UNMANAGED_REGISTER_VERTEX_SHELL_IPC_CALL:"
            + json.dumps(unmanaged, ensure_ascii=False)
        )

    candidates = service_constructor_candidates(text)
    print("HOST_SERVICE_CONSTRUCTOR_COUNT=" + str(len(candidates)))
    print(
        "HOST_SERVICE_CONSTRUCTOR_CONTEXTS="
        + json.dumps(broader_constructor_contexts(text), ensure_ascii=False)
    )
    if len(candidates) != 1:
        raise RuntimeError(
            "CANONICAL_HOST_VERTEX_SHELL_SERVICE_CONSTRUCTOR_NOT_UNIQUE:"
            + str(len(candidates))
        )

    match = candidates[0]
    service_name = match.group("name")
    indent = match.group("indent")
    print("CANONICAL_HOST_SERVICE=" + service_name)

    import_block = (
        IMPORT_MARKER
        + "\n"
        + "import { registerVertexShellIpc } "
        + "from '../ipc/register-vertex-shell-ipc'\n"
    )
    text = import_block + text

    # Locate the same declaration after prepending import.
    candidates2 = service_constructor_candidates(text)
    if len(candidates2) != 1 or candidates2[0].group("name") != service_name:
        raise RuntimeError("HOST_SERVICE_RELOCATION_FAILED")

    match2 = candidates2[0]
    insert_at = match2.end()
    call = (
        "\n"
        + indent
        + CALL_MARKER
        + "\n"
        + indent
        + f"registerVertexShellIpc({service_name})"
    )
    text = text[:insert_at] + call + text[insert_at:]

    if text.count(IMPORT_MARKER) != 1:
        raise RuntimeError("BOOTSTRAP_IMPORT_MARKER_COUNT_INVALID")
    if text.count(CALL_MARKER) != 1:
        raise RuntimeError("BOOTSTRAP_CALL_MARKER_COUNT_INVALID")
    if len(re.findall(r"\bregisterVertexShellIpc\s*\(", text)) != 1:
        raise RuntimeError("BOOTSTRAP_REGISTER_CALL_COUNT_INVALID")
    return text, service_name

def scan_external_registration_calls():
    hits = []
    for path in (ROOT / "src" / "main").rglob("*.ts"):
        if path == OWNER:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for index, line in enumerate(text.splitlines(), start=1):
            if re.search(r"\bregisterVertexShellIpc\s*\(", line):
                hits.append((str(path.relative_to(ROOT)), index, line.strip()))
    return hits

def rollback() -> bool:
    ok = True
    if host_backup is not None:
        try:
            atomic_write(HOST, host_backup)
            host_ok = HOST.read_bytes() == host_backup
            print("ROLLBACK_HOST_MATCH=" + str(host_ok).lower())
            ok = ok and host_ok
        except Exception as exc:
            print("ROLLBACK_HOST_EXCEPTION=" + type(exc).__name__ + ":" + str(exc))
            ok = False

    try:
        if out_main_existed and out_main_backup is not None:
            OUT_MAIN.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(OUT_MAIN, out_main_backup)
            out_ok = OUT_MAIN.read_bytes() == out_main_backup
            print("ROLLBACK_OUT_MAIN_MATCH=" + str(out_ok).lower())
            ok = ok and out_ok
        elif not out_main_existed and OUT_MAIN.exists():
            OUT_MAIN.unlink()
            print("ROLLBACK_OUT_MAIN_REMOVED=true")
    except Exception as exc:
        print("ROLLBACK_OUT_MAIN_EXCEPTION=" + type(exc).__name__ + ":" + str(exc))
        ok = False

    print("TRANSACTION_ROLLBACK=" + ("PASS" if ok else "FAIL"))
    return ok

def main() -> int:
    global stage, host_backup, out_main_backup, out_main_existed

    for path in (HOST, OWNER, NERVE, ACTIVITY, E2E):
        if not path.is_file():
            raise RuntimeError("REQUIRED_FILE_MISSING:" + str(path))

    stage = "SOURCE_RAY"
    host = HOST.read_text(encoding="utf-8")
    owner = OWNER.read_text(encoding="utf-8")
    nerve = NERVE.read_text(encoding="utf-8")
    activity = ACTIVITY.read_text(encoding="utf-8")

    print("HOST_PREFLIGHT_SHA256=" + sha(HOST))
    print("OWNER_SHA256=" + sha(OWNER))
    print("NERVE_SHA256=" + sha(NERVE))
    print("ACTIVITY_SHA256=" + sha(ACTIVITY))

    if "registerVeraVxsProductionIpc(service)" not in owner:
        raise RuntimeError("OWNER_VERA_PRODUCTION_IPC_REGISTRATION_MISSING")
    if "registerVeraVxsVraDirectHttpNerve(service)" not in owner:
        raise RuntimeError("OWNER_DIRECT_NERVE_REGISTRATION_MISSING")
    if "export function registerVertexShellIpc(" not in owner:
        raise RuntimeError("OWNER_REGISTER_VERTEX_SHELL_IPC_EXPORT_MISSING")
    if "service: VertexShellService" not in owner:
        raise RuntimeError("OWNER_SERVICE_INJECTION_SIGNATURE_MISSING")
    if "127.0.0.1" not in nerve or "47834" not in nerve:
        raise RuntimeError("DIRECT_NERVE_LOOPBACK_PORT_BASELINE_MISSING")
    if "VERA_VXS_HUMAN_GATE_REQUIRED" not in nerve:
        raise RuntimeError("DIRECT_NERVE_HUMAN_GATE_MISSING")
    if "beginVeraVxsActivity" not in nerve:
        raise RuntimeError("DIRECT_NERVE_ACTIVITY_BEGIN_MISSING")
    if "completeVeraVxsActivity" not in nerve:
        raise RuntimeError("DIRECT_NERVE_ACTIVITY_COMPLETE_MISSING")
    if "failVeraVxsActivity" not in nerve:
        raise RuntimeError("DIRECT_NERVE_ACTIVITY_FAIL_MISSING")
    if "vertex-shell-internal-unit" not in activity:
        raise RuntimeError("ACTIVITY_VXS_HOST_TARGET_MISSING")
    if "redactCommand" not in activity or "[REDACTED]" not in activity:
        raise RuntimeError("ACTIVITY_REDACTION_MISSING")

    existing_calls = scan_external_registration_calls()
    print(
        "PREPATCH_EXTERNAL_REGISTER_CALLS="
        + json.dumps(existing_calls, ensure_ascii=False)
    )
    # No production owner should already call it outside the registration module.
    if existing_calls:
        own_marker_hits = [
            hit for hit in existing_calls
            if hit[0] == str(HOST.relative_to(ROOT))
            and "registerVertexShellIpc" in hit[2]
        ]
        if len(existing_calls) != len(own_marker_hits):
            raise RuntimeError("UNEXPECTED_EXISTING_PRODUCTION_REGISTER_CALL")

    stage = "BACKUP"
    host_backup = HOST.read_bytes()
    out_main_existed = OUT_MAIN.is_file()
    if out_main_existed:
        out_main_backup = OUT_MAIN.read_bytes()

    stage = "PATCH_HOST_CANONICAL_SERVICE_BOOTSTRAP"
    patched_host, service_name = patch_host(host)
    atomic_write(HOST, patched_host.encode("utf-8"))
    print("HOST_POSTPATCH_SHA256=" + sha(HOST))
    print("BOOTSTRAP_SERVICE_IDENTIFIER=" + service_name)

    stage = "STATIC_GUARDS"
    host_after = HOST.read_text(encoding="utf-8")
    calls_after = scan_external_registration_calls()
    print(
        "POSTPATCH_EXTERNAL_REGISTER_CALLS="
        + json.dumps(calls_after, ensure_ascii=False)
    )

    checks = {
        "SHARED_SERVICE_CALL_PRESENT":
            f"registerVertexShellIpc({service_name})" in host_after,
        "NO_NEW_VERTEX_SHELL_SERVICE":
            host_after.count("new VertexShellService") == host.count("new VertexShellService"),
        "OWNER_SAME_SERVICE_FANOUT":
            "registerVeraVxsProductionIpc(service)" in owner
            and "registerVeraVxsVraDirectHttpNerve(service)" in owner,
        "ACTIVITY_ROUTE_VISIBLE":
            "VRA→VXS" in activity,
        "ACTIVITY_RUNNING_VISIBLE":
            "RUNNING" in activity and "vxsVeraActivity" in activity,
        "ACTIVITY_REDACTS_COMMAND":
            "redactCommand" in activity and "[REDACTED]" in activity,
        "NERVE_ACTIVITY_WIRED":
            all(token in nerve for token in (
                "beginVeraVxsActivity",
                "completeVeraVxsActivity",
                "failVeraVxsActivity",
            )),
        "DIRECT_NERVE_NO_CHILD_PROCESS":
            "child_process" not in nerve
            and "node:child_process" not in nerve
            and "new VertexShellService" not in nerve,
        "DIRECT_NERVE_TYPED_INTERFACE_REUSED":
            "executeVeraVxsRequest(service" in nerve,
        "DIRECT_NERVE_HUMAN_GATE_PRESERVED":
            "isVeraVxsHumanFullAccessGranted()" in nerve
            and "VERA_VXS_HUMAN_GATE_REQUIRED" in nerve,
    }
    for name, passed in checks.items():
        print(name + "=" + ("PASS" if passed else "FAIL"))
        if not passed:
            raise RuntimeError("STATIC_GUARD_FAILED:" + name)

    stage = "NPM_BUILD"
    node, npm_cli = resolve_node_npm()
    build = run([node, npm_cli, "run", "build"], timeout=480)
    emit("BUILD_STDOUT", build.stdout)
    emit("BUILD_STDERR", build.stderr)
    print("BUILD_EXIT=" + str(build.returncode))
    if build.returncode != 0:
        raise RuntimeError("NPM_BUILD_FAILED:" + str(build.returncode))
    print("NPM_BUILD=PASS")

    stage = "BUNDLE_GUARDS"
    if not OUT_MAIN.is_file():
        raise RuntimeError("OUT_MAIN_MISSING")
    bundle = OUT_MAIN.read_text(encoding="utf-8", errors="replace")
    bundle_checks = {
        "BUNDLE_PORT_47834": "47834" in bundle,
        "BUNDLE_DIRECT_SCHEMA": "vertex-vxs/vra-direct-request-1" in bundle,
        "BUNDLE_EXECUTE_ROUTE": "/v1/execute" in bundle,
        "BUNDLE_HEALTH_ROUTE": "/health" in bundle,
        "BUNDLE_HUMAN_GATE": "VERA_VXS_HUMAN_GATE_REQUIRED" in bundle,
        "BUNDLE_ACTIVITY_SCHEMA": "vertex-vxs/activity-1" in bundle,
        "BUNDLE_ACTIVITY_HOST_TARGET": "vertex-shell-internal-unit" in bundle,
        "BUNDLE_ACTIVITY_ROUTE": "VRA→VXS" in bundle,
    }
    for name, passed in bundle_checks.items():
        print(name + "=" + ("PASS" if passed else "FAIL"))
        if not passed:
            raise RuntimeError("BUNDLE_GUARD_FAILED:" + name)
    print("OUT_MAIN_SHA256=" + sha(OUT_MAIN))

    stage = "ACTIVITY_VISUAL_E2E_BUILD"
    es_node, esbuild = resolve_esbuild(node)
    e2e_bundle = Path(tempfile.gettempdir()) / "vra_vxs_activity_visual_e2e_000092V4H1.cjs"
    es = run([
        es_node,
        esbuild,
        str(E2E),
        "--bundle",
        "--platform=node",
        "--format=cjs",
        "--external:electron",
        f"--outfile={e2e_bundle}",
    ], timeout=120)
    emit("ESBUILD_STDOUT", es.stdout)
    emit("ESBUILD_STDERR", es.stderr)
    print("ESBUILD_EXIT=" + str(es.returncode))
    if es.returncode != 0 or not e2e_bundle.is_file():
        raise RuntimeError("ACTIVITY_E2E_BUILD_FAILED")

    stage = "ACTIVITY_VISUAL_E2E"
    electron = resolve_electron()
    e2e = run([electron, str(e2e_bundle)], timeout=120)
    emit("E2E_STDOUT", e2e.stdout)
    emit("E2E_STDERR", e2e.stderr)
    print("E2E_EXIT=" + str(e2e.returncode))
    try:
        e2e_bundle.unlink(missing_ok=True)
    except Exception:
        pass
    if e2e.returncode != 0:
        raise RuntimeError("ACTIVITY_VISUAL_E2E_FAILED:" + str(e2e.returncode))
    required_tokens = (
        "VRA_VXS_ACTIVITY_VISUAL_E2E_000092V4H1=PASS",
        "RUNNING_VISIBLE=PASS",
        "SUCCEEDED_VISIBLE=PASS",
        "FAILED_VISIBLE=PASS",
        "COMMAND_REDACTION=PASS",
        "SECOND_EXECUTOR=false",
    )
    for token in required_tokens:
        if token not in e2e.stdout:
            raise RuntimeError("ACTIVITY_E2E_TOKEN_MISSING:" + token)

    stage = "SUCCESS"
    print("VXS_PRODUCTION_BOOTSTRAP_VISUAL_000092V4H1=PASS")
    print("PRODUCTION_BOOTSTRAP_CONNECTED=true")
    print("SHARED_CANONICAL_VERTEX_SHELL_SERVICE=true")
    print("SECOND_EXECUTOR=false")
    print("DIRECT_NERVE_INCLUDED_IN_PRODUCTION_BUNDLE=true")
    print("PRODUCTION_PORT_47834_INCLUDED=true")
    print("VERA_ACTIVITY_VISUALIZATION=true")
    print("VERA_ACTIVITY_STATES=RUNNING,SUCCEEDED,FAILED")
    print("VERA_ACTIVITY_COMMAND_REDACTION=true")
    print("PORTAL_RESTART_REQUIRED=true")
    return 0

def wrapper() -> int:
    global stage
    try:
        return main()
    except BaseException as exc:
        print("VXS_PRODUCTION_BOOTSTRAP_VISUAL_000092V4H1=FAIL")
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
