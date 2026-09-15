from __future__ import annotations
from pathlib import Path
import os, re, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]

def require(path: str, text: str) -> None:
    body = (ROOT / path).read_text(encoding='utf-8')
    if text not in body:
        raise SystemExit(f'MISSING_CONTRACT:{path}:{text}')

print('VERTEX SESSION PORTAL / INTELLIGENCE SQLITE VCR VCA VERIFY 000025')
print(f'ROOT={ROOT}')

require('src/renderer/src/components/VeraSession/VeraSession.css', 'min-height: 270px;')
require('src/renderer/src/components/VeraSession/VeraSession.css', 'max-height: 900px !important;')
require('src/renderer/src/components/VeraSession/VeraSession.ts', 'const minimum = 238')
require('src/renderer/src/components/SearchVera/SearchVera.css', 'max-height: 115px !important;')
require('src/renderer/src/components/Explorer/Explorer.ts', "['PROJECT', 'VCR', 'VCA', 'AI']")
require('src/renderer/src/components/MainFrame/MainFrame.ts', 'providerStatus.providerLabel')
require('src/main/storage/workstation-db.ts', 'CREATE TABLE IF NOT EXISTS vcr_revision')
require('src/main/storage/workstation-db.ts', 'MAX(revision) AS current_revision')
require('src/main/storage/workstation-db.ts', 'searchVca(query =')
require('src/main/storage/workstation-db.ts', "'vera-01'")
require('src/main/storage/workstation-db.ts', "'vera-02'")
require('src/main/storage/workstation-db.ts', "'vera-03'")
require('src/main/storage/workstation-db.ts', "'vera-search'")
require('src/main/providers/provider-settings-store.ts', 'safeStorage.encryptString')
require('src/shared/contracts.ts', "| 'openai-compatible'")
require('src/main/providers/provider-settings-store.ts', "'openai-compatible': 'OpenAI Compatible'")
require('src/renderer/src/components/Explorer/Explorer.ts', "value: 'openai-compatible'")
require('src/main/providers/configured-provider.ts', 'openAiCompatibleStatus(cfg.provider, cfg.endpoint, cfg.model)')
require('src/renderer/src/components/SearchVera/SearchVera.ts', 'VCR · SQLITE')
require('src/renderer/src/components/SearchVera/SearchVera.ts', 'VCA · SQLITE')
search_vera = (ROOT / 'src/renderer/src/components/SearchVera/SearchVera.ts').read_text(encoding='utf-8')
if 'VCR · EXTERNAL' in search_vera or 'VCA · EXTERNAL' in search_vera:
    raise SystemExit('SEARCH_VERA_ARCHIVE_SURFACE=FAIL')

# Ensure the three main Session Portal panes remain code-driven and no replacement topology was introduced.
main = (ROOT / 'src/renderer/src/components/MainFrame/MainFrame.ts').read_text(encoding='utf-8')
if 'active.map(session => this.renderSession(session)).join' not in main:
    raise SystemExit('LAYOUT_TOPOLOGY_CONTRACT=FAIL')
print('LAYOUT_TOPOLOGY_CONTRACT=PASS')
print('COMPOSER_270_900_CONTRACT=PASS')
print('SQLITE_VCR_VCA_CONTRACT=PASS')
print('PROVIDER_SETTINGS_CONTRACT=PASS')
print('OPENAI_COMPATIBLE_CONTRACT_LOCATION=PASS')

npm = 'npm.cmd' if os.name == 'nt' else 'npm'
proc = subprocess.run([npm, 'run', 'build'], cwd=ROOT, text=True)
if proc.returncode != 0:
    raise SystemExit(proc.returncode)

print('BUILD=PASS')
print('VERTEX_SESSION_PORTAL_INTELLIGENCE_SQLITE_VCR_VCA_000025=PASS')
print('VERTEX_SESSION_PORTAL_INTELLIGENCE_SQLITE_VCR_VCA_000025H1=PASS')
