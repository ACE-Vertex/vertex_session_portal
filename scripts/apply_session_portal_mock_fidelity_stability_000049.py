from pathlib import Path
import datetime as dt
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "EVIDENCE" / "SESSION_PORTAL_UI_STABILITY_000049"
STAMP = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP = EVIDENCE / STAMP

MAINFRAME = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
MAINFRAME_CSS = ROOT / "src/renderer/src/components/MainFrame/MainFrame.css"
BROWSER = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts"
BROWSER_CSS = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css"
SCALER_CSS = ROOT / "src/renderer/src/components/VeraWindowScaler/VeraWindowScaler.css"
EXPLORER_CSS = ROOT / "src/renderer/src/components/Explorer/Explorer.css"
DISPATCH_CSS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css"
MAIN = ROOT / "src/main/index.ts"

TOUCH = [
    MAINFRAME,
    MAINFRAME_CSS,
    BROWSER,
    BROWSER_CSS,
    SCALER_CSS,
    EXPLORER_CSS,
    DISPATCH_CSS,
    MAIN,
]

CSS_MARKER_BEGIN = "/* VERTEX_SESSION_PORTAL_MOCK_FIDELITY_000049_BEGIN */"
CSS_MARKER_END = "/* VERTEX_SESSION_PORTAL_MOCK_FIDELITY_000049_END */"
MAIN_MARKER_BEGIN = "// VERTEX_SESSION_PORTAL_STREAM_STABILITY_000049_BEGIN"
MAIN_MARKER_END = "// VERTEX_SESSION_PORTAL_STREAM_STABILITY_000049_END"


def safe_emit(value, stream=None):
    stream = stream or sys.stdout
    enc = getattr(stream, "encoding", None) or "utf-8"
    out = str(value).encode(enc, errors="backslashreplace").decode(enc, errors="replace")
    stream.write(out)
    if out and not out.endswith("\n"):
        stream.write("\n")
    stream.flush()


def read(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(f"MISSING_REQUIRED_FILE:{path}")
    return path.read_text(encoding="utf-8-sig")


def write(path: Path, text: str) -> None:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    path.write_bytes(normalized.encode("utf-8"))


def backup() -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    for path in TOUCH:
        if not path.exists():
            continue
        rel = path.relative_to(ROOT)
        dst = BACKUP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)


def restore() -> None:
    if not BACKUP.exists():
        return
    for src in BACKUP.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(BACKUP)
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def strip_css_patch(text: str) -> str:
    pattern = re.compile(
        re.escape(CSS_MARKER_BEGIN) + r".*?" + re.escape(CSS_MARKER_END),
        re.S,
    )
    return pattern.sub("", text).rstrip() + "\n"


def append_css_patch(path: Path, block: str) -> None:
    text = read(path)
    text = strip_css_patch(text)
    text += "\n" + CSS_MARKER_BEGIN + "\n" + block.strip() + "\n" + CSS_MARKER_END + "\n"
    write(path, text)


