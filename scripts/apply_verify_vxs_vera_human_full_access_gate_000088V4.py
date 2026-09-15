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

HOST = ROOT / "src" / "main" / "shell" / "vertex-shell-host-bridge.ts"
INTERFACE = ROOT / "src" / "main" / "shell" / "vxs" / "vera-vxs-interface.ts"
OWNER = ROOT / "src" / "main" / "ipc" / "register-vertex-shell-ipc.ts"
PRELOAD = ROOT / "src" / "preload" / "index.ts"
AUTHORITY = ROOT / "src" / "main" / "shell" / "vxs" / "vera-vxs-human-authority.ts"
AUTH_TEST = ROOT / "scripts" / "vera_vxs_human_authority_test_000088V4.ts"
E2E = ROOT / "scripts" / "vera_vxs_human_full_access_e2e_000088V4.ts"

RECEIPT = ROOT / "runtime" / "vxs" / "vera-vxs" / "vera-vxs-human-full-access-gate-000088V4.json"
E2E_RECEIPT = ROOT / "runtime" / "vxs" / "vera-vxs" / "vera-vxs-human-full-access-e2e-000088V4.json"

HOST_IMPORT_MARKER = "// VERA_VXS_HUMAN_FULL_ACCESS_GATE_000088V4_IMPORT"
HOST_ACTION_BEGIN = "// VERA_VXS_HUMAN_FULL_ACCESS_GATE_000088V4_ACTION_BEGIN"
HOST_ACTION_END = "// VERA_VXS_HUMAN_FULL_ACCESS_GATE_000088V4_ACTION_END"
INTERFACE_IMPORT_MARKER = "// VERA_VXS_HUMAN_FULL_ACCESS_GATE_000088V4_INTERFACE_IMPORT"
INTERFACE_GATE_MARKER = "// VERA_VXS_HUMAN_FULL_ACCESS_GATE_000088V4_GATE"
OWNER_BEGIN = "// VERA_VXS_PRODUCTION_IPC_000088V4_BEGIN"
OWNER_END = "// VERA_VXS_PRODUCTION_IPC_000088V4_END"
OWNER_CALL = "// VERA_VXS_PRODUCTION_IPC_000088V4_REGISTER"
PRELOAD_BEGIN = "// VERA_VXS_PRELOAD_API_000088V4_BEGIN"
PRELOAD_END = "// VERA_VXS_PRELOAD_API_000088V4_END"

backups = {}
stage = "PREFLIGHT"

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())

def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".000088V4.tmp")
    tmp.write_bytes(data)
    os.replace(str(tmp), str(path))

def run(cmd: list[str], timeout: int = 300, env_extra: dict[str, str] | None = None):
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

def emit(label: str, value: str, limit: int = 18000) -> None:
    clean = (value or "")[-limit:].replace("\r", "").replace("\n", " | ")
    print(label + "=" + clean)

def resolve_node_npm():
    node = shutil.which("node.exe") or shutil.which("node")
    if not node:
        raise RuntimeError("NODE_NOT_FOUND")
    candidates = [
        Path(node).parent / "node_modules" / "npm" / "bin" / "npm-cli.js",
    ]
    npm_cmd = shutil.which("npm.cmd") or shutil.which("npm")
    if npm_cmd:
        candidates.append(Path(npm_cmd).parent / "node_modules" / "npm" / "bin" / "npm-cli.js")
    npm_cli = next((p for p in candidates if p.is_file()), None)
    if npm_cli is None:
        raise RuntimeError("NPM_CLI_JS_NOT_FOUND")
    return str(Path(node)), str(npm_cli)

def match_pair(text: str, open_index: int, opener: str, closer: str) -> int:
    depth = 0
    quote = None
    escaped = False
    i = open_index
    while i < len(text):
        ch = text[i]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            i += 1
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1

def remove_marked(text: str, begin: str, end: str) -> str:
    return re.sub(
        rf"(?ms)^[ \t]*{re.escape(begin)}\s*\n.*?^[ \t]*{re.escape(end)}\s*\n?",
        "",
        text,
    )

