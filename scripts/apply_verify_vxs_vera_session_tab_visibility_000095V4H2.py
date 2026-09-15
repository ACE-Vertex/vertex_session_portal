from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
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
ACTIVITY = ROOT / "src" / "main" / "shell" / "vxs" / "vera-vxs-activity.ts"
NERVE = ROOT / "src" / "main" / "shell" / "vxs" / "vera-vxs-vra-direct-http-nerve.ts"
E2E = ROOT / "scripts" / "vxs_vera_session_tab_visual_e2e_000095V4H2.ts"
OUT_MAIN = ROOT / "out" / "main" / "index.js"

MARKER = "VXS_VERA_SESSION_TAB_000095V4H2"
stage = "PREFLIGHT"

activity_backup: bytes | None = None
nerve_backup: bytes | None = None
out_main_backup: bytes | None = None
out_main_existed = False

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())

def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".000095V4H2.tmp")
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

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    print(label + "_MATCH_COUNT=" + str(count))
    if count != 1:
        raise RuntimeError(label + "_EXPECTED_ONE_MATCH:" + str(count))
    return text.replace(old, new, 1)

def patch_activity(text: str) -> str:
    if MARKER in text:
        raise RuntimeError("SESSION_TAB_PATCH_ALREADY_PRESENT")

    text = replace_once(
        text,
        "  originVera: string | null\n  route: 'VRA→VXS'",
        "  originVera: string | null\n  originSession: string | null\n  route: 'VRA→VXS'",
        "ACTIVITY_INTERFACE_SESSION",
    )

    text = replace_once(
        text,
        "  originVera: null,\n  route: 'VRA→VXS',",
        "  originVera: null,\n  originSession: null,\n  route: 'VRA→VXS',",
        "ACTIVITY_INITIAL_SESSION",
    )

    text = replace_once(
        text,
        "    const actions = shadow.querySelector('.actions')\n"
        "    if (!actions) return 'vxs-actions-not-ready'",
        "    const actions = shadow.querySelector('.actions')\n"
        "    const tabsRow = shadow.querySelector('.tabsRow')\n"
        "    const tabAdd = shadow.querySelector('.tabAdd')\n"
        "    if (!actions) return 'vxs-actions-not-ready'\n"
        "    if (!tabsRow) return 'vxs-tabs-row-not-ready'",
        "ACTIVITY_TABSROW_TARGET",
    )

    css_old = (
        "        '.vxsVeraActivity[data-state=\"FAILED\"] .vxsVeraState{color:#FF6F7C}',\n"
        "        '@media(max-width:760px){.vxsVeraActivity{max-width:150px}.vxsVeraActivity .vxsVeraCommand{display:none}}'"
    )
    css_new = (
        "        '.vxsVeraActivity[data-state=\"FAILED\"] .vxsVeraState{color:#FF6F7C}',\n"
        "        '.vxsVeraSessionBadge{height:24px;display:inline-flex;align-items:center;flex:none;padding:0 8px;',\n"
        "        'border:1px solid #26394B;border-radius:4px;background:#111923;color:#718195;',\n"
        "        'font:800 8px/1 \"Cascadia Mono\",Consolas,monospace;letter-spacing:.05em;white-space:nowrap}',\n"
        "        '.vxsVeraSessionBadge[data-state=\"RUNNING\"]{border-color:#F1B85B;color:#F1B85B;background:rgba(241,184,91,.06)}',\n"
        "        '.vxsVeraSessionBadge[data-state=\"SUCCEEDED\"]{border-color:#55D69E;color:#55D69E;background:rgba(85,214,158,.06)}',\n"
        "        '.vxsVeraSessionBadge[data-state=\"FAILED\"]{border-color:#FF6F7C;color:#FF6F7C;background:rgba(255,111,124,.06)}',\n"
        "        '@media(max-width:760px){.vxsVeraActivity{max-width:150px}.vxsVeraActivity .vxsVeraCommand{display:none}.vxsVeraSessionBadge{padding:0 6px}}'"
    )
    text = replace_once(text, css_old, css_new, "ACTIVITY_SESSION_BADGE_CSS")

    insert_old = (
        "    commandNode.textContent = activity.command || ''\n\n"
        "    const lines = ["
    )
    insert_new = (
        "    commandNode.textContent = activity.command || ''\n\n"
        "    // " + MARKER + "\n"
        "    const SESSION_BADGE_ID = 'vxs-vera-session-badge'\n"
        "    let sessionBadge = shadow.getElementById(SESSION_BADGE_ID)\n"
        "    if (!sessionBadge) {\n"
        "      sessionBadge = document.createElement('span')\n"
        "      sessionBadge.id = SESSION_BADGE_ID\n"
        "      sessionBadge.className = 'vxsVeraSessionBadge'\n"
        "      sessionBadge.setAttribute('role', 'status')\n"
        "      sessionBadge.setAttribute('aria-live', 'polite')\n"
        "      sessionBadge.setAttribute('aria-label', 'VERA session using VXS')\n"
        "      tabsRow.insertBefore(sessionBadge, tabAdd || null)\n"
        "    }\n\n"
        "    const sessionMatch = String(activity.originSession || '').match(/(\\\\d{2})$/)\n"
        "    const veraMatch = String(activity.originVera || '').match(/(\\\\d{2})$/)\n"
        "    const sessionNo = sessionMatch?.[1] || veraMatch?.[1] || ''\n"
        "    sessionBadge.dataset.state = activity.state\n"
        "    sessionBadge.hidden = activity.state === 'IDLE' || !sessionNo\n"
        "    sessionBadge.textContent = sessionNo\n"
        "      ? (activity.originVera || 'VERA') + ' · S' + sessionNo + ' · ' + stateLabel\n"
        "      : ''\n\n"
        "    const lines = ["
    )
    text = replace_once(text, insert_old, insert_new, "ACTIVITY_SESSION_BADGE_INSERT")

    text = replace_once(
        text,
        "      activity.originVera ? 'Origin: ' + activity.originVera : '',\n"
        "      activity.command ? 'Command: ' + activity.command : '',",
        "      activity.originVera ? 'Origin: ' + activity.originVera : '',\n"
        "      activity.originSession ? 'Session: ' + activity.originSession : '',\n"
        "      activity.command ? 'Command: ' + activity.command : '',",
        "ACTIVITY_TOOLTIP_SESSION",
    )

    text = replace_once(
        text,
        "    chip.title = lines.join('\\\\n')\n"
        "    return 'vxs-vera-activity-updated'",
        "    chip.title = lines.join('\\\\n')\n"
        "    sessionBadge.title = lines.join('\\\\n')\n"
        "    return 'vxs-vera-activity-updated'",
        "ACTIVITY_SESSION_BADGE_TITLE",
    )

    text = replace_once(
        text,
        "export function beginVeraVxsActivity(input: {\n"
        "  originVera: string\n"
        "  command: string",
        "export function beginVeraVxsActivity(input: {\n"
        "  originVera: string\n"
        "  originSession: string\n"
        "  command: string",
        "ACTIVITY_BEGIN_INPUT_SESSION",
    )

    text = replace_once(
        text,
        "    originVera: input.originVera,\n"
        "    route: 'VRA→VXS',",
        "    originVera: input.originVera,\n"
        "    originSession: input.originSession,\n"
        "    route: 'VRA→VXS',",
        "ACTIVITY_BEGIN_ASSIGN_SESSION",
    )
    return text