def patch_mainframe(text: str) -> str:
    out = text

    import_line = "import '../VraDispatchLane/VraDispatchDestinationControl'"
    if import_line not in out:
        out = import_line + "\n" + out

    # VERA 04 / 05 must use the same visible session header structure as 01-03.
    role_old = "const role = projection ? `session-role=\"${escapeHtml(projection.role)}\"` : ''"
    objective_old = """const objective = this.state.virtualArd
      ? `mission-objective=\"${escapeHtml(this.state.virtualArd.mission.objective)}\"`
      : ''"""
    if role_old in out:
        out = out.replace(
            role_old,
            "const assignmentChrome = session.id !== 'vera-04' && session.id !== 'vera-05'\n"
            "    const role = assignmentChrome && projection ? `session-role=\"${escapeHtml(projection.role)}\"` : ''",
            1,
        )
    elif "assignmentChrome = session.id !== 'vera-04'" not in out:
        # Tolerant regex for the same declaration if formatting has drifted.
        out, count = re.subn(
            r"const\s+role\s*=\s*projection\s*\?\s*`session-role=\\?\"\$\{escapeHtml\(projection\.role\)\}\\?\"`\s*:\s*''",
            "const assignmentChrome = session.id !== 'vera-04' && session.id !== 'vera-05'\n"
            "    const role = assignmentChrome && projection ? `session-role=\"${escapeHtml(projection.role)}\"` : ''",
            out,
            count=1,
        )
        if count == 0:
            raise RuntimeError("MAINFRAME_ROLE_DECLARATION_ANCHOR_NOT_FOUND")

    if objective_old in out:
        out = out.replace(
            objective_old,
            """const objective = assignmentChrome && this.state.virtualArd
      ? `mission-objective=\"${escapeHtml(this.state.virtualArd.mission.objective)}\"`
      : ''""",
            1,
        )
    elif "const objective = assignmentChrome && this.state.virtualArd" not in out:
        out, count = re.subn(
            r"const\s+objective\s*=\s*this\.state\.virtualArd\s*\?\s*`mission-objective=\\?\"\$\{escapeHtml\(this\.state\.virtualArd\.mission\.objective\)\}\\?\"`\s*:\s*''",
            "const objective = assignmentChrome && this.state.virtualArd\n"
            "      ? `mission-objective=\"${escapeHtml(this.state.virtualArd.mission.objective)}\"`\n"
            "      : ''",
            out,
            count=1,
        )
        if count == 0:
            raise RuntimeError("MAINFRAME_OBJECTIVE_DECLARATION_ANCHOR_NOT_FOUND")

    if 'class="brandMark"' not in out:
        brand_pattern = re.compile(
            r'<div class="brand">\s*'
            r'<span class="vertex">VERTEX</span>\s*'
            r'<span class="product">SESSION PORTAL</span>\s*'
            r'</div>'
        )
        replacement = '''<div class="brand">
            <span class="brandMark" aria-hidden="true"><i></i><i></i></span>
            <span class="vertex">VERTEX</span>
            <span class="product">Session Portal</span>
          </div>'''
        out, count = brand_pattern.subn(replacement, out, count=1)
        if count == 0:
            raise RuntimeError("MAINFRAME_BRAND_ANCHOR_NOT_FOUND")

    if 'class="primaryEntry"' not in out:
        system_anchor = '<div class="system">'
        if system_anchor not in out:
            raise RuntimeError("MAINFRAME_SYSTEM_ANCHOR_NOT_FOUND")
        primary = '''<div class="primaryEntry" title="Canonical Session Portal entry">
            <span class="primaryEntryGlyph">↗</span>
            <span>PRIMARY ENTRY</span>
          </div>
          '''
        out = out.replace(system_anchor, primary + system_anchor, 1)

    return out


