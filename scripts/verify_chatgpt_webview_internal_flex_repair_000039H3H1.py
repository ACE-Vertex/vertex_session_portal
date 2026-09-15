\
from pathlib import Path
import re, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
CSS=ROOT/'src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css'
TS=ROOT/'src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts'
MAIN=ROOT/'src/renderer/src/components/MainFrame/MainFrame.css'


def result(name, ok):
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok


def block(text, selector):
    m=re.search(re.escape(selector)+r"\s*\{(.*?)\}", text, re.S)
    return m.group(1) if m else ''


def main():
    print('VERTEX SESSION PORTAL / CHATGPT WEBVIEW INTERNAL FLEX REPAIR VERIFY 000039H3H1')
    print('ROOT='+str(ROOT))
    css=CSS.read_text(encoding='utf-8')
    ts=TS.read_text(encoding='utf-8')
    maincss=MAIN.read_text(encoding='utf-8')
    b=block(css,'.chatgptView')
    checks=[]
    checks.append(result('WEBVIEW_DISPLAY_FLEX', bool(re.search(r"display\s*:\s*flex\s*;", b))))
    checks.append(result('WEBVIEW_DISPLAY_BLOCK_RETIRED', not bool(re.search(r"display\s*:\s*block\s*;", b))))
    checks.append(result('WEBVIEW_WIDTH_100_PRESERVED', bool(re.search(r"width\s*:\s*100%\s*;", b))))
    checks.append(result('WEBVIEW_HEIGHT_100_PRESERVED', bool(re.search(r"height\s*:\s*100%\s*;", b))))
    checks.append(result('WEBVIEW_FLEX_FILL_PRESERVED', bool(re.search(r"flex\s*:\s*1\s+1\s+auto\s*;", b))))
    checks.append(result('H2_RESIZE_OBSERVER_PRESERVED', 'ResizeObserver' in ts and 'getBoundingClientRect()' in ts))
    checks.append(result('H2_EXACT_PIXEL_SYNC_PRESERVED', 'browser.style.height = heightPx' in ts and 'browser.style.width = widthPx' in ts))
    checks.append(result('MAIN_HEIGHT_CHAIN_PRESERVED', '.sessionTrack' in maincss and bool(re.search(r"height\s*:\s*100%\s*;", maincss))))
    checks.append(result('PERSIST_PARTITION_PRESERVED', 'persist:vertex-vera-chatgpt' in ts))
    checks.append(result('THREAD_BRIDGE_PRESERVED', 'updateVeraSessionThread' in ts))
    checks.append(result('VRA_DOWNLOAD_BRIDGE_PRESERVED', 'registerVraWebviewSource' in ts))
    checks.append(result('NO_CHATGPT_DOM_SCRAPE', 'executeJavaScript' not in ts))
    checks.append(result('VERIFIER_FALSE_NEGATIVE_RETIRED', "'flex:1 1 auto' in b.replace(' ', '')" not in Path(__file__).read_text(encoding='utf-8')))
    if not all(checks):
        print('VERTEX_SESSION_PORTAL_CHATGPT_WEBVIEW_INTERNAL_FLEX_REPAIR_000039H3H1=FAIL')
        raise SystemExit(1)
    print('RUN=npm.cmd run build')
    cp=subprocess.run(['npm.cmd','run','build'], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if cp.returncode != 0:
        print('BUILD=FAIL')
        sys.stdout.write(cp.stdout.encode('ascii','backslashreplace').decode('ascii'))
        print('VERTEX_SESSION_PORTAL_CHATGPT_WEBVIEW_INTERNAL_FLEX_REPAIR_000039H3H1=FAIL')
        raise SystemExit(cp.returncode)
    print('BUILD=PASS')
    print('VERTEX_SESSION_PORTAL_CHATGPT_WEBVIEW_INTERNAL_FLEX_REPAIR_000039H3H1=PASS')

if __name__=='__main__':
    main()
