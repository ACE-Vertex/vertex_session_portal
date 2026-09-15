from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

checks = []

def require(path: str, needle: str, label: str):
    text = (ROOT / path).read_text(encoding='utf-8')
    if needle not in text:
        raise RuntimeError(f'{label}=FAIL missing {needle!r} in {path}')
    checks.append(label)

require('src/shared/contracts.ts', "role: 'DEDICATED_AI_ASSISTANT'", 'CURATOR_ASSISTANT_ROLE')
require('src/shared/contracts.ts', "defaultLane: 'lane-4'", 'CURATOR_DEFAULT_LANE4')
require('src/shared/contracts.ts', "providerFallback: 'FORBIDDEN'", 'CURATOR_PROVIDER_FALLBACK_FORBIDDEN')
require('src/main/memory/vca-curator-service.ts', "if (!lane?.override)", 'NO_ASSISTANT_NO_RUN_GUARD')
require('src/main/memory/vca-curator-service.ts', 'Human and Vera are peer speakers.', 'HUMAN_VERA_PEER_PROMPT')
require('src/main/memory/vca-curator-service.ts', 'Age alone is not decay.', 'NO_TIME_DECAY_PROMPT')
require('src/main/memory/vca-curator-service.ts', 'AI_ASSISTANT:${settings.laneId}', 'CURATOR_REVISION_IDENTITY')
require('src/main/storage/workstation-db.ts', "VALUES ('vca_curator_lane', 'lane-4')", 'CURATOR_SETTINGS_PERSISTED')
require('src/main/storage/workstation-db.ts', "COALESCE(w.curator, 'UNWEIGHTED') IN ('DETERMINISTIC_SEED', 'UNWEIGHTED')", 'PENDING_MEMORY_QUERY')
require('src/main/storage/workstation-db.ts', 'insertVcaWeightRevision(eventId', 'APPEND_ONLY_WEIGHT_PATH_PRESERVED')
require('src/main/ipc/register-workstation-ipc.ts', "'workstation:vca-curator-run'", 'CURATOR_RUN_IPC')
require('src/preload/index.ts', 'runVcaCurator:', 'CURATOR_PRELOAD_API')
require('src/renderer/src/components/Explorer/Explorer.ts', 'VCA MEMORY CURATOR', 'CURATOR_UI_PANEL')
require('src/renderer/src/components/Explorer/Explorer.ts', 'AUTO CURATE NEW VCA MEMORY', 'AUTO_CURATE_UI')
require('src/renderer/src/components/Explorer/Explorer.ts', 'RUN PENDING', 'RUN_PENDING_UI')
require('src/renderer/src/components/Explorer/Explorer.ts', 'RE-EVALUATE', 'REEVALUATE_UI')
require('src/renderer/src/components/Explorer/Explorer.ts', 'Recommended starting point: a local ~12B Assistant.', 'TWELVEB_RECOMMENDATION_NOT_HARDCODED')
require('src/main/index.ts', 'new VcaCuratorService(', 'CURATOR_SERVICE_BOOTSTRAP')
require('src/main/index.ts', 'vcaCuratorService.start()', 'CURATOR_AUTORUN_BOOTSTRAP')
require('src/renderer/src/components/Explorer/Explorer.ts', 'private projectTree(): string', 'PROJECT_TREE_RESERVED')

print('VERTEX SESSION PORTAL / VCA CURATOR ASSISTANT VERIFY 000035')
print(f'ROOT={ROOT}')
for label in checks:
    print(f'{label}=PASS')

print('RUN=npm.cmd run build')
result = subprocess.run(
    ['npm.cmd', 'run', 'build'],
    cwd=ROOT,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
if result.returncode != 0:
    def safe(data: bytes) -> str:
        text = data.decode('utf-8', errors='replace')
        encoding = sys.stdout.encoding or 'utf-8'
        return text.encode(encoding, errors='backslashreplace').decode(encoding, errors='replace')
    print(safe(result.stdout))
    print(safe(result.stderr), file=sys.stderr)
    raise SystemExit(result.returncode)

print('BUILD=PASS')
print('VERTEX_SESSION_PORTAL_VCA_CURATOR_ASSISTANT_000035=PASS')
