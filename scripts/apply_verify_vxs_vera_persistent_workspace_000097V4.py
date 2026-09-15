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
ACTIVITY = ROOT / "src" / "main" / "shell" / "vxs" / "vera-vxs-activity.ts"
NERVE = ROOT / "src" / "main" / "shell" / "vxs" / "vera-vxs-vra-direct-http-nerve.ts"
HOST = ROOT / "src" / "main" / "shell" / "vertex-shell-host-bridge.ts"
E2E = ROOT / "scripts" / "vxs_vera_persistent_workspace_e2e_000097V4.ts"
OUT_MAIN = ROOT / "out" / "main" / "index.js"

MARKER = "VXS_VERA_PERSISTENT_WORKSPACE_000097V4"
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
    tmp = path.with_name(path.name + ".000097V4.tmp")
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
    candidates = [Path(node).parent / "node_modules" / "npm" / "bin" / "npm-cli.js"]
    npm_cmd = shutil.which("npm.cmd") or shutil.which("npm")
    if npm_cmd:
        candidates.append(Path(npm_cmd).parent / "node_modules" / "npm" / "bin" / "npm-cli.js")
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
        raise RuntimeError("PERSISTENT_WORKSPACE_PATCH_ALREADY_PRESENT")
    if "VXS_VERA_SESSION_TAB_000095V4H2" not in text:
        raise RuntimeError("REQUIRED_000095V4H2_BASELINE_NOT_FOUND")

    text = replace_once(
        text,
        "  updatedAt: number\n  error: string | null\n}",
        "  updatedAt: number\n  visibleOutput: string | null\n  exitCode: number | null\n  error: string | null\n}",
        "ACTIVITY_INTERFACE_OUTPUT",
    )

    text = replace_once(
        text,
        "const MAX_VISIBLE_COMMAND_CHARS = 180\nconst MAX_VISIBLE_ERROR_CHARS = 240",
        "const MAX_VISIBLE_COMMAND_CHARS = 180\nconst MAX_VISIBLE_ERROR_CHARS = 240\nconst MAX_VISIBLE_OUTPUT_CHARS = 32_000",
        "ACTIVITY_OUTPUT_BOUND",
    )

    text = replace_once(
        text,
        "  completedAt: null,\n  updatedAt: Date.now(),\n  error: null",
        "  completedAt: null,\n  updatedAt: Date.now(),\n  visibleOutput: null,\n  exitCode: null,\n  error: null",
        "ACTIVITY_INITIAL_OUTPUT",
    )

    helper_anchor = '''function boundedError(value: unknown): string {
  const text = value instanceof Error ? value.message : String(value ?? '')
  return text.length <= MAX_VISIBLE_ERROR_CHARS
    ? text
    : `${text.slice(0, MAX_VISIBLE_ERROR_CHARS - 1)}…`
}
'''
    helper_insert = helper_anchor + r'''
function redactVisibleOutput(value: string): string {
  const redacted = String(value ?? '')
    .replace(
      /(api[_-]?key|token|password|passwd|secret)\s*=\s*("[^"]*"|'[^']*'|\S+)/gi,
      '$1=[REDACTED]'
    )
    .replace(
      /(authorization\s*:\s*bearer)\s+\S+/gi,
      '$1 [REDACTED]'
    )
    .replace(/\bsk-[A-Za-z0-9_-]{12,}\b/g, '[REDACTED]')

  return redacted.length <= MAX_VISIBLE_OUTPUT_CHARS
    ? redacted
    : `${redacted.slice(0, MAX_VISIBLE_OUTPUT_CHARS - 1)}…`
}

function visibleResult(result: unknown): {
  output: string | null
  exitCode: number | null
} {
  if (!result || typeof result !== 'object') {
    return { output: null, exitCode: null }
  }

  const record = result as Record<string, unknown>
  const streamEvents = Array.isArray(record.streamEvents)
    ? record.streamEvents
    : []

  const streamText = streamEvents
    .map(event => {
      if (!event || typeof event !== 'object') return ''
      const chunk = (event as Record<string, unknown>).chunk
      return typeof chunk === 'string' ? chunk : ''
    })
    .join('')

  const shellResult =
    record.shellResult && typeof record.shellResult === 'object'
      ? (record.shellResult as Record<string, unknown>)
      : null

  const exitCode =
    shellResult && typeof shellResult.exitCode === 'number'
      ? shellResult.exitCode
      : null

  let output = streamText
  if (!output && shellResult) {
    for (const key of ['output', 'stdout', 'stderr', 'message']) {
      const value = shellResult[key]
      if (typeof value === 'string' && value) {
        output += value
        if (!output.endsWith('\n')) output += '\n'
      }
    }
  }

  return {
    output: output ? redactVisibleOutput(output.trimEnd()) : null,
    exitCode
  }
}
'''
    text = replace_once(text, helper_anchor, helper_insert, "ACTIVITY_VISIBLE_RESULT_HELPERS")

    workspace_anchor = '''    sessionBadge.textContent = sessionNo
      ? (activity.originVera || 'VERA') + ' · S' + sessionNo + ' · ' + stateLabel
      : ''

    const lines = ['''

    workspace_insert = r'''    sessionBadge.textContent = sessionNo
      ? (activity.originVera || 'VERA') + ' · S' + sessionNo + ' · ' + stateLabel
      : ''

    // VXS_VERA_PERSISTENT_WORKSPACE_000097V4
    const shellPanel = shadow.querySelector('.vsh')
    const nativeTabs = shadow.querySelector('.tabs')
    const cwdRow = shadow.querySelector('.cwdRow')
    const nativeOutput = shadow.querySelector('.output')
    const composer = shadow.querySelector('.composer')

    if (
      shellPanel &&
      nativeTabs &&
      activity.originSession &&
      activity.originVera &&
      activity.requestId
    ) {
      const WORKSPACE_STYLE_ID = 'vxs-vera-workspace-style'
      const SESSION_TABS_ID = 'vxs-vera-session-tabs'

      let workspaceStyle = shadow.getElementById(WORKSPACE_STYLE_ID)
      if (!workspaceStyle) {
        workspaceStyle = document.createElement('style')
        workspaceStyle.id = WORKSPACE_STYLE_ID
        workspaceStyle.textContent = [
          '.vxsVeraSessionTabs{display:flex;align-items:center;gap:4px;flex:none;min-width:0}',
          '.vxsVeraPersistentTab{height:24px;min-width:126px;max-width:220px;display:flex;align-items:center;',
          'justify-content:center;gap:6px;padding:0 9px;border:1px solid #26394B;border-radius:5px;',
          'background:#111923;color:#718195;font:800 8px/1 "Cascadia Mono",Consolas,monospace;',
          'white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
          '.vxsVeraPersistentTab.active{color:#CBD5DF;border-color:#168CFF;background:#102C44;',
          'box-shadow:inset 0 -1px 0 #168CFF}',
          '.vxsVeraPersistentTab[data-state="RUNNING"]::before{content:"●";color:#F1B85B;font-size:7px}',
          '.vxsVeraPersistentTab[data-state="SUCCEEDED"]::before{content:"●";color:#55D69E;font-size:7px}',
          '.vxsVeraPersistentTab[data-state="FAILED"]::before{content:"●";color:#FF6F7C;font-size:7px}',
          '.vxsVeraWorkspace{grid-row:3 / 6;min-height:0;display:grid;grid-template-rows:34px minmax(0,1fr);',
          'background:#070B10;border-top:1px solid #1C2935}',
          '.vxsVeraWorkspace[hidden]{display:none}',
          '.vxsVeraWorkspaceHead{display:flex;align-items:center;justify-content:space-between;gap:10px;',
          'padding:0 10px;background:#0C121A;border-bottom:1px solid #1C2935}',
          '.vxsVeraWorkspaceIdentity{font:800 9px/1 system-ui,sans-serif;letter-spacing:.06em;color:#CBD5DF}',
          '.vxsVeraWorkspaceRoute{font:700 8px/1 "Cascadia Mono",Consolas,monospace;color:#718195}',
          '.vxsVeraWorkspaceHistory{min-height:0;overflow:auto;padding:9px 10px 14px;scrollbar-color:#26394B #070B10}',
          '.vxsVeraRun{padding:9px 10px;margin:0 0 8px;border:1px solid #1C2935;border-radius:6px;background:#0C121A}',
          '.vxsVeraRun:last-child{margin-bottom:0}',
          '.vxsVeraRunHead{display:flex;align-items:center;justify-content:space-between;gap:8px;',
          'margin-bottom:6px;color:#718195;font:800 8px/1 system-ui,sans-serif;letter-spacing:.04em}',
          '.vxsVeraRunState[data-state="RUNNING"]{color:#F1B85B}',
          '.vxsVeraRunState[data-state="SUCCEEDED"]{color:#55D69E}',
          '.vxsVeraRunState[data-state="FAILED"]{color:#FF6F7C}',
          '.vxsVeraRunInput,.vxsVeraRunOutput{margin:0;white-space:pre-wrap;word-break:break-word;',
          'font:11px/1.5 "Cascadia Mono",Consolas,monospace}',
          '.vxsVeraRunInput{padding:7px 9px;border:1px solid #26394B;border-radius:5px;',
          'background:#111923;color:#CBD5DF}',
          '.vxsVeraRunInput::before{content:"VSH › ";color:#168CFF;font-weight:900}',
          '.vxsVeraRunOutput{padding:7px 2px 0;color:#CBD5DF}',
          '.vxsVeraRunOutput:empty{display:none}',
          '@media(max-width:760px){.vxsVeraPersistentTab{min-width:100px;max-width:150px}.vxsVeraWorkspaceRoute{display:none}}'
        ].join('')
        shadow.appendChild(workspaceStyle)
      }

      let sessionTabs = shadow.getElementById(SESSION_TABS_ID)
      if (!sessionTabs) {
        sessionTabs = document.createElement('div')
        sessionTabs.id = SESSION_TABS_ID
        sessionTabs.className = 'vxsVeraSessionTabs'
        tabsRow.insertBefore(sessionTabs, sessionBadge || tabAdd || null)
      }

      const sessionKey = String(activity.originSession)
      const allWorkspaces = () => Array.from(shadow.querySelectorAll('.vxsVeraWorkspace'))
      const allVeraTabs = () => Array.from(shadow.querySelectorAll('.vxsVeraPersistentTab'))

      const showNativeWorkspace = () => {
        for (const node of [cwdRow, nativeOutput, composer]) {
          if (node) node.style.display = ''
        }
        for (const pane of allWorkspaces()) pane.hidden = true
        for (const button of allVeraTabs()) button.classList.remove('active')
      }

      const showVeraWorkspace = (button, pane) => {
        for (const node of [cwdRow, nativeOutput, composer]) {
          if (node) node.style.display = 'none'
        }
        for (const other of allWorkspaces()) other.hidden = other !== pane
        for (const other of allVeraTabs()) other.classList.toggle('active', other === button)
        pane.hidden = false
        const history = pane.querySelector('.vxsVeraWorkspaceHistory')
        if (history) history.scrollTop = history.scrollHeight
      }

      if (nativeTabs.dataset.vxsVeraWorkspaceBound !== '1') {
        nativeTabs.dataset.vxsVeraWorkspaceBound = '1'
        nativeTabs.addEventListener('click', event => {
          const target = event.target
          if (target && target.closest && target.closest('.tab')) showNativeWorkspace()
        })
      }

      if (tabAdd && tabAdd.dataset.vxsVeraWorkspaceBound !== '1') {
        tabAdd.dataset.vxsVeraWorkspaceBound = '1'
        tabAdd.addEventListener('click', () => showNativeWorkspace())
      }

      let sessionTab = Array.from(sessionTabs.querySelectorAll('.vxsVeraPersistentTab'))
        .find(button => button.dataset.session === sessionKey)
      const createdSessionTab = !sessionTab

      if (!sessionTab) {
        sessionTab = document.createElement('button')
        sessionTab.type = 'button'
        sessionTab.className = 'vxsVeraPersistentTab'
        sessionTab.dataset.session = sessionKey
        sessionTabs.appendChild(sessionTab)
      }

      let workspace = allWorkspaces().find(pane => pane.dataset.session === sessionKey)
      if (!workspace) {
        workspace = document.createElement('section')
        workspace.className = 'vxsVeraWorkspace'
        workspace.dataset.session = sessionKey
        workspace.hidden = true

        const workspaceHead = document.createElement('div')
        workspaceHead.className = 'vxsVeraWorkspaceHead'
        const identity = document.createElement('span')
        identity.className = 'vxsVeraWorkspaceIdentity'
        const route = document.createElement('span')
        route.className = 'vxsVeraWorkspaceRoute'
        route.textContent = 'VRA → VXS · persistent session workspace'
        const history = document.createElement('div')
        history.className = 'vxsVeraWorkspaceHistory'
        workspaceHead.append(identity, route)
        workspace.append(workspaceHead, history)
        shellPanel.appendChild(workspace)
      }

      const sessionNumber = sessionKey.slice(-2)
      const workspaceIdentity = workspace.querySelector('.vxsVeraWorkspaceIdentity')
      if (workspaceIdentity) workspaceIdentity.textContent = activity.originVera + ' · S' + sessionNumber

      sessionTab.dataset.state = activity.state
      sessionTab.textContent = activity.originVera + ' · S' + sessionNumber
      sessionTab.title = 'Persistent VXS workspace · ' + activity.originVera + ' / ' + sessionKey

      if (sessionTab.dataset.vxsVeraWorkspaceBound !== '1') {
        sessionTab.dataset.vxsVeraWorkspaceBound = '1'
        sessionTab.addEventListener('click', () => showVeraWorkspace(sessionTab, workspace))
      }

      const history = workspace.querySelector('.vxsVeraWorkspaceHistory')
      let run = history
        ? Array.from(history.querySelectorAll('.vxsVeraRun')).find(node => node.dataset.requestId === activity.requestId)
        : null

      if (!run && history) {
        run = document.createElement('article')
        run.className = 'vxsVeraRun'
        run.dataset.requestId = activity.requestId
        const runHead = document.createElement('div')
        runHead.className = 'vxsVeraRunHead'
        const request = document.createElement('span')
        request.className = 'vxsVeraRunRequest'
        request.textContent = activity.requestId.length > 42 ? activity.requestId.slice(0, 41) + '…' : activity.requestId
        const runState = document.createElement('span')
        runState.className = 'vxsVeraRunState'
        const runInput = document.createElement('pre')
        runInput.className = 'vxsVeraRunInput'
        const runOutput = document.createElement('pre')
        runOutput.className = 'vxsVeraRunOutput'
        runHead.append(request, runState)
        run.append(runHead, runInput, runOutput)
        history.appendChild(run)
        const runs = Array.from(history.querySelectorAll('.vxsVeraRun'))
        while (runs.length > 50) {
          const oldest = runs.shift()
          if (oldest) oldest.remove()
        }
      }

      if (run) {
        const runState = run.querySelector('.vxsVeraRunState')
        const runInput = run.querySelector('.vxsVeraRunInput')
        const runOutput = run.querySelector('.vxsVeraRunOutput')
        if (runState) {
          runState.dataset.state = activity.state
          runState.textContent =
            activity.state === 'RUNNING'
              ? 'RUNNING'
              : activity.state === 'SUCCEEDED'
                ? 'OK' + (typeof activity.exitCode === 'number' ? ' · EXIT ' + activity.exitCode : '')
                : activity.state === 'FAILED'
                  ? 'FAIL'
                  : 'IDLE'
        }
        if (runInput) runInput.textContent = activity.command || ''
        if (runOutput) runOutput.textContent = activity.visibleOutput || (activity.error ? 'ERR | ' + activity.error : '')
      }

      if (createdSessionTab) {
        if (typeof window.__VERTEX_SHELL_SET_VISIBILITY__ === 'function') {
          window.__VERTEX_SHELL_SET_VISIBILITY__(true)
        }
        shellPanel.classList.remove('collapsed')
        showVeraWorkspace(sessionTab, workspace)
      } else if (sessionTab.classList.contains('active')) {
        showVeraWorkspace(sessionTab, workspace)
      }

      if (history && sessionTab.classList.contains('active')) {
        history.scrollTop = history.scrollHeight
      }
    }

    const lines = ['''
    text = replace_once(text, workspace_anchor, workspace_insert, "ACTIVITY_PERSISTENT_WORKSPACE_UI")

    text = replace_once(
        text,
        "    completedAt: null,\n    updatedAt: now,\n    error: null",
        "    completedAt: null,\n    updatedAt: now,\n    visibleOutput: null,\n    exitCode: null,\n    error: null",
        "ACTIVITY_BEGIN_RESET_OUTPUT",
    )

    complete_old = '''export function completeVeraVxsActivity(
  requestId: string
): VeraVxsActivitySnapshot {
  if (activity.requestId !== requestId) return cloneActivity()
  const now = Date.now()
  activity = {
    ...activity,
    state: 'SUCCEEDED',
    completedAt: now,
    updatedAt: now,
    error: null
  }
  publishActivity(activity)
  return cloneActivity()
}
'''
    complete_new = '''export function completeVeraVxsActivity(
  requestId: string,
  result?: unknown
): VeraVxsActivitySnapshot {
  if (activity.requestId !== requestId) return cloneActivity()
  const now = Date.now()
  const visible = visibleResult(result)
  activity = {
    ...activity,
    state: 'SUCCEEDED',
    completedAt: now,
    updatedAt: now,
    visibleOutput: visible.output,
    exitCode: visible.exitCode,
    error: null
  }
  publishActivity(activity)
  return cloneActivity()
}
'''
    text = replace_once(text, complete_old, complete_new, "ACTIVITY_COMPLETE_WITH_RESULT")

    text = replace_once(
        text,
        "    completedAt: now,\n    updatedAt: now,\n    error: boundedError(error)",
        "    completedAt: now,\n    updatedAt: now,\n    visibleOutput: boundedError(error),\n    exitCode: null,\n    error: boundedError(error)",
        "ACTIVITY_FAIL_VISIBLE_OUTPUT",
    )
    return text

