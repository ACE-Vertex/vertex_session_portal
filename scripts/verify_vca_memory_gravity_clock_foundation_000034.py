from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')

def require(name: str, condition: bool) -> None:
    if not condition:
        raise SystemExit(f'{name}=FAIL')
    print(f'{name}=PASS')

print('VERTEX SESSION PORTAL / VCA MEMORY GRAVITY + CLOCK VERIFY 000034')
print(f'ROOT={ROOT}')

contracts = read('src/shared/contracts.ts')
db = read('src/main/storage/workstation-db.ts')
ipc = read('src/main/ipc/register-workstation-ipc.ts')
preload = read('src/preload/index.ts')
explorer = read('src/renderer/src/components/Explorer/Explorer.ts')
css = read('src/renderer/src/components/Explorer/Explorer.css')

require('VERTEX_OWNED_VCA_CONTRACT', 'VCA_MEMORY_CONTRACT' in contracts and "humanVeraPriority: 'PEER'" in contracts)
require('NO_AUTOMATIC_TIME_DECAY', "automaticTimeDecay: 'NO'" in contracts)
require('VCA_EVENT_APPEND_ONLY_TABLE', 'CREATE TABLE IF NOT EXISTS vca_memory_event' in db and 'memory_revision INTEGER PRIMARY KEY AUTOINCREMENT' in db)
require('VCA_WEIGHT_APPEND_ONLY_TABLE', 'CREATE TABLE IF NOT EXISTS vca_weight_revision' in db and 'PRIMARY KEY (event_id, revision)' in db)
require('VERA_MEMORY_CLOCK_TABLE', 'CREATE TABLE IF NOT EXISTS vera_memory_clock' in db)
require('LEGACY_CHAT_MIGRATION', 'FROM session_chat_message' in db and "'PORTAL_CHAT'" in db)
require('HUMAN_VERA_EQUAL_GRAVITY_COEFFICIENT', 'dimensions.humanSignal * 0.16' in db and 'dimensions.veraSignal * 0.16' in db)
require('PURPOSE_AND_IMPLEMENTATION_WEIGHT', 'dimensions.purposeRelation * 0.18' in db and 'dimensions.implementationLink * 0.16' in db)
require('WEIGHTED_VCA_RETRIEVAL', 'memory_gravity' in db and 'ORDER BY\n      COALESCE(w.memory_gravity, 0) DESC' in db)
require('VCA_CURATOR_REVISION_API', 'appendVcaWeightRevision' in contracts and 'appendVcaWeightRevision' in db and 'workstation:vca-weight-append' in ipc and 'workstation:vca-weight-append' in preload)
require('VCA_MEMORY_INGEST_API', 'appendVcaMemoryEvent' in contracts and 'workstation:vca-memory-append' in ipc and 'workstation:vca-memory-append' in preload)
require('CANONICAL_MEMORY_FRONTIER', 'getVcaMemoryClockState' in db and 'canonicalRevision' in contracts)
require('COMPENSATION_PACKET', 'getVcaCompensation' in db and 'VcaCompensationPacket' in contracts)
require('COMPENSATION_ACK', 'acknowledgeVcaCompensation' in db and 'workstation:vca-compensation-ack' in ipc)
require('VCA_CLOCK_UI', 'MEMORY CLOCK' in explorer and 'CANONICAL r${clock.canonicalRevision}' in explorer and 'memoryClockRail' in css)
require('VCA_GRAVITY_UI', 'gravityBadge' in explorer and 'vcaWeightLine' in explorer and 'memoryGravity' in explorer)
require('PROJECT_TREE_RESERVED', 'vertex_session_portal' in explorer and 'projectTree()' in explorer)
require('NO_BROWSER_DOM_SCRAPE_ADDED', 'querySelectorAll' not in db and 'CHATGPT_BROWSER' in contracts)

print('RUN=npm.cmd run build')
result = subprocess.run(
    ['npm.cmd', 'run', 'build'],
    cwd=ROOT,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
if result.returncode != 0:
    text = result.stdout.decode('utf-8', errors='replace')
    safe = text.encode('ascii', errors='backslashreplace').decode('ascii')
    print(safe[-16000:])
    raise SystemExit(result.returncode)

print('BUILD=PASS')
print('VERTEX_SESSION_PORTAL_VCA_MEMORY_GRAVITY_CLOCK_FOUNDATION_000034=PASS')