def normalize_owner(text: str) -> str:
    # Current feature rerun.
    text = remove_marked(text, OWNER_BEGIN, OWNER_END)
    text = re.sub(
        rf"(?m)^[ \t]*{re.escape(OWNER_CALL)}\s*\n"
        r"[ \t]*registerVeraVxsProductionIpc\([A-Za-z_$][A-Za-z0-9_$]*\)\s*;?\s*\n?",
        "",
        text,
    )

    # Earlier H2/H4/H5/H6 wiring residue.
    for begin, end in (
        ("// VERA_VXS_PRODUCTION_HANDLER_000087V4H2_BEGIN", "// VERA_VXS_PRODUCTION_HANDLER_000087V4H2_END"),
        ("// VERA_VXS_PRODUCTION_H4_BEGIN", "// VERA_VXS_PRODUCTION_H4_END"),
        ("// VERA_VXS_PRODUCTION_H5_BEGIN", "// VERA_VXS_PRODUCTION_H5_END"),
        ("// VERA_VXS_PRODUCTION_H6_BEGIN", "// VERA_VXS_PRODUCTION_H6_END"),
    ):
        text = remove_marked(text, begin, end)

    text = re.sub(
        r"(?m)^[ \t]*// VERA_VXS_PRODUCTION_(?:CALL_000087V4H2|H4_REGISTER|H5_REGISTER|H6_REGISTER)\s*\n"
        r"[ \t]*registerVeraVxsProductionIpc\([A-Za-z_$][A-Za-z0-9_$]*\)\s*;?\s*\n?",
        "",
        text,
    )
    text = re.sub(
        r"(?m)^import type \{ VeraVxsRequest, VeraVxsResult \} from '../../shared/vera-vxs-contracts'\s*\n",
        "",
        text,
    )
    text = re.sub(
        r"(?m)^import \{ executeVeraVxsRequest \} from '../shell/vxs/vera-vxs-interface'\s*\n",
        "",
        text,
    )
    text = re.sub(
        r"(?m)^import \{ registerVeraVxsIpc \} from '\./register-vera-vxs-ipc'\s*\n",
        "",
        text,
    )
    text = re.sub(
        r"(?m)^[ \t]*// VERA_VXS_PRODUCTION_WIRING_000087V4H[13]\s*\n"
        r"[ \t]*registerVeraVxsIpc\([A-Za-z_$][A-Za-z0-9_$]*\)\s*;?\s*\n?",
        "",
        text,
    )
    return text

def normalize_preload(text: str) -> str:
    text = remove_marked(text, PRELOAD_BEGIN, PRELOAD_END)
    for begin, end in (
        ("// VERA_VXS_PRELOAD_H4_BEGIN", "// VERA_VXS_PRELOAD_H4_END"),
        ("// VERA_VXS_PRELOAD_H5_BEGIN", "// VERA_VXS_PRELOAD_H5_END"),
        ("// VERA_VXS_PRELOAD_H6_BEGIN", "// VERA_VXS_PRELOAD_H6_END"),
    ):
        text = remove_marked(text, begin, end)
    text = re.sub(
        r"(?m)^[ \t]*// VERA_VXS_PRELOAD_IMPORT_000087V4H[23]\s*\n"
        r"[ \t]*import '\./vera-vxs-preload'\s*\n?",
        "",
        text,
    )
    text = re.sub(
        r"(?ms)\n?[ \t]*// VERA_VXS_PRELOAD_WIRING_000087V4H1\s*\n"
        r"[ \t]*contextBridge\.exposeInMainWorld\('veraVxs'.*?\}\)\s*\n?",
        "\n",
        text,
    )
    return text

