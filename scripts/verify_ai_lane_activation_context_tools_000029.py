from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

checks = [
    ('FIVE_MAIN_SESSION_SEED', ROOT/'src/main/storage/workstation-db.ts', "['vera-05', 'Vera 05', 'MAIN', 5, 0, 0, now]"),
    ('SEARCH_SEPARATE_POSITION_6', ROOT/'src/main/storage/workstation-db.ts', "['vera-search', 'Search Vera', 'SEARCH', 6, 1, 0, now]"),
    ('ADD_LANE_DB_METHOD', ROOT/'src/main/storage/workstation-db.ts', 'activateNextMainLane(): PortalBootstrapState'),
    ('ADD_LANE_IPC', ROOT/'src/main/ipc/register-workstation-ipc.ts', "'workstation:activate-next-main-lane'"),
    ('ADD_LANE_API', ROOT/'src/shared/contracts.ts', 'activateNextMainLane(): Promise<PortalBootstrapState>'),
    ('LANE4_VERA04', ROOT/'src/main/providers/provider-settings-store.ts', "laneId: 'lane-4', label: 'LANE 4', sessionId: 'vera-04'"),
    ('LANE5_VERA05', ROOT/'src/main/providers/provider-settings-store.ts', "laneId: 'lane-5', label: 'LANE 5', sessionId: 'vera-05'"),
    ('SEARCH_DEFAULT_NOT_LANE5', ROOT/'src/main/providers/provider-settings-store.ts', 'return direct?.laneId ?? null'),
    ('EXPLORER_ADD_BUTTON', ROOT/'src/renderer/src/components/Explorer/Explorer.ts', '⊕ ADD LANE'),
    ('EXPLORER_ACTIVE_COUNT', ROOT/'src/renderer/src/components/Explorer/Explorer.ts', 'ACTIVE LLM LANES · ${this.activeMainLanes}/5'),
    ('MAINFRAME_LANE_EVENT', ROOT/'src/renderer/src/components/MainFrame/MainFrame.ts', "'vertex-lanes-changed'"),
    ('CONTEXT_ATTACH_API', ROOT/'src/shared/contracts.ts', 'browseSessionContextFile(): Promise<SessionContextAttachment | null>'),
    ('CONTEXT_SCOPE_CONTRACT', ROOT/'src/shared/contracts.ts', "| 'PROJECT_EVIDENCE'"),
    ('ATTACH_PICKER', ROOT/'src/main/ipc/register-session-agent-ipc.ts', "'session-agent:browse-session-context-file'"),
    ('ATTACH_256KB_GUARD', ROOT/'src/main/ipc/register-session-agent-ipc.ts', 'SESSION_CONTEXT_FILE_TOO_LARGE_256KB_MAX'),
    ('ATTACH_COMPOSER_BUTTON', ROOT/'src/renderer/src/components/VeraSession/VeraSession.ts', 'Attach local text context'),
    ('TARGET_COMPOSER_BUTTON', ROOT/'src/renderer/src/components/VeraSession/VeraSession.ts', 'Choose context target:'),
    ('TARGET_MENU', ROOT/'src/renderer/src/components/VeraSession/VeraSession.ts', 'PROJECT + EVIDENCE'),
    ('ATTACH_CONTEXT_TO_PROVIDER', ROOT/'src/main/agents/session-agent-service.ts', 'User-selected local context attachments:'),
    ('SCOPE_RETRIEVAL', ROOT/'src/main/agents/session-agent-service.ts', "if (contextScope === 'PROJECT') return hit.source === 'PROJECT'"),
]

print('VERTEX SESSION PORTAL / AI LANE ACTIVATION + CONTEXT TOOLS VERIFY 000029')
print('ROOT=' + str(ROOT))
failed = []
for label, path, needle in checks:
    text = path.read_text(encoding='utf-8')
    ok = needle in text
    print(f'{label}=' + ('PASS' if ok else 'FAIL'))
    if not ok:
        failed.append(label)

# Dedicated patch boundary: VCR card/modal and Project Tree are deliberately not part of 000029.
explorer = (ROOT/'src/renderer/src/components/Explorer/Explorer.ts').read_text(encoding='utf-8')
print('VCR_MODAL_NOT_INTRODUCED=' + ('PASS' if 'vcrModal' not in explorer and 'VCR EDITOR' not in explorer else 'FAIL'))

if failed:
    raise SystemExit('STATIC_CONTRACT_FAILED:' + ','.join(failed))

print('RUN=npm.cmd run build')
r = subprocess.run(['npm.cmd', 'run', 'build'], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
if r.returncode != 0:
    print(r.stdout.encode('ascii', 'replace').decode('ascii'))
    print(r.stderr.encode('ascii', 'replace').decode('ascii'))
    raise SystemExit(r.returncode)

print('BUILD=PASS')
print('VERTEX_SESSION_PORTAL_AI_LANE_ACTIVATION_CONTEXT_TOOLS_000029=PASS')
