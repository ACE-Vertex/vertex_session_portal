from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')

def require(label: str, condition: bool) -> None:
    if not condition:
        raise SystemExit(f'{label}=FAIL')
    print(f'{label}=PASS')

print('VERTEX SESSION PORTAL / VERA-FIRST LANE + ASSISTANT FOUNDATION VERIFY 000032')
print(f'ROOT={ROOT}')
contracts = read('src/shared/contracts.ts')
explorer = read('src/renderer/src/components/Explorer/Explorer.ts')
css = read('src/renderer/src/components/Explorer/Explorer.css')
main = read('src/renderer/src/components/MainFrame/MainFrame.ts')

require('VERA_PRIMARY_IDENTITY_CONTRACT', "primaryIdentity: 'VERA'" in contracts)
require('FIVE_VERA_LANES_CONTRACT', 'laneCount: 5' in contracts)
require('EMPTY_ASSISTANT_IS_NONE', "emptyAssistantBehavior: 'NO_ASSISTANT'" in contracts)
require('EXTERNAL_MODEL_ASSISTANT_ONLY', "externalModelRole: 'AI_ASSISTANT_ONLY'" in contracts)
require('CHATGPT_BROWSER_TARGET', "primaryTransportTarget: 'CHATGPT_BROWSER_SESSION'" in contracts)
require('AI_TAB_REFRAMED_TO_VERA', "title: 'VERA SESSION MATRIX'" in explorer)
require('NO_ASSISTANT_UI', '>No Assistant</option>' in explorer)
require('DEDICATED_ASSISTANT_UI', 'DEDICATED AI ASSISTANT' in explorer)
require('ADD_VERA_CONTROL', '⊕ ADD VERA' in explorer)
require('ACTIVE_VERA_SESSIONS_LABEL', 'ACTIVE VERA SESSIONS' in explorer)
require('ASSISTANT_REMOVE_CONTROL', 'REMOVE AI ASSISTANT' in explorer)
require('ASSISTANT_ONLY_ROUTE_LABEL', 'ASSISTANT ONLY' in explorer)
require('VERA_DEFAULT_UI_REMOVED', 'VERA DEFAULT' not in explorer)
require('OLD_LLM_LANE_COPY_REMOVED', 'Five independent LLM lanes' not in explorer)
require('ASSISTANT_STYLING', '.assistantHeader' in css and '.assistantEyebrow' in css)
require('FOOTER_VERA_MATRIX', 'VERA SESSION MATRIX' in main)
require('LEGACY_ENGINE_DISCLOSED', 'LEGACY CHAT ENGINE' in main)
require('PROJECT_TREE_RESERVED', 'private projectTree(): string' in explorer)

print('RUN=npm.cmd run build')
r = subprocess.run(['npm.cmd','run','build'], cwd=ROOT, capture_output=True, text=False)
stdout = (r.stdout or b'').decode('utf-8', errors='replace')
stderr = (r.stderr or b'').decode('utf-8', errors='replace')
# Encode safely for cp932 Works consoles without failing the verifier.
def emit(text: str) -> None:
    enc = sys.stdout.encoding or 'utf-8'
    safe = text.encode(enc, errors='replace').decode(enc, errors='replace')
    print(safe)
emit(stdout)
if stderr.strip(): emit(stderr)
require('BUILD', r.returncode == 0)
print('VERTEX_SESSION_PORTAL_VERA_FIRST_LANE_ASSISTANT_FOUNDATION_000032=PASS')