def choose_service(text: str) -> str:
    scores = {}
    for method, weight in (("execute", 20), ("state", 3), ("setCwd", 3), ("stop", 2)):
        for name in re.findall(rf"\b([A-Za-z_$][A-Za-z0-9_$]*)\.{method}\s*\(", text):
            if name in {"ipcMain", "ipcRenderer", "console", "window", "event"}:
                continue
            scores[name] = scores.get(name, 0) + weight
    for name in re.findall(
        r"\b(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*new\s+VertexShellService\s*\(",
        text,
    ):
        scores[name] = scores.get(name, 0) + 30
    if not scores:
        raise RuntimeError("VERTEX_SHELL_SERVICE_IDENTIFIER_NOT_FOUND")
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    print("SERVICE_CANDIDATES=" + json.dumps(ranked))
    return ranked[0][0]

def patch_owner(text: str) -> str:
    text = normalize_owner(text)
    service = choose_service(text)

    block = f"""
{OWNER_BEGIN}
export function registerVeraVxsProductionIpc(service: VertexShellService): void {{
  ipcMain.removeHandler('vera-vxs:execute')
  ipcMain.handle('vera-vxs:execute', async (_event, request: unknown) => {{
    const module = await import('../shell/vxs/vera-vxs-interface')
    return module.executeVeraVxsRequest(service, request as any)
  }})
}}
{OWNER_END}
"""
    text = text.rstrip() + "\n\n" + block.strip() + "\n"

    execute_match = re.search(rf"\b{re.escape(service)}\.execute\s*\(", text)
    if not execute_match:
        raise RuntimeError("SERVICE_EXECUTE_CALL_NOT_FOUND")
    handles = list(re.finditer(r"\bipcMain\.handle\s*\(", text[:execute_match.start()]))
    if not handles:
        raise RuntimeError("OWNER_IPC_HANDLE_ANCHOR_NOT_FOUND")
    anchor = handles[-1]
    line_start = text.rfind("\n", 0, anchor.start()) + 1
    indent = re.match(r"[ \t]*", text[line_start:anchor.start()]).group(0)
    registration = (
        indent + OWNER_CALL + "\n"
        + indent + f"registerVeraVxsProductionIpc({service})\n"
    )
    return text[:line_start] + registration + text[line_start:]

def patch_preload(text: str) -> str:
    text = normalize_preload(text)
    block = f"""
{PRELOAD_BEGIN}
contextBridge.exposeInMainWorld('veraVxs', {{
  execute: (request: unknown) => ipcRenderer.invoke('vera-vxs:execute', request)
}})
{PRELOAD_END}
"""
    return text.rstrip() + "\n\n" + block.strip() + "\n"

def decode_host_ui(text: str):
    m = re.search(r'const hostUi = ("(?:\\.|[^"\\])*")\s*\n', text)
    if not m:
        raise RuntimeError("HOST_UI_STRING_LITERAL_NOT_FOUND")
    try:
        ui = json.loads(m.group(1))
    except Exception as exc:
        raise RuntimeError("HOST_UI_JSON_DECODE_FAILED:" + str(exc))
    return m, ui