def patch_nerve(text: str) -> str:
    if "VXS_VERA_PERSISTENT_WORKSPACE_000097V4" in text:
        raise RuntimeError("NERVE_PERSISTENT_WORKSPACE_ALREADY_PRESENT")
    return replace_once(
        text,
        "      completeVeraVxsActivity(direct.request_id)",
        "      completeVeraVxsActivity(direct.request_id, result) // VXS_VERA_PERSISTENT_WORKSPACE_000097V4",
        "NERVE_PASS_RESULT_TO_WORKSPACE",
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
    for path in (ACTIVITY, NERVE, HOST, E2E):
        if not path.is_file():
            raise RuntimeError("REQUIRED_FILE_MISSING:" + str(path.relative_to(ROOT)))

    activity = ACTIVITY.read_text(encoding="utf-8", errors="replace")
    nerve = NERVE.read_text(encoding="utf-8", errors="replace")
    host = HOST.read_text(encoding="utf-8", errors="replace")
    print("ACTIVITY_PREFLIGHT_SHA256=" + sha(ACTIVITY))
    print("NERVE_PREFLIGHT_SHA256=" + sha(NERVE))
    print("HOST_PREFLIGHT_SHA256=" + sha(HOST))

    ray_checks = {
        "BASELINE_000095V4H2": "VXS_VERA_SESSION_TAB_000095V4H2" in activity,
        "HOST_VISIBILITY_HOOK": "__VERTEX_SHELL_SET_VISIBILITY__" in host,
        "HOST_TABS_ROW": ".tabsRow" in host,
        "HOST_NATIVE_TABS": ".tabs" in host,
        "HOST_CWD_ROW": ".cwdRow" in host,
        "HOST_OUTPUT": ".output" in host,
        "HOST_COMPOSER": ".composer" in host,
        "NERVE_COMPLETE_CALL": "completeVeraVxsActivity(direct.request_id)" in nerve,
        "HUMAN_GATE_PRESENT": "isVeraVxsHumanFullAccessGranted()" in nerve,
        "CANONICAL_EXECUTION_PRESENT": "executeVeraVxsRequest(service" in nerve,
    }
    for name, passed in ray_checks.items():
        print(name + "=" + ("PASS" if passed else "FAIL"))
        if not passed:
            raise RuntimeError("SOURCE_RAY_FAILED:" + name)

    activity_backup = ACTIVITY.read_bytes()
    nerve_backup = NERVE.read_bytes()
    out_main_existed = OUT_MAIN.is_file()
    if out_main_existed:
        out_main_backup = OUT_MAIN.read_bytes()

    stage = "PATCH"
    atomic_write(ACTIVITY, patch_activity(activity).encode("utf-8"))
    atomic_write(NERVE, patch_nerve(nerve).encode("utf-8"))
    print("ACTIVITY_POSTPATCH_SHA256=" + sha(ACTIVITY))
    print("NERVE_POSTPATCH_SHA256=" + sha(NERVE))

    stage = "STATIC_GUARDS"
    activity_after = ACTIVITY.read_text(encoding="utf-8", errors="replace")
    nerve_after = NERVE.read_text(encoding="utf-8", errors="replace")
    checks = {
        "PERSISTENT_WORKSPACE_MARKER": MARKER in activity_after,
        "PERSISTENT_TAB_CONTAINER": "vxs-vera-session-tabs" in activity_after,
        "PERSISTENT_WORKSPACE_PANEL": "vxsVeraWorkspace" in activity_after,
        "FIRST_OPEN_VISIBILITY": "__VERTEX_SHELL_SET_VISIBILITY__" in activity_after,
        "FIRST_OPEN_EXPANDS": "shellPanel.classList.remove('collapsed')" in activity_after,
        "SAME_SESSION_REUSE": "button.dataset.session === sessionKey" in activity_after,
        "HISTORY_LIMIT_50": "while (runs.length > 50)" in activity_after,
        "OUTPUT_REDACTION_PRESENT": "redactVisibleOutput" in activity_after,
        "RESULT_OUTPUT_CAPTURE": "visibleResult(result)" in activity_after,
        "NERVE_PASSES_RESULT": "completeVeraVxsActivity(direct.request_id, result)" in nerve_after,
        "HUMAN_GATE_PRESERVED": "isVeraVxsHumanFullAccessGranted()" in nerve_after,
        "CANONICAL_EXECUTOR_PRESERVED": "executeVeraVxsRequest(service" in nerve_after,
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
        "BUNDLE_PERSISTENT_TAB": "vxs-vera-session-tabs" in bundle,
        "BUNDLE_WORKSPACE": "vxsVeraWorkspace" in bundle,
        "BUNDLE_VISIBILITY_HOOK": "__VERTEX_SHELL_SET_VISIBILITY__" in bundle,
        "BUNDLE_RESULT_CAPTURE": "visibleResult" in bundle,
        "BUNDLE_DIRECT_PORT_47834": "47834" in bundle,
        "BUNDLE_HUMAN_GATE": "VERA_VXS_HUMAN_GATE_REQUIRED" in bundle,
    }
    for name, passed in bundle_checks.items():
        print(name + "=" + ("PASS" if passed else "FAIL"))
        if not passed:
            raise RuntimeError("BUNDLE_GUARD_FAILED:" + name)
    print("OUT_MAIN_SHA256=" + sha(OUT_MAIN))

    stage = "E2E_BUILD"
    es_node, esbuild = resolve_esbuild(node)
    e2e_bundle = Path(tempfile.gettempdir()) / "vxs_vera_persistent_workspace_e2e_000097V4.cjs"
    es = run([es_node, esbuild, str(E2E), "--bundle", "--platform=node", "--format=cjs", "--external:electron", f"--outfile={e2e_bundle}"], timeout=120)
    emit("ESBUILD_STDOUT", es.stdout)
    emit("ESBUILD_STDERR", es.stderr)
    print("ESBUILD_EXIT=" + str(es.returncode))
    if es.returncode != 0 or not e2e_bundle.is_file():
        raise RuntimeError("E2E_BUILD_FAILED")

    stage = "PERSISTENT_WORKSPACE_E2E"
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
        raise RuntimeError("PERSISTENT_WORKSPACE_E2E_FAILED:" + str(e2e.returncode))

    required_tokens = (
        "VXS_VERA_PERSISTENT_WORKSPACE_E2E_000097V4=PASS",
        "FIRST_REQUEST_OPENS_VXS=PASS",
        "FIRST_REQUEST_OPENS_DEDICATED_TAB=PASS",
        "INPUT_VISIBLE_DURING_RUNNING=PASS",
        "RESULT_VISIBLE_AFTER_COMPLETE=PASS",
        "NATIVE_TAB_CAN_SWITCH_AWAY=PASS",
        "VERA_TAB_PERSISTS_AFTER_SWITCH=PASS",
        "SECOND_REQUEST_REUSES_SAME_TAB=PASS",
        "SECOND_REQUEST_APPENDS_HISTORY=PASS",
        "HUMAN_CAN_REOPEN_VERA_TAB=PASS",
        "SECOND_EXECUTOR=false",
    )
    for token in required_tokens:
        if token not in e2e.stdout:
            raise RuntimeError("E2E_TOKEN_MISSING:" + token)

    stage = "SUCCESS"
    print("VXS_VERA_PERSISTENT_WORKSPACE_000097V4=PASS")
    print("PERSISTENT_SESSION_WORKSPACE=true")
    print("SESSION_KEY=vera-04")
    print("FIRST_REQUEST_AUTO_OPENS=true")
    print("AUTO_CLOSE=false")
    print("SUBSEQUENT_REQUESTS_REUSE_SAME_TAB=true")
    print("HUMAN_GATE_PRESERVED=true")
    print("SECOND_EXECUTOR=false")
    print("PORTAL_RESTART_REQUIRED=true")
    return 0

def wrapper() -> int:
    global stage
    try:
        return main()
    except BaseException as exc:
        print("VXS_VERA_PERSISTENT_WORKSPACE_000097V4=FAIL")
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
