from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / 'src/renderer/src/shared/tokens.css'
MAIN = ROOT / 'src/renderer/src/components/MainFrame/MainFrame.ts'
BROWSER_TS = ROOT / 'src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts'
BROWSER_CSS = ROOT / 'src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css'


def need(label: str, condition: bool) -> None:
    print(f'{label}={"PASS" if condition else "FAIL"}')
    if not condition:
        raise SystemExit(1)


def main() -> None:
    print('VERTEX SESSION PORTAL / VERA 600 DRAG + SEARCH RETIRE VERIFY 000037')
    print(f'ROOT={ROOT}')

    tokens = TOKENS.read_text(encoding='utf-8')
    frame = MAIN.read_text(encoding='utf-8')
    browser_ts = BROWSER_TS.read_text(encoding='utf-8')
    browser_css = BROWSER_CSS.read_text(encoding='utf-8')

    need('VERA_BASE_600', '--vertex-session-min-width: 600px;' in tokens)
    need('PRIORITY_WIDTH_NEUTRALIZED', '--vertex-session-priority-width: 600px;' in tokens)
    need('SEARCH_VERA_IMPORT_RETIRED', "import '../SearchVera/SearchVera'" not in frame)
    need('SEARCH_VERA_RENDER_RETIRED', '<search-vera' not in frame)
    need('MAIN_LANES_ONLY', "session.active && session.kind === 'MAIN'" in frame)

    need('LANE_WIDTH_EXACT_USER_VAR', 'flex: 0 0 var(--session-user-width);' in browser_css)
    need('LANE_MIN_600_TOKEN', 'min-width: var(--vertex-session-min-width);' in browser_css)
    need('PRIORITY_NO_SIZE_RULE', ':host([priority]) {' not in browser_css)
    need('PRIORITY_VISUAL_ONLY', ':host([priority]) .session {' in browser_css)

    need('PER_LANE_WIDTH_STORAGE', 'vertex.vera.browser.width.${this.sessionId()}' in browser_ts)
    need('WIDTH_RESTORE', 'private restoreWidth(): void' in browser_ts and 'this.restoreWidth()' in browser_ts)
    need('WIDTH_PERSIST', 'private persistWidth(width: number): void' in browser_ts)
    need('DRAG_RESIZE', "handle.addEventListener('pointerdown'" in browser_ts and '--session-user-width' in browser_ts)
    need('RESET_TO_600', 'private resetWidth(): void' in browser_ts and "window.localStorage.removeItem(this.widthStorageKey())" in browser_ts)
    need('EXPAND_BUTTON_RETIRED', 'data-action="expand"' not in browser_ts)
    need('HEADER_DBLCLICK_EXPAND_RETIRED', "addEventListener('dblclick', () => this.emitPriority())" not in browser_ts)
    need('PRIORITY_EMIT_RETIRED', 'private emitPriority()' not in browser_ts)
    need('PROJECT_TREE_UNTOUCHED', not (ROOT / 'docs/ARCHITECTURE/PROJECT_EXPLORER_TREE_000031.md').exists())

    command = ['npm.cmd', 'run', 'build'] if sys.platform.startswith('win') else ['npm', 'run', 'build']
    print('RUN=' + ' '.join(command))
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode != 0:
        print('BUILD=FAIL')
        output = (completed.stdout or '') + (completed.stderr or '')
        print(output.encode('ascii', 'backslashreplace').decode('ascii'))
        raise SystemExit(completed.returncode)

    print('BUILD=PASS')
    print('VERTEX_SESSION_PORTAL_VERA_600_DRAG_SEARCH_RETIRE_000037=PASS')


if __name__ == '__main__':
    main()