def patch_host_ui(ui: str) -> str:
    front = '<button class="summon" title="Bring Portal to front">FRONT</button>'
    auth = '<button class="authority" title="Grant VERA Full Access · Human Gate">AUTH</button>'
    if ui.count(front) != 1:
        raise RuntimeError("FRONT_BUTTON_ANCHOR_COUNT:" + str(ui.count(front)))
    ui = ui.replace(front, auth, 1)

    old_hint = 'CTRL+ALT+SPACE ON/OFF · CTRL+B FRONT OFF · CTRL+F FRONT ON'
    if old_hint in ui:
        ui = ui.replace(old_hint, 'CTRL+ALT+SPACE ON/OFF · AUTH = VERA FULL ACCESS', 1)

    css_anchor = '.pin.on{color:#55D69E;border-color:#55D69E}'
    if css_anchor not in ui:
        raise RuntimeError("HOST_UI_CSS_ANCHOR_NOT_FOUND")
    ui = ui.replace(
        css_anchor,
        css_anchor
        + '.authority{color:#F1B85B}'
        + '.authority.on{color:#55D69E;border-color:#55D69E;background:rgba(85,214,158,.08)}',
        1,
    )

    pin_anchor = "  const pin = q('.pin')\n"
    if pin_anchor not in ui:
        raise RuntimeError("HOST_UI_PIN_QUERY_ANCHOR_NOT_FOUND")
    ui = ui.replace(pin_anchor, pin_anchor + "  const authority = q('.authority')\n", 1)

    receive_anchor = "    if (message.type === 'execution_start') {\n"
    if receive_anchor not in ui:
        raise RuntimeError("HOST_UI_RECEIVE_ANCHOR_NOT_FOUND")
    receive = """    if (message.type === 'vera_authority_state') {
      const gate = message.state || {}
      const full = gate.mode === 'FULL' && gate.granted === true && gate.grantedBy === 'HUMAN'
      authority.classList.toggle('on', full)
      authority.textContent = full ? 'FULL' : 'AUTH'
      authority.title = full
        ? 'VERA Full Access · HUMAN GRANTED · click to revoke'
        : 'Grant VERA Full Access · Human Gate'
      return
    }

"""
    ui = ui.replace(receive_anchor, receive + receive_anchor, 1)

    click_anchor = "  q('.summon').addEventListener('click', () => send('summon'))\n"
    if click_anchor not in ui:
        raise RuntimeError("HOST_UI_FRONT_CLICK_ANCHOR_NOT_FOUND")
    ui = ui.replace(
        click_anchor,
        "  authority.addEventListener('click', () => send('toggle_vera_full_access'))\n",
        1,
    )

    init_anchor = "  send('state')\n  command.focus()\n"
    if init_anchor not in ui:
        raise RuntimeError("HOST_UI_INIT_ANCHOR_NOT_FOUND")
    ui = ui.replace(
        init_anchor,
        "  send('state')\n  send('vera_authority_state')\n  command.focus()\n",
        1,
    )

    if '<button class="summon"' in ui or '>FRONT</button>' in ui:
        raise RuntimeError("FRONT_BUTTON_STILL_PRESENT")
    if '<button class="authority"' not in ui:
        raise RuntimeError("AUTH_BUTTON_NOT_PRESENT")
    return ui

def patch_host(text: str) -> str:
    # Remove exact rerun import/action if present.
    text = re.sub(
        rf"(?m)^{re.escape(HOST_IMPORT_MARKER)}\s*\n"
        r"import \{ getVeraVxsHumanAuthorityState, toggleVeraVxsHumanFullAccess \} "
        r"from '\./vxs/vera-vxs-human-authority'\s*\n",
        "",
        text,
    )
    text = remove_marked(text, HOST_ACTION_BEGIN, HOST_ACTION_END)

    host_import = (
        HOST_IMPORT_MARKER + "\n"
        + "import { getVeraVxsHumanAuthorityState, toggleVeraVxsHumanFullAccess } "
        + "from './vxs/vera-vxs-human-authority'\n"
    )
    text = host_import + text

    paste_anchor = "      case 'paste_clipboard': {"
    if text.count(paste_anchor) != 1:
        raise RuntimeError("HOST_ACTION_SWITCH_ANCHOR_COUNT:" + str(text.count(paste_anchor)))
    action = f"""      {HOST_ACTION_BEGIN}
      case 'vera_authority_state': {{
        const state = getVeraVxsHumanAuthorityState()
        await sendToHost(binding, {{
          type: 'vera_authority_state',
          state
        }})
        return
      }}

      case 'toggle_vera_full_access': {{
        const state = toggleVeraVxsHumanFullAccess()
        await sendToHost(binding, {{
          type: 'vera_authority_state',
          state
        }})
        writeBridgeLog('vera_full_access_human_gate', {{
          wc_id: binding.wc.id,
          mode: state.mode,
          generation: state.generation,
          granted_by: state.grantedBy
        }})
        return
      }}
      {HOST_ACTION_END}

"""
    text = text.replace(paste_anchor, action + paste_anchor, 1)

    m, ui = decode_host_ui(text)
    patched_ui = patch_host_ui(ui)
    encoded = json.dumps(patched_ui, ensure_ascii=False)
    text = text[:m.start(1)] + encoded + text[m.end(1):]
    return text