def patch_browser(text: str) -> str:
    out = text

    if "reloadIgnoringCache: () => void" not in out:
        anchor = "  reload: () => void\n"
        if anchor not in out:
            raise RuntimeError("BROWSER_WEBVIEW_RELOAD_TYPE_ANCHOR_NOT_FOUND")
        out = out.replace(
            anchor,
            anchor + "  reloadIgnoringCache: () => void\n  stop: () => void\n",
            1,
        )

    # Existing reload becomes the recovery path, not a weak ordinary reload.
    old_reload = """this.shadowRoot
      ?.querySelector<HTMLButtonElement>('[data-action="reload"]')
      ?.addEventListener('click', () => browser.reload())"""
    new_reload = """this.shadowRoot
      ?.querySelector<HTMLButtonElement>('[data-action="reload"]')
      ?.addEventListener('click', () => {
        this.loading = true
        this.failure = ''
        this.updateStatus()
        try {
          browser.stop()
          browser.reloadIgnoringCache()
        } catch {
          browser.reload()
        }
      })"""
    if old_reload in out:
        out = out.replace(old_reload, new_reload, 1)
    elif "browser.reloadIgnoringCache()" not in out:
        raise RuntimeError("BROWSER_RELOAD_HANDLER_ANCHOR_NOT_FOUND")

    if "[data-action=\"recover\"]" not in out and "data-action=\"recover\"" not in out:
        reload_button = '<button type="button" data-action="reload" title="Reload">↻</button>'
        if reload_button not in out:
            raise RuntimeError("BROWSER_RELOAD_BUTTON_ANCHOR_NOT_FOUND")
        out = out.replace(
            reload_button,
            reload_button + '\n          <button type="button" data-action="recover" title="Force session recovery">⟳</button>',
            1,
        )

    if "querySelector<HTMLButtonElement>('[data-action=\"recover\"]')" not in out:
        home_anchor = """this.shadowRoot
      ?.querySelector<HTMLButtonElement>('[data-action="home"]')"""
        if home_anchor not in out:
            raise RuntimeError("BROWSER_HOME_HANDLER_ANCHOR_NOT_FOUND")
        recover_handler = """this.shadowRoot
      ?.querySelector<HTMLButtonElement>('[data-action="recover"]')
      ?.addEventListener('click', () => {
        this.loading = true
        this.failure = ''
        this.updateStatus()
        try {
          browser.stop()
          browser.reloadIgnoringCache()
        } catch {
          browser.reload()
        }
      })

    """
        out = out.replace(home_anchor, recover_handler + home_anchor, 1)

    if "CHATGPT SESSION UNRESPONSIVE" not in out:
        fail_anchor = """browser.addEventListener('did-fail-load', event => {
      const failure = event as WebviewFailEvent
      this.loading = false
      this.failure = failure.errorDescription || 'ChatGPT browser failed to load.'
      this.updateStatus()
    })"""
        if fail_anchor not in out:
            raise RuntimeError("BROWSER_DID_FAIL_LOAD_ANCHOR_NOT_FOUND")
        lifecycle = fail_anchor + """
    browser.addEventListener('unresponsive', () => {
      this.loading = false
      this.failure = 'CHATGPT SESSION UNRESPONSIVE · use ⟳ recovery'
      this.updateStatus()
    })
    browser.addEventListener('responsive', () => {
      if (this.failure.startsWith('CHATGPT SESSION UNRESPONSIVE')) {
        this.failure = ''
        this.updateStatus()
      }
    })
    browser.addEventListener('render-process-gone', () => {
      this.loading = false
      this.failure = 'CHATGPT SESSION PROCESS RESTART REQUIRED · use ⟳ recovery'
      this.updateStatus()
    })"""
        out = out.replace(fail_anchor, lifecycle, 1)

    return out


def patch_main(text: str) -> str:
    out = text

    # Place Chromium stability switches before runtime probe declarations and before app readiness.
    if MAIN_MARKER_BEGIN not in out:
        anchor = "const runtimeProbeMode ="
        pos = out.find(anchor)
        if pos < 0:
            raise RuntimeError("MAIN_RUNTIME_PROBE_ANCHOR_NOT_FOUND")
        block = f"""{MAIN_MARKER_BEGIN}
app.commandLine.appendSwitch('disable-renderer-backgrounding')
app.commandLine.appendSwitch('disable-background-timer-throttling')
app.commandLine.appendSwitch('disable-backgrounding-occluded-windows')
{MAIN_MARKER_END}

"""
        out = out[:pos] + block + out[pos:]

    # Keep the Portal renderer itself active even when the large Session Portal window
    # is partially occluded, and apply the same policy to each ChatGPT webview.
    if "        backgroundThrottling: false," not in out:
        window_anchor = "        webSecurity: true,\n        webviewTag: true"
        if window_anchor not in out:
            raise RuntimeError("MAIN_WINDOW_WEBPREFERENCES_ANCHOR_NOT_FOUND")
        out = out.replace(
            window_anchor,
            "        webSecurity: true,\n        backgroundThrottling: false,\n        webviewTag: true",
            1,
        )

    if "webPreferences.backgroundThrottling = false" not in out:
        anchor = "      webPreferences.webSecurity = true\n"
        if anchor not in out:
            raise RuntimeError("MAIN_WEBVIEW_WEBSECURITY_ANCHOR_NOT_FOUND")
        out = out.replace(
            anchor,
            anchor + "      webPreferences.backgroundThrottling = false\n",
            1,
        )

    # Pop-out windows from ChatGPT inherit the same no-throttle policy.
    popup_anchor = "                webSecurity: true\n              }"
    if "POPUP_BACKGROUND_THROTTLING_000049" not in out and popup_anchor in out:
        out = out.replace(
            popup_anchor,
            "                webSecurity: true,\n                backgroundThrottling: false // POPUP_BACKGROUND_THROTTLING_000049\n              }",
            1,
        )

    return out