def patch_nerve(text: str) -> str:
    return replace_once(
        text,
        "    beginVeraVxsActivity({\n"
        "      originVera: direct.origin.vera,\n"
        "      command: direct.command,",
        "    beginVeraVxsActivity({\n"
        "      originVera: direct.origin.vera,\n"
        "      originSession: direct.origin.session,\n"
        "      command: direct.command,",
        "NERVE_PASS_ORIGIN_SESSION",
    )

def rollback() -> bool:
    ok = True
    if activity_backup is not None:
        try:
            atomic_write(ACTIVITY, activity_backup)
            print("ROLLBACK_ACTIVITY_MATCH=" + str(ACTIVITY.read_bytes() == activity_backup).lower())
        except Exception as exc:
            ok = False
            print("ROLLBACK_ACTIVITY_ERROR=" + str(exc))
    if nerve_backup is not None:
        try:
            atomic_write(NERVE, nerve_backup)
            print("ROLLBACK_NERVE_MATCH=" + str(NERVE.read_bytes() == nerve_backup).lower())
        except Exception as exc:
            ok = False
            print("ROLLBACK_NERVE_ERROR=" + str(exc))
    try:
        if out_main_existed and out_main_backup is not None:
            OUT_MAIN.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(OUT_MAIN, out_main_backup)
            print("ROLLBACK_OUT_MAIN_MATCH=" + str(OUT_MAIN.read_bytes() == out_main_backup).lower())
        elif not out_main_existed and OUT_MAIN.exists():
            OUT_MAIN.unlink()
            print("ROLLBACK_OUT_MAIN_REMOVED=true")
    except Exception as exc:
        ok = False
        print("ROLLBACK_OUT_MAIN_ERROR=" + str(exc))
    print("TRANSACTION_ROLLBACK=" + ("PASS" if ok else "FAIL"))
    return ok