def find_containing_if(text: str, token_pos: int):
    candidates = list(re.finditer(r"\bif\s*\(", text[max(0, token_pos - 2500):token_pos]))
    base = max(0, token_pos - 2500)
    for match in reversed(candidates):
        if_pos = base + match.start()
        open_paren = text.find("(", if_pos, token_pos)
        if open_paren < 0:
            continue
        close_paren = match_pair(text, open_paren, "(", ")")
        if close_paren < 0 or close_paren > token_pos:
            continue
        j = close_paren + 1
        while j < len(text) and text[j].isspace():
            j += 1
        if j < len(text) and text[j] == "{":
            close_brace = match_pair(text, j, "{", "}")
            if close_brace >= token_pos:
                return if_pos, open_paren, close_paren
        else:
            semi = text.find(";", j, token_pos + 600)
            if semi >= token_pos:
                return if_pos, open_paren, close_paren
    return None

def patch_interface(text: str) -> str:
    text = re.sub(
        rf"(?m)^{re.escape(INTERFACE_IMPORT_MARKER)}\s*\n"
        r"import \{ isVeraVxsHumanFullAccessGranted \} from '\./vera-vxs-human-authority'\s*\n",
        "",
        text,
    )
    text = re.sub(
        rf"(?m)^[ \t]*{re.escape(INTERFACE_GATE_MARKER)}\s*\n"
        r"[ \t]*if \(!isVeraVxsHumanFullAccessGranted\(\)\) \{\s*\n"
        r"[ \t]*throw new Error\('VERA_VXS_HUMAN_GATE_REQUIRED'\)\s*\n"
        r"[ \t]*\}\s*\n",
        "",
        text,
    )

    import_block = (
        INTERFACE_IMPORT_MARKER + "\n"
        + "import { isVeraVxsHumanFullAccessGranted } from './vera-vxs-human-authority'\n"
    )
    text = import_block + text

    fn = re.search(r"export\s+async\s+function\s+executeVeraVxsRequest\s*\(", text)
    if not fn:
        raise RuntimeError("EXECUTE_VERA_VXS_REQUEST_NOT_FOUND")
    open_paren = text.find("(", fn.start())
    close_paren = match_pair(text, open_paren, "(", ")")
    if close_paren < 0:
        raise RuntimeError("EXECUTE_SIGNATURE_UNBALANCED")
    open_brace = text.find("{", close_paren)
    if open_brace < 0:
        raise RuntimeError("EXECUTE_BODY_NOT_FOUND")

    gate = (
        "\n  " + INTERFACE_GATE_MARKER + "\n"
        + "  if (!isVeraVxsHumanFullAccessGranted()) {\n"
        + "    throw new Error('VERA_VXS_HUMAN_GATE_REQUIRED')\n"
        + "  }\n"
    )
    text = text[:open_brace + 1] + gate + text[open_brace + 1:]

    token = "VERA_VXS_CANONICAL_VXS_COMMAND_REQUIRED"
    if text.count(token) != 1:
        raise RuntimeError("CANONICAL_GUARD_TOKEN_COUNT:" + str(text.count(token)))
    token_pos = text.index(token)
    located = find_containing_if(text, token_pos)
    if located is None:
        raise RuntimeError("CANONICAL_GUARD_IF_NOT_FOUND")
    _if_pos, cond_open, cond_close = located
    condition = text[cond_open + 1:cond_close].strip()
    if "isVeraVxsHumanFullAccessGranted" in condition:
        raise RuntimeError("CANONICAL_GUARD_ALREADY_AUTH_PATCHED")
    replacement = f"!isVeraVxsHumanFullAccessGranted() && ({condition})"
    text = text[:cond_open + 1] + replacement + text[cond_close:]

    if "executor.execute" not in text:
        raise RuntimeError("EXISTING_EXECUTOR_DELEGATION_MISSING")
    return text

