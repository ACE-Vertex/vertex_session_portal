from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'src' / 'main' / 'index.ts'

print('VERTEX SESSION PORTAL / INITIAL WINDOW SIZE 3200X1300 VERIFY 000040')
print(f'ROOT={ROOT}')

text = INDEX.read_text(encoding='utf-8')

def check(name: str, ok: bool):
    print(f'{name}=' + ('PASS' if ok else 'FAIL'))
    if not ok:
        raise SystemExit(1)

check('MAIN_WINDOW_WIDTH_3200', bool(re.search(r'new\s+BrowserWindow\s*\(\s*\{[\s\S]*?\bwidth\s*:\s*3200\s*,', text)))
check('MAIN_WINDOW_HEIGHT_1300', bool(re.search(r'new\s+BrowserWindow\s*\(\s*\{[\s\S]*?\bheight\s*:\s*1300\s*,', text)))
check('MIN_WIDTH_PRESERVED', 'minWidth: 1100' in text)
check('MIN_HEIGHT_PRESERVED', 'minHeight: 720' in text)
check('NO_FORCED_MAXIMIZE', '.maximize()' not in text)
check('NO_FORCED_FULLSCREEN', 'fullScreen: true' not in text and '.setFullScreen(true)' not in text)
check('CHATGPT_PERSIST_PARTITION_PRESERVED', "persist:vertex-vera-chatgpt" in text)
check('VRA_DISPATCH_BOOTSTRAP_PRESERVED', 'registerVraDispatchIpc' in text)
check('PROJECT_TREE_BOOTSTRAP_PRESERVED', 'registerProjectTreeIpc' in text)

print('RUN=npm.cmd run build')
proc = subprocess.run(
    ['npm.cmd', 'run', 'build'],
    cwd=ROOT,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding='utf-8',
    errors='replace',
)
if proc.returncode != 0:
    print('BUILD=FAIL')
    sys.stdout.write(proc.stdout.encode('ascii', 'backslashreplace').decode('ascii'))
    raise SystemExit(proc.returncode)
print('BUILD=PASS')
print('VERTEX_SESSION_PORTAL_INITIAL_WINDOW_SIZE_3200X1300_000040=PASS')
