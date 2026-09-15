from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    (
        'VRA_DISPATCH_CONTRACT',
        'src/shared/contracts.ts',
        [
            'VRA_WORKS_DISPATCH_CONTRACT',
            "capture: 'CHATGPT_BROWSER_DOWNLOAD_VRA_ONLY'",
            "applyAuthority: 'HUMAN_APPLY'",
            "browserDomScrape: 'NO'",
        ],
    ),
    (
        'VRA_DISPATCH_API',
        'src/shared/contracts.ts',
        [
            'getVraDispatchState(): Promise<VraDispatchState>',
            'registerVraWebviewSource(request: RegisterVraWebviewSourceRequest)',
            'dispatchVraCard(cardId: string): Promise<VraDispatchCard>',
            'removeVraCard(cardId: string): Promise<VraDispatchState>',
        ],
    ),
    (
        'VRA_DOWNLOAD_CAPTURE',
        'src/main/vra/vra-dispatch-service.ts',
        [
            "target.on('will-download'",
            "extname(filename).toLowerCase() !== '.vra'",
            'item.setSavePath(stagedPath)',
            'captureCompleted(',
        ],
    ),
    (
        'VRA_SHA256_GUARD',
        'src/main/vra/vra-dispatch-service.ts',
        [
            "createHash('sha256')",
            "STAGED_VRA_SHA256_MISMATCH",
            'duplicate = this.cards.find(card => card.sha256 === sha256)',
        ],
    ),
    (
        'WORKS_RECEIVING_COPY_ONLY',
        'src/main/vra/vra-dispatch-service.ts',
        [
            'copyFileSync(card.stagedPath, destination)',
            "resolve(process.cwd(), '..', '_incoming')" if False else 'worksIncomingRoot',
            "card.status = 'DISPATCHED'",
        ],
    ),
    (
        'VRA_SOURCE_LANE_MAP',
        'src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts',
        [
            'getWebContentsId: () => number',
            'registerVraDownloadSource(browser)',
            'window.vertexPortal.registerVraWebviewSource',
        ],
    ),
    (
        'VRA_PRELOAD_BRIDGE',
        'src/preload/index.ts',
        [
            "ipcRenderer.invoke('workstation:vra-dispatch-state')",
            "ipcRenderer.invoke('workstation:vra-dispatch-card', cardId)",
            "ipcRenderer.on('vra-dispatch:changed', wrapped)",
        ],
    ),
    (
        'VRA_IPC_REGISTERED',
        'src/main/ipc/register-vra-dispatch-ipc.ts',
        [
            "'workstation:vra-dispatch-state'",
            "'workstation:vra-register-webview-source'",
            "'workstation:vra-dispatch-card'",
        ],
    ),
    (
        'VRA_SERVICE_BOOTSTRAP',
        'src/main/index.ts',
        [
            'new VraDispatchService(',
            'electronSession.fromPartition(VERA_CHATGPT_PARTITION)',
            'registerVraDispatchIpc(vraDispatchService)',
            "mainWindow?.webContents.send('vra-dispatch:changed')",
            "resolve(process.cwd(), '..', '_incoming')",
        ],
    ),
    (
        'VRA_DISPATCH_LANE_UI',
        'src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts',
        [
            'VRA / WORKS LOGISTICS',
            'Dispatch Bay',
            'SEND TO WORKS',
            'WORKS RECEIVING BAY',
            "application/x-vertex-vra-card",
            'HUMAN_APPLY REMAINS IN WORKS',
        ],
    ),
    (
        'VRA_LANE_MOUNTED_AFTER_VERA',
        'src/renderer/src/components/MainFrame/MainFrame.ts',
        [
            "import '../VraDispatchLane/VraDispatchLane'",
            '<vertex-vra-dispatch-lane></vertex-vra-dispatch-lane>',
        ],
    ),
    (
        'SEARCH_VERA_STAYS_RETIRED',
        'src/renderer/src/components/MainFrame/MainFrame.ts',
        [
            "if (session.kind !== 'MAIN') return ''",
        ],
    ),
]


def check() -> None:
    print('VERTEX SESSION PORTAL / VRA WORKS DISPATCH LANE VERIFY 000038')
    print(f'ROOT={ROOT}')

    failures: list[str] = []
    for label, relative, needles in CHECKS:
        path = ROOT / relative
        if not path.exists():
            print(f'{label}=FAIL missing_file={relative}')
            failures.append(label)
            continue
        text = path.read_text(encoding='utf-8')
        missing = [needle for needle in needles if needle not in text]
        if missing:
            print(f'{label}=FAIL missing={missing!r}')
            failures.append(label)
        else:
            print(f'{label}=PASS')

    combined = '\n'.join(
        (ROOT / rel).read_text(encoding='utf-8')
        for rel in [
            'src/main/vra/vra-dispatch-service.ts',
            'src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts',
            'src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts',
        ]
        if (ROOT / rel).exists()
    )
    forbidden = ['executeJavaScript(', 'HUMAN_AUTO_APPLY', 'child_process', 'spawn(', 'exec(']
    bad = [token for token in forbidden if token in combined]
    if bad:
        print(f'NO_BROWSER_DOM_SCRAPE_OR_AUTO_APPLY=FAIL forbidden={bad!r}')
        failures.append('NO_BROWSER_DOM_SCRAPE_OR_AUTO_APPLY')
    else:
        print('NO_BROWSER_DOM_SCRAPE_OR_AUTO_APPLY=PASS')

    project_tree_files = [
        ROOT / 'src/renderer/src/components/Explorer/Explorer.ts',
        ROOT / 'src/renderer/src/components/Explorer/Explorer.css',
    ]
    if all(path.exists() for path in project_tree_files):
        print('PROJECT_TREE_RESERVED=PASS')
    else:
        print('PROJECT_TREE_RESERVED=FAIL')
        failures.append('PROJECT_TREE_RESERVED')

    if failures:
        raise SystemExit('STATIC_VERIFY_FAIL:' + ','.join(failures))

    command = ['npm.cmd', 'run', 'build'] if sys.platform.startswith('win') else ['npm', 'run', 'build']
    print('RUN=' + ' '.join(command))
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='backslashreplace')
    if result.returncode != 0:
        print('BUILD=FAIL')
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise SystemExit(result.returncode)

    print('BUILD=PASS')
    print('VERTEX_SESSION_PORTAL_VRA_WORKS_DISPATCH_LANE_000038=PASS')


if __name__ == '__main__':
    check()
