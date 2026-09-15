from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')


def need(label: str, condition: bool) -> None:
    if not condition:
        raise SystemExit('MISSING_CONTRACT:' + label)
    print(label + '=PASS')


def console_safe(text: str) -> str:
    encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
    try:
        return text.encode(encoding, errors='replace').decode(encoding, errors='replace')
    except LookupError:
        return text.encode('ascii', errors='replace').decode('ascii')

contracts = read('src/shared/contracts.ts')
db = read('src/main/storage/workstation-db.ts')
ipc = read('src/main/ipc/register-workstation-ipc.ts')
preload = read('src/preload/index.ts')
curator = read('src/main/memory/vca-curator-service.ts')
explorer = read('src/renderer/src/components/Explorer/Explorer.ts')
browser = read('src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts')

print('VERTEX SESSION PORTAL / VCA MEMORY INBOX + SESSION CLOCK BRIDGE VERIFY 000036')
print('ROOT=' + str(ROOT))

need('VCA_INBOX_CONTRACT', "purpose: 'SESSION_TO_VERTEX_MEMORY_BOUNDARY'" in contracts)
need('HUMAN_VERA_MUTUAL_UNKNOWN_ACTORS', "'HUMAN' | 'VERA' | 'MUTUAL' | 'UNKNOWN'" in contracts)
need('SHA256_FINGERPRINT_DEDUP_CONTRACT', "duplicatePolicy: 'SHA256_FINGERPRINT_DEDUP'" in contracts and "createHash('sha256')" in db)
need('VERA_SESSION_THREAD_TABLE', 'CREATE TABLE IF NOT EXISTS vera_session_thread' in db)
need('VCA_MEMORY_INBOX_TABLE', 'CREATE TABLE IF NOT EXISTS vca_memory_inbox' in db)
need('VCA_MEMORY_RELATION_FOUNDATION', 'CREATE TABLE IF NOT EXISTS vca_memory_relation' in db)
need('PENDING_TO_VCA_PROMOTION', "status TEXT NOT NULL DEFAULT 'PENDING'" in db and 'promoteVcaInboxItem' in db)
need('CURATED_AFTER_AI_WEIGHT', 'markVcaInboxCuratedByEvent' in db and 'this.db.markVcaInboxCuratedByEvent(item.eventId)' in curator)
need('THREAD_BINDING_API', 'getVeraSessionThreadBindings' in contracts and 'updateVeraSessionThread' in contracts)
need('THREAD_BINDING_IPC', "'workstation:vera-thread-bindings'" in ipc and "'workstation:vera-thread-update'" in ipc)
need('THREAD_BINDING_PRELOAD', 'getVeraSessionThreadBindings:' in preload and 'updateVeraSessionThread:' in preload)
need('BROWSER_REPORTS_THREAD_METADATA', 'private reportThread' in browser and 'updateVeraSessionThread' in browser)
need('CHATGPT_HTTPS_THREAD_GUARD', "parsed.protocol !== 'https:' || parsed.hostname !== 'chatgpt.com'" in db)
need('INBOX_IPC', "'workstation:vca-inbox'" in ipc and "'workstation:vca-inbox-enqueue'" in ipc)
need('INBOX_PRELOAD_API', 'getVcaInbox:' in preload and 'enqueueVcaInbox:' in preload)
need('INBOX_UI_PANEL', 'VCA MEMORY INBOX' in explorer and 'SESSION → VERTEX MEMORY BOUNDARY' in explorer)
need('MANUAL_CAPTURE_BOUNDARY', "captureKind: 'MANUAL_BOUNDARY'" in explorer and 'CAPTURE TO VCA' in explorer)
need('MUTUAL_WEIGHT_SEED', "actor === 'MUTUAL'" in db)
need('CURATOR_AUTO_RELAY', "curator.schedule('VCA_INBOX_ENQUEUE')" in ipc)
need('NO_BROWSER_DOM_SCRAPE', 'executeJavaScript' not in browser and 'browserContentExtraction: \'NO_DOM_SCRAPE\'' in contracts)
need('MEMORY_CLOCK_BRIDGE_PRESERVED', 'getVcaMemoryClockState' in db and 'canonicalRevision' in contracts)
need('PROJECT_TREE_RESERVED', '<div class="tree">' in explorer and '<strong>vertex_session_portal</strong>' in explorer)

npm = 'npm.cmd' if sys.platform.startswith('win') else 'npm'
print('RUN=' + npm + ' run build')
r = subprocess.run(
    [npm, 'run', 'build'],
    cwd=ROOT,
    text=True,
    capture_output=True,
    encoding='utf-8',
    errors='replace',
)
if r.stdout:
    print(console_safe(r.stdout))
if r.stderr:
    print(console_safe(r.stderr), file=sys.stderr)
if r.returncode != 0:
    raise SystemExit(r.returncode)
print('BUILD=PASS')
print('VERTEX_SESSION_PORTAL_VCA_MEMORY_INBOX_SESSION_CLOCK_BRIDGE_000036=PASS')