def main() -> int:
    global stage, activity_backup, nerve_backup, out_main_backup, out_main_existed

    stage = "SOURCE_RAY"
    for path in (HOST, ACTIVITY, NERVE, E2E):
        if not path.is_file():
            raise RuntimeError("REQUIRED_FILE_MISSING:" + str(path.relative_to(ROOT)))

    host = HOST.read_text(encoding="utf-8", errors="replace")
    activity = ACTIVITY.read_text(encoding="utf-8", errors="replace")
    nerve = NERVE.read_text(encoding="utf-8", errors="replace")

    print("HOST_SHA256=" + sha(HOST))
    print("ACTIVITY_PREFLIGHT_SHA256=" + sha(ACTIVITY))
    print("NERVE_PREFLIGHT_SHA256=" + sha(NERVE))

    host_checks = {
        "HOST_HAS_TABS_ROW": ".tabsRow" in host,
        "HOST_HAS_TABS_NODE": ".tabs" in host,
        "HOST_HAS_TAB_ADD": ".tabAdd" in host,
        "HOST_HAS_RENDER_TABS": "renderTabs" in host,
    }
    for name, passed in host_checks.items():
        print(name + "=" + ("PASS" if passed else "FAIL"))
        if not passed:
            raise RuntimeError("SOURCE_RAY_FAILED:" + name)

    activity_backup = ACTIVITY.read_bytes()
    nerve_backup = NERVE.read_bytes()
    out_main_existed = OUT_MAIN.is_file()
    if out_main_existed:
        out_main_backup = OUT_MAIN.read_bytes()

    stage = "PATCH_ACTIVITY_AND_NERVE"
    patched_activity = patch_activity(activity)
    patched_nerve = patch_nerve(nerve)
    atomic_write(ACTIVITY, patched_activity.encode("utf-8"))
    atomic_write(NERVE, patched_nerve.encode("utf-8"))

    print("ACTIVITY_POSTPATCH_SHA256=" + sha(ACTIVITY))
    print("NERVE_POSTPATCH_SHA256=" + sha(NERVE))

    stage = "STATIC_GUARDS"
    activity_after = ACTIVITY.read_text(encoding="utf-8", errors="replace")
    nerve_after = NERVE.read_text(encoding="utf-8", errors="replace")

    template_regex_token = "match(/(" + (chr(92) * 2) + "d{2})$/)"
    print("SESSION_REGEX_EXPECTED_TOKEN=" + json.dumps(template_regex_token))
    print("SESSION_REGEX_EXPECTED_COUNT=" + str(activity_after.count(template_regex_token)))
    checks = {
        "SESSION_BADGE_MARKER_PRESENT": MARKER in activity_after,
        "SESSION_BADGE_TARGETS_TABS_ROW": "tabsRow.insertBefore(sessionBadge, tabAdd || null)" in activity_after,
        "SESSION_BADGE_ID_PRESENT": "vxs-vera-session-badge" in activity_after,
        "SESSION_NUMBER_VISIBLE": "' · S' + sessionNo + ' · ' + stateLabel" in activity_after,
        "SESSION_REGEX_SURVIVES_TEMPLATE": activity_after.count(template_regex_token) == 2,
        "ORIGIN_SESSION_TYPED": "originSession: string | null" in activity_after,
        "ORIGIN_SESSION_BEGIN_INPUT": "originSession: string" in activity_after,
        "NERVE_PASSES_REAL_SESSION": "originSession: direct.origin.session" in nerve_after,
        "COMMAND_REDACTION_PRESERVED": "redactCommand" in activity_after and "[REDACTED]" in activity_after,
        "HUMAN_GATE_PRESERVED": "isVeraVxsHumanFullAccessGranted()" in nerve_after,
        "TYPED_INTERFACE_PRESERVED": "executeVeraVxsRequest(service" in nerve_after,
        "NO_SECOND_EXECUTOR": "new VertexShellService" not in nerve_after and "child_process" not in nerve_after,
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
        "BUNDLE_SESSION_BADGE_ID": "vxs-vera-session-badge" in bundle,
        "BUNDLE_SESSION_BADGE_MARKER": MARKER in bundle,
        "BUNDLE_ORIGIN_SESSION": "originSession" in bundle,
        "BUNDLE_DIRECT_SESSION_SOURCE": "direct.origin.session" in bundle,
        "BUNDLE_TABS_ROW_TARGET": "tabsRow" in bundle,
        "BUNDLE_DIRECT_PORT_47834": "47834" in bundle,
        "BUNDLE_HUMAN_GATE": "VERA_VXS_HUMAN_GATE_REQUIRED" in bundle,
    }
    for name, passed in bundle_checks.items():
        print(name + "=" + ("PASS" if passed else "FAIL"))
        if not passed:
            raise RuntimeError("BUNDLE_GUARD_FAILED:" + name)
    print("OUT_MAIN_SHA256=" + sha(OUT_MAIN))

    stage = "SESSION_TAB_VISUAL_E2E_BUILD"
    es_node, esbuild = resolve_esbuild(node)
    e2e_bundle = Path(tempfile.gettempdir()) / "vxs_vera_session_tab_visual_e2e_000095V4H2.cjs"
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
        raise RuntimeError("SESSION_TAB_E2E_BUILD_FAILED")

    stage = "SESSION_TAB_VISUAL_E2E"
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
        raise RuntimeError("SESSION_TAB_VISUAL_E2E_FAILED:" + str(e2e.returncode))

    required_tokens = (
        "VXS_VERA_SESSION_TAB_E2E_000095V4H2=PASS",
        "SESSION_04_VISIBLE_IN_TAB_MENU=PASS",
        "SESSION_REGEX_TEMPLATE_ESCAPE=PASS",
        "SESSION_LABEL_RENDERED=VERA04 · S04",
        "RUNNING_STATE_VISIBLE=PASS",
        "SUCCEEDED_STATE_VISIBLE=PASS",
        "FAILED_STATE_VISIBLE=PASS",
        "SESSION_PROVENANCE_EXACT=PASS",
        "SECOND_EXECUTOR=false",
    )
    for token in required_tokens:
        if token not in e2e.stdout:
            raise RuntimeError("SESSION_TAB_E2E_TOKEN_MISSING:" + token)

    stage = "SUCCESS"
    print("VXS_VERA_SESSION_TAB_000095V4H2=PASS")
    print("VXS_TAB_MENU_SESSION_VISIBILITY=true")
    print("SESSION_LABEL_FORMAT=VERA04 · S04 · <STATE>")
    print("REAL_ORIGIN_SESSION_SOURCE=direct.origin.session")
    print("HUMAN_GATE_PRESERVED=true")
    print("SECOND_EXECUTOR=false")
    print("PORTAL_RESTART_REQUIRED=true")
    return 0

def wrapper() -> int:
    global stage
    try:
        return main()
    except BaseException as exc:
        print("VXS_VERA_SESSION_TAB_000095V4H2=FAIL")
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
