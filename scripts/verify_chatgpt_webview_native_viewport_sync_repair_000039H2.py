from pathlib import Path
import subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
TS=ROOT/'src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts'
CSS=ROOT/'src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css'
MF=ROOT/'src/renderer/src/components/MainFrame/MainFrame.css'

def check(name, ok):
    print(f'{name}={"PASS" if ok else "FAIL"}')
    if not ok: failures.append(name)

failures=[]
ts=TS.read_text(encoding='utf-8')
css=CSS.read_text(encoding='utf-8')
mf=MF.read_text(encoding='utf-8')
print('VERTEX SESSION PORTAL / CHATGPT WEBVIEW NATIVE VIEWPORT SYNC REPAIR VERIFY 000039H2')
print('ROOT='+str(ROOT))
check('RESIZE_OBSERVER_PRESENT', 'new ResizeObserver' in ts and 'browserViewportObserver' in ts)
check('BODY_RECT_MEASURED', "querySelector<HTMLElement>('.browserBody')" in ts and 'getBoundingClientRect()' in ts)
check('EXACT_PIXEL_WIDTH_SYNC', 'browser.style.width = widthPx' in ts)
check('EXACT_PIXEL_HEIGHT_SYNC', 'browser.style.height = heightPx' in ts)
check('RAF_COALESCING', 'requestAnimationFrame' in ts and 'cancelAnimationFrame' in ts)
check('OBSERVER_CLEANUP', 'stopBrowserViewportSync()' in ts and '.disconnect()' in ts)
check('SYNC_AFTER_RENDER', 'this.startBrowserViewportSync()' in ts)
check('SYNC_ON_READY', 'this.scheduleBrowserViewportSync()' in ts and "browser.addEventListener('dom-ready', markReady)" in ts)
check('BROWSER_BODY_WIDTH_100', '.browserBody {' in css and 'width:100%' in css)
check('BROWSER_BODY_HEIGHT_100', '.browserBody {' in css and 'height:100%' in css)
check('WEBVIEW_FLEX_PRESERVED', '.chatgptView {' in css and 'flex:1 1 auto' in css)
check('WEBVIEW_HEIGHT_100_PRESERVED', '.chatgptView {' in css and 'height:100%' in css)
check('MAIN_HEIGHT_CHAIN_PRESERVED', '.sessionTrack' in mf and 'height:100%' in mf and '.sessionViewport' in mf and 'min-height:0' in mf)
check('NO_CHATGPT_DOM_SCRAPE', 'executeJavaScript' not in ts and '.getWebContents().executeJavaScript' not in ts)
check('PERSIST_PARTITION_PRESERVED', "persist:vertex-vera-chatgpt" in ts)
check('THREAD_BRIDGE_PRESERVED', 'updateVeraSessionThread' in ts)
check('VRA_DOWNLOAD_BRIDGE_PRESERVED', 'registerVraWebviewSource' in ts)
check('VERA_600_WIDTH_PRESERVED', '--vertex-session-min-width' in css and '--session-user-width' in css)
if failures:
    print('VERTEX_SESSION_PORTAL_CHATGPT_WEBVIEW_NATIVE_VIEWPORT_SYNC_REPAIR_000039H2=FAIL')
    print('FAILURES='+','.join(failures))
    raise SystemExit(1)
print('RUN=npm.cmd run build')
cp=subprocess.run(['npm.cmd','run','build'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
if cp.returncode:
    print('BUILD=FAIL')
    if cp.stdout: print(cp.stdout.encode('ascii','backslashreplace').decode('ascii'))
    if cp.stderr: print(cp.stderr.encode('ascii','backslashreplace').decode('ascii'))
    raise SystemExit(cp.returncode)
print('BUILD=PASS')
print('VERTEX_SESSION_PORTAL_CHATGPT_WEBVIEW_NATIVE_VIEWPORT_SYNC_REPAIR_000039H2=PASS')
