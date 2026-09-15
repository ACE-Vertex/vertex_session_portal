from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / 'src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css'
TS = ROOT / 'src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts'
MAIN = ROOT / 'src/main/index.ts'
FRAME = ROOT / 'src/renderer/src/components/MainFrame/MainFrame.ts'

def block(text: str, selector: str) -> str:
    m = re.search(rf'{re.escape(selector)}\s*\{{(.*?)\}}', text, re.S)
    if not m:
        raise AssertionError(f'missing css block: {selector}')
    return m.group(1)

def check(name: str, ok: bool) -> None:
    print(f'{name}={"PASS" if ok else "FAIL"}')
    if not ok:
        raise AssertionError(name)

def run_build() -> None:
    print('RUN=npm.cmd run build')
    cp = subprocess.run(
        ['npm.cmd', 'run', 'build'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        errors='replace'
    )
    if cp.returncode != 0:
        sys.stdout.write(cp.stdout.encode('ascii', 'backslashreplace').decode('ascii'))
        sys.stderr.write(cp.stderr.encode('ascii', 'backslashreplace').decode('ascii'))
        print('BUILD=FAIL')
        raise SystemExit(cp.returncode)
    print('BUILD=PASS')

def main() -> None:
    print('VERTEX SESSION PORTAL / CHATGPT WEBVIEW FLOW HEIGHT REPAIR VERIFY 000039H1')
    print(f'ROOT={ROOT}')

    css = CSS.read_text(encoding='utf-8')
    ts = TS.read_text(encoding='utf-8')
    main = MAIN.read_text(encoding='utf-8')
    frame = FRAME.read_text(encoding='utf-8')

    body = block(css, '.browserBody')
    view = block(css, '.chatgptView')

    check('BROWSER_BODY_FLEX_FLOW', 'display:flex' in body.replace(' ', ''))
    check('WEBVIEW_ABSOLUTE_RETIRED', 'position:absolute' not in view.replace(' ', ''))
    check('WEBVIEW_RELATIVE_FLOW', 'position:relative' in view.replace(' ', ''))
    check('WEBVIEW_FLEX_FILL', 'flex:1 1 auto' in view)
    check('WEBVIEW_STRETCH', 'align-self:stretch' in view.replace(' ', ''))
    check('WEBVIEW_WIDTH_100', 'width:100%' in view.replace(' ', ''))
    check('WEBVIEW_HEIGHT_100', 'height:100%' in view.replace(' ', ''))
    check('BLACK_BACKING_PRESERVED', 'background:#000' in body.replace(' ', '') and 'background:#000' in view.replace(' ', ''))
    check('WHITE_LINE_GUARD_PRESERVED', 'line-height:0' in body.replace(' ', '') and 'box-shadow:inset 0 -1px 0 #000' in body)
    check('WEBVIEW_BORDER_ZERO_PRESERVED', 'border:0 !important' in view)
    check('ACTIVE_NEON_PRESERVED', ':host([active-window]) .session' in css)
    check('VERA_600_WIDTH_PRESERVED', '--session-user-width: var(--vertex-session-min-width)' in css and 'min-width: var(--vertex-session-min-width)' in css)
    check('THREAD_BRIDGE_PRESERVED', 'updateVeraSessionThread' in ts and 'THREAD MAP · VCA CLOCK BRIDGE' in ts)
    check('PERSIST_PARTITION_PRESERVED', "persist:vertex-vera-chatgpt" in ts)
    check('VRA_DISPATCH_LANE_PRESERVED', '<vertex-vra-dispatch-lane></vertex-vra-dispatch-lane>' in frame)
    check('INITIAL_WINDOW_3200X1300_PRESERVED', 'width: 3200' in main and 'height: 1300' in main)
    check('NO_CHATGPT_DOM_SCRAPE', 'executeJavaScript' not in ts)

    run_build()
    print('VERTEX_SESSION_PORTAL_CHATGPT_WEBVIEW_FLOW_HEIGHT_REPAIR_000039H1=PASS')

if __name__ == '__main__':
    main()
