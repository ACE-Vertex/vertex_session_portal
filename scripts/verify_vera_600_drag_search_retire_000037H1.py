from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')


def need(label: str, condition: bool) -> None:
    print(f'{label}={"PASS" if condition else "FAIL"}')
    if not condition:
        raise SystemExit(1)


def safe(text: str) -> str:
    enc = getattr(sys.stdout, 'encoding', None) or 'utf-8'
    try:
        return text.encode(enc, errors='backslashreplace').decode(enc, errors='replace')
    except LookupError:
        return text.encode('ascii', errors='backslashreplace').decode('ascii')


def main() -> None:
    print('VERTEX SESSION PORTAL / VERA 600 DRAG + SEARCH RETIRE VERIFY 000037H1')
    print(f'ROOT={ROOT}')

    contracts = read('src/shared/contracts.ts')
    db = read('src/main/storage/workstation-db.ts')
    ipc = read('src/main/ipc/register-workstation-ipc.ts')
    preload = read('src/preload/index.ts')
    curator = read('src/main/memory/vca-curator-service.ts')
    explorer = read('src/renderer/src/components/Explorer/Explorer.ts')
    frame = read('src/renderer/src/components/MainFrame/MainFrame.ts')
    browser = read('src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts')
    browser_css = read('src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css')
    tokens = read('src/renderer/src/shared/tokens.css')

    # Missing 000036 prerequisite surface.
    need('THREAD_UPDATE_CONTRACT_RESTORED',
         'updateVeraSessionThread(request: UpdateVeraSessionThreadRequest)' in contracts)
    need('THREAD_UPDATE_REQUEST_TYPE_RESTORED',
         'export interface UpdateVeraSessionThreadRequest' in contracts)
    need('THREAD_UPDATE_PRELOAD_RESTORED',
         'updateVeraSessionThread:' in preload and "'workstation:vera-thread-update'" in preload)
    need('THREAD_BINDING_IPC_RESTORED',
         "'workstation:vera-thread-bindings'" in ipc and "'workstation:vera-thread-update'" in ipc)
    need('THREAD_BINDING_DB_RESTORED',
         'getVeraSessionThreadBindings()' in db and 'updateVeraSessionThread(request:' in db)
    need('VCA_INBOX_CONTRACT_RESTORED',
         "purpose: 'SESSION_TO_VERTEX_MEMORY_BOUNDARY'" in contracts)
    need('VCA_INBOX_DB_RESTORED',
         'CREATE TABLE IF NOT EXISTS vca_memory_inbox' in db)
    need('VCA_INBOX_PRELOAD_RESTORED',
         'getVcaInbox:' in preload and 'enqueueVcaInbox:' in preload)
    need('CURATOR_INBOX_RELAY_RESTORED',
         'markVcaInboxCuratedByEvent' in curator)
    need('VCA_INBOX_UI_RESTORED',
         'VCA MEMORY INBOX' in explorer and 'SESSION → VERTEX MEMORY BOUNDARY' in explorer)
    need('BROWSER_THREAD_REPORT_COMPILES_AGAINST_CONTRACT',
         'window.vertexPortal.updateVeraSessionThread({' in browser)

    # Preserve 000037 behavior.
    need('VERA_BASE_600_PRESERVED', '--vertex-session-min-width: 600px;' in tokens)
    need('SEARCH_VERA_RENDER_RETIRED_PRESERVED', '<search-vera' not in frame)
    need('LANE_WIDTH_USER_VAR_PRESERVED', 'flex: 0 0 var(--session-user-width);' in browser_css)
    need('WIDTH_PERSIST_PRESERVED', 'vertex.vera.browser.width.${this.sessionId()}' in browser)
    need('DRAG_RESIZE_PRESERVED', "handle.addEventListener('pointerdown'" in browser)
    need('EXPAND_BUTTON_RETIRED_PRESERVED', 'data-action="expand"' not in browser)
    need('NO_BROWSER_DOM_SCRAPE', 'executeJavaScript' not in browser)
    need('PROJECT_TREE_RESERVED', not (ROOT / 'docs/ARCHITECTURE/PROJECT_EXPLORER_TREE_000031.md').exists())

    command = ['npm.cmd', 'run', 'build'] if sys.platform.startswith('win') else ['npm', 'run', 'build']
    print('RUN=' + ' '.join(command))
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, encoding='utf-8', errors='replace')
    if completed.returncode != 0:
        print('BUILD=FAIL')
        output = (completed.stdout or '') + (completed.stderr or '')
        print(safe(output))
        raise SystemExit(completed.returncode)

    print('BUILD=PASS')
    print('VERTEX_SESSION_PORTAL_VERA_600_DRAG_SEARCH_RETIRE_000037H1=PASS')


if __name__ == '__main__':
    main()