MAINFRAME_CSS_BLOCK = r'''
.topbar {
  min-height: 52px;
  grid-template-columns: 286px minmax(320px, 1fr) auto auto;
  gap: 14px;
  padding: 0 14px;
  border-bottom-color: #1C2935;
  background:
    linear-gradient(180deg, rgba(10,25,47,.98), rgba(7,11,16,.99));
  box-shadow: 0 8px 28px rgba(0,0,0,.16), inset 0 -1px 0 rgba(58,184,255,.04);
}

.brand {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 9px;
  white-space: nowrap;
}

.brandMark {
  position: relative;
  display: inline-block;
  width: 31px;
  height: 30px;
  flex: 0 0 31px;
  filter: drop-shadow(0 0 8px rgba(22,140,255,.24));
}

.brandMark i {
  position: absolute;
  top: 2px;
  width: 15px;
  height: 26px;
  background: linear-gradient(180deg, #3AB8FF, #168CFF 62%, #0C5DB7);
  clip-path: polygon(0 0, 100% 0, 48% 100%);
}

.brandMark i:first-child { left: 0; transform: skewX(-8deg); }
.brandMark i:last-child { right: 0; transform: skewX(8deg); opacity: .82; }

.vertex {
  color: #CBD5DF;
  font-size: 16px;
  font-weight: 900;
  letter-spacing: .17em;
  text-shadow: 0 0 12px rgba(58,184,255,.08);
}

.product {
  margin-left: 2px;
  padding-left: 10px;
  border-left: 1px solid #26394B;
  color: #AEBBC8;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: .02em;
  text-transform: none;
}

.commandSearch {
  justify-self: stretch;
  max-width: 760px;
  min-width: 260px;
  height: 32px;
  border-color: #1C2935;
  border-radius: 9px;
  background: #0C121A;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.015);
}

.primaryEntry {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-width: 134px;
  height: 32px;
  padding: 0 13px;
  border: 1px solid #168CFF;
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(16,44,68,.96), rgba(8,25,43,.96));
  color: #9EDBFF;
  font-size: 9px;
  font-weight: 900;
  letter-spacing: .12em;
  box-shadow: 0 0 16px rgba(22,140,255,.18), inset 0 0 14px rgba(58,184,255,.05);
}

.primaryEntryGlyph {
  color: #3AB8FF;
  font-size: 14px;
  line-height: 1;
}

.system {
  gap: 10px;
  white-space: nowrap;
}

.main { min-height: 0; }
.sessionViewport { background: #070B10; }
.sessionTrack { gap: 6px; padding: 6px; }
.statusbar { border-top-color: #1C2935; background: #070B10; }

@media (max-width: 1680px) {
  .topbar { grid-template-columns: 252px minmax(260px, 1fr) auto; }
  .primaryEntry { display: none; }
  .system .telemetry:nth-of-type(-n+2) { display: none; }
}
'''

BROWSER_CSS_BLOCK = r'''
:host { min-width: 0; }
.session {
  border-color: #1C2935;
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(8,18,32,.99), rgba(3,8,14,.99));
}
.chrome {
  min-height: 28px;
  padding: 0 9px;
  border-bottom-color: #1C2935;
  background: #0C121A;
}
.header {
  padding: 8px 10px;
  border-bottom-color: #1C2935;
  background: linear-gradient(180deg, rgba(12,27,48,.96), rgba(8,18,32,.96));
}
.eyebrow { color: #3AB8FF; font-size: 8.5px; letter-spacing: .11em; }
.title { color: #CBD5DF; font-size: 15px; font-weight: 760; }
.roleBar { min-height: 0; }
:host([session-id="vera-04"]) .roleBar,
:host([session-id="vera-05"]) .roleBar { display: none !important; }
.browserToolbar {
  grid-template-columns: 24px 24px 24px 24px 24px minmax(0,1fr) auto;
  gap: 4px;
  padding: 4px 7px;
  border-bottom-color: #1C2935;
  background: #070B10;
}
.browserToolbar button { border-color: #1C2935; background: #0C121A; }
.browserToolbar button[data-action="recover"] {
  border-color: #26394B;
  color: #3AB8FF;
}
.browserToolbar button[data-action="recover"]:hover {
  border-color: #3AB8FF;
  box-shadow: 0 0 12px rgba(22,140,255,.16);
}
.accountMode { color: #718195; font-size: 7.5px; }
.browserBody { background: #000; }
.sessionFoot { border-top-color: #1C2935; background: #070B10; }
'''