def rollback():
    ok = True
    for path, data in backups.items():
        try:
            atomic_write(path, data)
            same = path.read_bytes() == data
            print("ROLLBACK_" + path.name.replace(".", "_").upper() + "_MATCH=" + str(same).lower())
            ok = ok and same
        except Exception as exc:
            ok = False
            print("ROLLBACK_ERROR=" + str(path) + ":" + type(exc).__name__ + ":" + str(exc))
    print("TRANSACTION_ROLLBACK=" + ("PASS" if ok else "FAIL"))
    try:
        if E2E_RECEIPT.exists():
            E2E_RECEIPT.unlink()
    except Exception:
        pass
    return ok

def main():
    global stage
    for path in (HOST, INTERFACE, OWNER, PRELOAD, AUTHORITY, AUTH_TEST, E2E):
        if not path.is_file():
            raise RuntimeError("REQUIRED_FILE_MISSING:" + str(path))

    stage = "BACKUP"
    for path in (HOST, INTERFACE, OWNER, PRELOAD):
        backups[path] = path.read_bytes()
        print("PREFLIGHT_SHA256[" + str(path.relative_to(ROOT)) + "]=" + sha(path))

    stage = "PATCH"
    atomic_write(HOST, patch_host(HOST.read_text(encoding="utf-8")).encode("utf-8"))
    atomic_write(INTERFACE, patch_interface(INTERFACE.read_text(encoding="utf-8")).encode("utf-8"))
    atomic_write(OWNER, patch_owner(OWNER.read_text(encoding="utf-8")).encode("utf-8"))
    atomic_write(PRELOAD, patch_preload(PRELOAD.read_text(encoding="utf-8")).encode("utf-8"))

    stage = "STATIC_GUARDS"
    host = HOST.read_text(encoding="utf-8")
    interface = INTERFACE.read_text(encoding="utf-8")
    owner = OWNER.read_text(encoding="utf-8")
    preload = PRELOAD.read_text(encoding="utf-8")
    authority = AUTHORITY.read_text(encoding="utf-8")

    checks = {
        "FRONT_BUTTON_REMOVED": 'class=\\"summon\\"' not in host and '>FRONT</button>' not in host,
        "AUTH_BUTTON_PRESENT": 'class=\\"authority\\"' in host or 'class="authority"' in host,
        "AUTH_TOGGLE_ACTION_PRESENT": "toggle_vera_full_access" in host,
        "AUTH_STATE_ACTION_PRESENT": "vera_authority_state" in host,
        "AUTH_MAIN_PROCESS_MODULE_BOUND": "toggleVeraVxsHumanFullAccess" in host,
        "GATE_DEFAULT_LOCKED": "mode: 'LOCKED'" in authority and "granted: false" in authority,
        "GATE_PROCESS_SCOPED": "persistence: 'PROCESS'" in authority,
        "GATE_HUMAN_ONLY": "grantedBy: 'HUMAN'" in authority,
        "INTERFACE_GATE_REQUIRED": "VERA_VXS_HUMAN_GATE_REQUIRED" in interface,
        "INTERFACE_FULL_ACCESS_BYPASS": "!isVeraVxsHumanFullAccessGranted() &&" in interface,
        "CANONICAL_GUARD_PRESERVED": "VERA_VXS_CANONICAL_VXS_COMMAND_REQUIRED" in interface,
        "EXISTING_EXECUTOR_PRESERVED": "executor.execute" in interface,
        "PRODUCTION_IPC_PRESENT": "ipcMain.handle('vera-vxs:execute'" in owner,
        "PRODUCTION_SERVICE_REGISTERED": "registerVeraVxsProductionIpc(" in owner,
        "PRELOAD_API_PRESENT": "contextBridge.exposeInMainWorld('veraVxs'" in preload,
        "PRELOAD_IPC_PRESENT": "ipcRenderer.invoke('vera-vxs:execute', request)" in preload,
        "NO_CHILD_PROCESS_IN_INTERFACE": "child_process" not in interface and "node:child_process" not in interface,
        "NO_PERSISTENT_AUTH_STORAGE": "writeFile" not in authority and "localStorage" not in authority,
    }
    for name, value in checks.items():
        print(name + "=" + ("PASS" if value else "FAIL"))
        if not value:
            raise RuntimeError("STATIC_GUARD_FAILED:" + name)

    stage = "TOOLCHAIN"
    node, npm_cli = resolve_node_npm()
    esbuild_cli = ROOT / "node_modules" / "esbuild" / "bin" / "esbuild"
    if not esbuild_cli.is_file():
        raise RuntimeError("ESBUILD_JS_CLI_NOT_FOUND:" + str(esbuild_cli))
    electron = ROOT / "node_modules" / "electron" / "dist" / "electron.exe"
    if not electron.is_file():
        raise RuntimeError("ELECTRON_EXE_NOT_FOUND:" + str(electron))

    stage = "AUTHORITY_UNIT_TEST"
    runtime = ROOT / "runtime" / "vxs" / "vera-vxs-gate-000088V4"
    runtime.mkdir(parents=True, exist_ok=True)
    auth_bundle = runtime / "authority-test.cjs"
    build_auth = run([
        node, str(esbuild_cli), str(AUTH_TEST),
        "--bundle", "--platform=node", "--format=cjs",
        "--outfile=" + str(auth_bundle)
    ], timeout=120)
    emit("AUTH_TEST_BUNDLE_STDOUT", build_auth.stdout)
    emit("AUTH_TEST_BUNDLE_STDERR", build_auth.stderr)
    if build_auth.returncode != 0:
        raise RuntimeError("AUTHORITY_TEST_BUNDLE_FAILED:" + str(build_auth.returncode))
    auth_run = run([node, str(auth_bundle)], timeout=60)
    emit("AUTH_TEST_STDOUT", auth_run.stdout)
    emit("AUTH_TEST_STDERR", auth_run.stderr)
    if auth_run.returncode != 0 or "VERA_VXS_HUMAN_AUTHORITY_TEST=PASS" not in auth_run.stdout:
        raise RuntimeError("AUTHORITY_UNIT_TEST_FAILED")

    stage = "BUILD"
    build = run([node, npm_cli, "run", "build"], timeout=360)
    emit("BUILD_STDOUT", build.stdout)
    emit("BUILD_STDERR", build.stderr)
    if build.returncode != 0:
        raise RuntimeError("NPM_BUILD_FAILED:" + str(build.returncode))
    print("NPM_BUILD=PASS")

    stage = "E2E_BUNDLE"
    e2e_bundle = runtime / "human-full-access-e2e.cjs"
    e2e_build = run([
        node, str(esbuild_cli), str(E2E),
        "--bundle", "--platform=node", "--format=cjs",
        "--external:electron",
        "--outfile=" + str(e2e_bundle)
    ], timeout=120)
    emit("E2E_BUNDLE_STDOUT", e2e_build.stdout)
    emit("E2E_BUNDLE_STDERR", e2e_build.stderr)
    if e2e_build.returncode != 0:
        raise RuntimeError("E2E_BUNDLE_FAILED:" + str(e2e_build.returncode))

    stage = "PRELOAD_DISCOVERY"
    preload_dir = ROOT / "out" / "preload"
    candidates = [preload_dir / "index.js", preload_dir / "index.cjs", preload_dir / "index.mjs"]
    built_preload = next((p for p in candidates if p.is_file()), None)
    if built_preload is None and preload_dir.is_dir():
        found = sorted(p for p in preload_dir.glob("index.*") if p.is_file())
        if len(found) == 1:
            built_preload = found[0]
    if built_preload is None:
        raise RuntimeError("BUILT_PRELOAD_NOT_FOUND")

    stage = "HUMAN_GATE_E2E"
    if E2E_RECEIPT.exists():
        E2E_RECEIPT.unlink()
    e2e = run(
        [str(electron), str(e2e_bundle)],
        timeout=150,
        env_extra={
            "VERA_VXS_PRELOAD_PATH": str(built_preload),
            "VERA_VXS_GATE_E2E_RECEIPT": str(E2E_RECEIPT),
        },
    )
    emit("E2E_PROCESS_STDOUT", e2e.stdout)
    emit("E2E_PROCESS_STDERR", e2e.stderr)
    print("E2E_PROCESS_EXIT=" + str(e2e.returncode))
    if e2e.returncode != 0:
        raise RuntimeError("HUMAN_GATE_E2E_PROCESS_FAILED:" + str(e2e.returncode))
    if not E2E_RECEIPT.is_file():
        raise RuntimeError("HUMAN_GATE_E2E_RECEIPT_MISSING")
    e2e_data = json.loads(E2E_RECEIPT.read_text(encoding="utf-8"))
    required = {
        "locked_before": True,
        "full_vxs_exit_code": 0,
        "full_powershell_exit_code": 0,
        "locked_after_revoke": True,
        "process_scoped_authority": True,
    }
    for key, expected in required.items():
        if e2e_data.get(key) != expected:
            raise RuntimeError("HUMAN_GATE_E2E_ASSERT:" + key + ":" + repr(e2e_data.get(key)))
    print("HUMAN_GATE_E2E=PASS")
    print("FULL_POWERSHELL_BACKEND=" + str(e2e_data.get("full_powershell_backend", "")))

    stage = "RECEIPT"
    receipt = {
        "schema": "vertex-vxs/human-full-access-gate-receipt-1",
        "artifact_id": "vertex-session-portal-vxs-vera-human-full-access-gate-000088V4",
        "ui": {
            "front_button_removed": True,
            "authority_button": "AUTH",
            "granted_label": "FULL",
        },
        "authority": {
            "default": "LOCKED",
            "grant": "HUMAN",
            "scope": "VERA_FULL_ACCESS",
            "persistence": "PROCESS",
            "revoke": "AUTH_BUTTON_OR_PROCESS_EXIT",
            "vera_self_promotion": False,
            "cryptographic_authentication": False,
        },
        "route": {
            "preload_api": "window.veraVxs.execute",
            "ipc_channel": "vera-vxs:execute",
            "executor": "VertexShellService",
            "second_executor": False,
        },
        "verification": {
            "authority_unit_test": True,
            "npm_build": True,
            "e2e_locked_before": True,
            "e2e_vxs_full_access": True,
            "e2e_powershell_read_full_access": True,
            "e2e_locked_after_revoke": True,
            "powershell_backend": str(e2e_data.get("full_powershell_backend", "")),
        },
        "source_sha256": {
            "host_bridge": sha(HOST),
            "vera_vxs_interface": sha(INTERFACE),
            "ipc_owner": sha(OWNER),
            "preload": sha(PRELOAD),
            "authority_module": sha(AUTHORITY),
        },
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(RECEIPT, json.dumps(receipt, ensure_ascii=False, indent=2).encode("utf-8"))
    print("RECEIPT_PATH=" + str(RECEIPT))
    print("RECEIPT_SHA256=" + sha(RECEIPT))

    print("VXS_VERA_HUMAN_FULL_ACCESS_GATE_000088V4=PASS")
    print("FRONT_BUTTON_REMOVED=true")
    print("AUTH_BUTTON_INSTALLED=true")
    print("DEFAULT_AUTHORITY=LOCKED")
    print("HUMAN_GRANT=FULL")
    print("VERA_SELF_PROMOTION=false")
    print("AUTHORITY_PERSISTENCE=PROCESS")
    print("FULL_ACCESS_VXS=PASS")
    print("FULL_ACCESS_POWERSHELL_READ=PASS")
    print("REVOKE_RETURNS_LOCKED=PASS")
    print("SECOND_EXECUTOR=false")
    print("CRYPTOGRAPHIC_AUTHENTICATION=false")
    return 0

def wrapper():
    global stage
    try:
        return main()
    except BaseException as exc:
        print("VXS_VERA_HUMAN_FULL_ACCESS_GATE_000088V4=FAIL")
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
