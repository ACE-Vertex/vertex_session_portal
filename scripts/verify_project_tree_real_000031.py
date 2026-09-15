from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    'contracts': ROOT / 'src/shared/contracts.ts',
    'service': ROOT / 'src/main/project/project-tree-service.ts',
    'ipc': ROOT / 'src/main/ipc/register-project-tree-ipc.ts',
    'main': ROOT / 'src/main/index.ts',
    'preload': ROOT / 'src/preload/index.ts',
    'explorer': ROOT / 'src/renderer/src/components/Explorer/Explorer.ts',
    'css': ROOT / 'src/renderer/src/components/Explorer/Explorer.css',
}


def read(name: str) -> str:
    return FILES[name].read_text(encoding='utf-8')


def check(label: str, ok: bool) -> None:
    print(f'{label}={"PASS" if ok else "FAIL"}')
    if not ok:
        raise SystemExit(1)


def safe_emit(text: str) -> None:
    encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
    payload = text.encode(encoding, errors='backslashreplace').decode(encoding, errors='ignore')
    print(payload)


def main() -> None:
    print('VERTEX SESSION PORTAL / PROJECT TREE REAL VERIFY 000031')
    print(f'ROOT={ROOT}')

    contracts = read('contracts')
    service = read('service')
    ipc = read('ipc')
    main_ts = read('main')
    preload = read('preload')
    explorer = read('explorer')
    css = read('css')

    check('REAL_FILESYSTEM_CONTRACT', "source: 'REAL_FILESYSTEM'" in contracts)
    check('PROJECT_ROOT_SCOPE_CONTRACT', "scope: 'PROJECT_ROOT_ONLY'" in contracts)
    check('READ_ONLY_CONTRACT', "writes: 'NO'" in contracts)
    check('REAL_READDIR', "readdirSync(directoryPath, { withFileTypes: true })" in service)
    check('DIRECTORY_FIRST_SORT', "left.kind === 'DIRECTORY' ? 0 : 1" in service and 'localeCompare' in service)
    check('ROOT_ESCAPE_GUARD', "throw new Error('PROJECT_TREE_OUTSIDE_ROOT')" in service and "rel.startsWith('..')" in service)
    check('SYMLINK_NO_TRAVERSAL', "entry.isSymbolicLink()" in service and "expandable: kind === 'DIRECTORY'" in service)
    check('NO_FILESYSTEM_MUTATION', all(token not in service for token in ['writeFile', 'unlink', 'rmSync', 'renameSync', 'mkdirSync', 'copyFileSync']))

    check('TREE_IPC_LIST', "'project-tree:list'" in ipc)
    check('TREE_IPC_RESOLVE', "'project-tree:resolve'" in ipc)
    check('TREE_IPC_OPEN', "'project-tree:open'" in ipc)
    check('TREE_IPC_REVEAL', "'project-tree:reveal'" in ipc)
    check('TREE_IPC_COPY_PATH', "'project-tree:copy-path'" in ipc)
    check('TREE_SERVICE_BOOTSTRAP', 'registerProjectTreeIpc' in main_ts and 'new ProjectTreeService(process.cwd())' in main_ts)

    check('TREE_PRELOAD_LIST', 'listProjectTree:' in preload and "'project-tree:list'" in preload)
    check('TREE_PRELOAD_RESOLVE', 'resolveProjectTreePath:' in preload)
    check('TREE_PRELOAD_OPEN', 'openProjectTreePath:' in preload)
    check('TREE_PRELOAD_REVEAL', 'revealProjectTreePath:' in preload)
    check('TREE_PRELOAD_COPY', 'copyProjectTreePath:' in preload)

    check('FAKE_TREE_RETIRED', '<span>src</span>' not in explorer and '<span>docs</span>' not in explorer and '<span>scripts</span>' not in explorer)
    check('LAZY_EXPANSION', 'toggleProjectDirectory' in explorer and 'projectLoaded' in explorer and 'listProjectTree(path)' in explorer)
    check('FOLDER_FILE_TYPES', 'data-kind="${node.kind}"' in explorer and "node.kind === 'DIRECTORY'" in explorer)
    check('SELECTION_STATE', 'projectSelectedPath' in explorer and 'data-selected' in explorer)
    check('SELECTION_PERSISTENCE', 'localStorage.setItem(this.projectTreeStorageKey()' in explorer and 'restoreProjectTreeUi' in explorer)
    check('DOUBLE_CLICK_OPEN', "row.addEventListener('dblclick'" in explorer and 'openProjectTreePath(path)' in explorer)
    check('RIGHT_CLICK_CONTEXT_MENU', "row.addEventListener('contextmenu'" in explorer and 'data-tree-menu="reveal"' in explorer and 'data-tree-menu="copy"' in explorer)
    check('REFRESH_CONTROL', 'refreshProjectDirectory' in explorer and 'data-action="project-refresh"' in explorer)
    check('PROJECT_REVEAL_REAL', 'resolveProjectTreePath(path)' in explorer and 'revealProjectNode' in explorer)
    check('KEYBOARD_NAV', "event.key === 'ArrowRight'" in explorer and "event.key === 'ArrowLeft'" in explorer and "event.key === 'F5'" in explorer)
    check('GUIDE_LINES', '.treeIndent' in css and 'repeating-linear-gradient' in css)
    check('CONTEXT_MENU_STYLE', '.treeContextMenu' in css)

    check('VRA_DISPATCH_PRESERVED', 'registerVraDispatchIpc(vraDispatchService)' in main_ts)
    check('PROJECT_TREE_DEDICATED', 'VraDispatchLane' not in explorer)

    print('RUN=npm.cmd run build')
    result = subprocess.run(
        ['npm.cmd', 'run', 'build'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    if result.returncode != 0:
        print('BUILD=FAIL')
        safe_emit(result.stdout)
        safe_emit(result.stderr)
        raise SystemExit(result.returncode or 1)

    print('BUILD=PASS')
    print('VERTEX_SESSION_PORTAL_PROJECT_TREE_REAL_000031=PASS')


if __name__ == '__main__':
    main()