SCALER_CSS_BLOCK = r'''
:host { top: 10px; left: 302px; z-index: 5000; }
.scaler {
  height: 31px;
  border-color: #26394B;
  border-radius: 8px;
  background: linear-gradient(180deg, #111923, #0C121A);
  box-shadow: 0 0 14px rgba(22,140,255,.10);
}
button[data-active] {
  border-color: #3AB8FF;
  background: #102C44;
  color: #3AB8FF;
}
@media (max-width: 1680px) { :host { left: 270px; } }
'''

EXPLORER_CSS_BLOCK = r'''
:host { border-right-color: #1C2935; }
* { scrollbar-color: #26394B #070B10; }
button:hover { border-color: #26394B; }
'''

DISPATCH_CSS_BLOCK = r'''
:host { flex-basis: 410px; width: 410px; min-width: 370px; }
.lane {
  border-color: #1C2935;
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(8,20,36,.99), rgba(4,10,18,.99));
}
.header { padding: 10px 12px 9px; border-bottom-color: #1C2935; }
.title { font-size: 17px; color: #CBD5DF; }
.contract { padding: 7px 9px; border-bottom-color: #1C2935; }
.contract span { border-radius: 5px; }
.queue { padding: 9px; }
.worksDrop { border-color: rgba(58,184,255,.26); background: rgba(7,18,31,.78); }
.footer { border-top-color: #1C2935; background: #070B10; }
'''


def run_build(label: str) -> int:
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    safe_emit(f"RUN={npm} run build")
    result = subprocess.run(
        [npm, "run", "build"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    safe_emit(result.stdout, sys.stdout)
    if result.stderr:
        safe_emit(result.stderr, sys.stderr)
    safe_emit(f"{label}_EXIT={result.returncode}")
    return result.returncode


def main() -> None:
    print("=== VERTEX SESSION PORTAL / MOCK FIDELITY + STREAM STABILITY APPLY 000049 ===")
    print(f"ROOT={ROOT}")
    print(f"TRANSACTION_BACKUP={BACKUP}")
    backup()

    originals = {path: read(path) for path in TOUCH}

    try:
        write(MAINFRAME, patch_mainframe(originals[MAINFRAME]))
        write(BROWSER, patch_browser(originals[BROWSER]))
        write(MAIN, patch_main(originals[MAIN]))

        append_css_patch(MAINFRAME_CSS, MAINFRAME_CSS_BLOCK)
        append_css_patch(BROWSER_CSS, BROWSER_CSS_BLOCK)
        append_css_patch(SCALER_CSS, SCALER_CSS_BLOCK)
        append_css_patch(EXPLORER_CSS, EXPLORER_CSS_BLOCK)
        append_css_patch(DISPATCH_CSS, DISPATCH_CSS_BLOCK)

        if run_build("PATCHED_BUILD") != 0:
            raise RuntimeError("SESSION_PORTAL_000049_BUILD_FAILED")

    except Exception:
        restore()
        print("TRANSACTION_ROLLBACK=PASS")
        raise

    print("TRANSACTION_ROLLBACK=NOT_REQUIRED")
    print("TOP_LEFT_BRANDING=POLISHED")
    print("PRIMARY_ENTRY_UI=VISIBLE")
    print("VERA_04_05_ASSIGNMENT_CHROME=RETIRED")
    print("DISPATCH_VRA_SAVE_PATH_PANEL=ACTIVE")
    print("WEBVIEW_BACKGROUND_THROTTLING=DISABLED")
    print("CHATGPT_FORCE_RECOVERY_CONTROL=ACTIVE")
    print("CANONICAL_RELEASE_POLICY=000044_PLUS_000047")
    print("VERTEX_SESSION_PORTAL_MOCK_FIDELITY_STABILITY_000049_APPLY=PASS")


if __name__ == "__main__":
    main()
