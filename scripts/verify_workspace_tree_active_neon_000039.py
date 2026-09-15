from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')

def check(name: str, ok: bool) -> None:
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        raise SystemExit(1)

print('VERTEX SESSION PORTAL / WORKSPACE TREE + ACTIVE NEON VERIFY 000039')
print(f'ROOT={ROOT}')

service = read('src/main/project/project-tree-service.ts')
contracts = read('src/shared/contracts.ts')
explorer = read('src/renderer/src/components/Explorer/Explorer.ts')
explorer_css = read('src/renderer/src/components/Explorer/Explorer.css')
frame = read('src/renderer/src/components/MainFrame/MainFrame.ts')
vera = read('src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts')
vera_css = read('src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css')

check('WORKSPACE_SCOPE_CONTRACT', "scope: 'VERTEX_WORKSPACE_NAVIGATION'" in contracts)
check('WORKSPACE_BOUNDARY_DERIVED', "basename(parent).toLowerCase() === 'development'" in service and 'workspaceRootPath' in service)
check('WORKSPACE_ESCAPE_GUARD', 'PROJECT_TREE_OUTSIDE_WORKSPACE' in service)
check('WORKSPACE_READ_ONLY_PRESERVED', 'readdirSync' in service and all(token not in service for token in ['writeFile', 'unlink', 'rename(', 'mkdirSync', 'rmSync']))
check('BREADCRUMB_METADATA', 'ProjectTreeBreadcrumb' in contracts and 'breadcrumbs:' in service and 'parentPath:' in service)
check('TREE_UP_CONTROL', 'data-action="project-up"' in explorer and 'projectParentPath' in explorer)
check('TREE_HOME_CONTROL', 'data-action="project-home"' in explorer and 'projectCanonicalRootPath' in explorer)
check('TREE_BREADCRUMB_CONTROL', 'data-project-breadcrumb' in explorer and 'projectBreadcrumbs' in explorer)
check('TREE_ROOT_NAVIGATION', 'navigateProjectRoot' in explorer and 'OPEN AS TREE ROOT' in explorer)
check('TREE_INLINE_LAZY_EXPANSION_PRESERVED', 'toggleProjectDirectory' in explorer and 'projectLoaded' in explorer)
check('TREE_NAV_PERSISTED', 'project-tree-root:000039' in explorer)
check('TREE_BREADCRUMB_STYLE', '.projectBreadcrumbs' in explorer_css and '.projectTreeActions' in explorer_css)
check('CANONICAL_PROJECT_MARK', 'data-canonical' in explorer and 'PROJECT"' in explorer_css)
check('VISUAL_ACTIVE_EVENT', 'vertex-session-visual-active' in vera and 'vertex-session-visual-active' in frame)
check('VISUAL_ACTIVE_RENDERER_ONLY', "toggleAttribute('active-window'" in frame and 'setPrioritySession(sessionId)' not in frame[frame.find('onSessionVisualActive'):frame.find('private async bootstrap')])
check('ACTIVE_WATER_CYAN_NEON', ':host([active-window]) .session' in vera_css and 'rgba(121,239,255,.92)' in vera_css)
check('INACTIVE_PRIORITY_GLOW_RETIRED', ':host([priority]) .session' not in vera_css)
check('ACTIVE_STATE_LABEL', ".chromeState::after { content:'VERA BROWSER'; }" in vera_css and "content:'ACTIVE'" in vera_css)
check('WHITE_BACKING_RETIRED', 'background:#fff' not in vera_css and '.browserBody' in vera_css and 'background:#000' in vera_css)
check('WEBVIEW_PIXEL_FILL', 'position:absolute' in vera_css and 'inset:0' in vera_css and 'border:0 !important' in vera_css)
check('VRA_DISPATCH_PRESERVED', '<vertex-vra-dispatch-lane></vertex-vra-dispatch-lane>' in frame)
check('SEARCH_VERA_STAYS_RETIRED', 'SearchVera' not in frame and '<search-vera' not in frame)
check('DRAG_RESIZE_PRESERVED', 'bindResize' in vera and 'resizeRail' in vera)

print('RUN=npm.cmd run build')
proc = subprocess.run(
    ['npm.cmd', 'run', 'build'],
    cwd=ROOT,
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace'
)
if proc.returncode != 0:
    print('BUILD=FAIL')
    if proc.stdout:
        print(proc.stdout.encode(sys.stdout.encoding or 'utf-8', errors='backslashreplace').decode(sys.stdout.encoding or 'utf-8', errors='replace'))
    if proc.stderr:
        print(proc.stderr.encode(sys.stdout.encoding or 'utf-8', errors='backslashreplace').decode(sys.stdout.encoding or 'utf-8', errors='replace'))
    raise SystemExit(proc.returncode)
print('BUILD=PASS')
print('VERTEX_SESSION_PORTAL_WORKSPACE_TREE_ACTIVE_NEON_000039=PASS')
