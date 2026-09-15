from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def require(label: str, condition: bool) -> None:
    if not condition:
        raise RuntimeError(f'{label}=FAIL')
    print(f'{label}=PASS')


def build() -> None:
    npm = 'npm.cmd' if os.name == 'nt' else 'npm'
    print(f'RUN={npm} run build')
    result = subprocess.run(
        [npm, 'run', 'build'],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    if result.returncode != 0:
        output = result.stdout.decode('utf-8', errors='replace')
        safe = output.encode('ascii', errors='replace').decode('ascii')
        print(safe[-12000:])
        raise RuntimeError(f'BUILD_FAILED:{result.returncode}')
    print('BUILD=PASS')


def main() -> None:
    print('VERTEX SESSION PORTAL / AI LANES + EXPLORER 365 VERIFY 000028')
    print(f'ROOT={ROOT}')

    contracts = text('src/shared/contracts.ts')
    store = text('src/main/providers/provider-settings-store.ts')
    provider = text('src/main/providers/configured-provider.ts')
    service = text('src/main/agents/session-agent-service.ts')
    ipc = text('src/main/ipc/register-session-agent-ipc.ts')
    preload = text('src/preload/index.ts')
    explorer = text('src/renderer/src/components/Explorer/Explorer.ts')
    css = text('src/renderer/src/components/Explorer/Explorer.css')
    tokens = text('src/renderer/src/shared/tokens.css')

    require('EXPLORER_WIDTH_365', '--vertex-explorer-width: 365px;' in tokens)
    require('EXPLORER_NO_HORIZONTAL_SCROLL', 'overflow-x:hidden' in css and 'max-width:100%' in css)
    require('AI_LANE_1_TO_5_CONTRACT', all(f"'lane-{i}'" in contracts for i in range(1, 6)))
    require('LANE_SESSION_MAPPING', all(value in store for value in ['vera-01', 'vera-02', 'vera-03', 'vera-search']))
    require('LANE5_RESERVE', "laneId: 'lane-5'" in store and 'sessionId: null' in store)
    require('EMPTY_LANE_VERA_FALLBACK', "source: 'VERA_DEFAULT'" in store and 'provider: null' in explorer)
    require('PER_LANE_SQLITE_SETTINGS', 'provider_lane_settings' in store and 'provider_lane_secret' in store)
    require('PER_LANE_SAFE_STORAGE', 'saveLaneSecret' in store and 'safeStorage.encryptString' in store)
    require('LOCAL_PROVIDER_CONTRACT', "| 'local'" in contracts and "local: 'Local Raw LLM'" in store)
    require('LOCAL_RAW_LLM_PICKER', 'session-agent:browse-local-llm' in ipc and 'showOpenDialog' in ipc and 'browseLocalLlm' in preload)
    require('LOCAL_FIELD_CONDITIONAL', 'LOCAL LLM SOURCE' in explorer and 'data-local-field' in explorer)
    require('MODEL_DROPDOWN_COMBO', 'datalist id="availableModels"' in explorer and 'listAiLaneModels' in explorer)
    require('MODEL_DISCOVERY_ENDPOINTS', '/api/tags' in provider and "'models'" in provider)
    require('API_KEY_FITS_EXPLORER', '.fieldInput' in css and 'width:100%' in css and 'min-width:0' in css)
    require('SESSION_ROUTE_TO_LANE', 'sessionLaneId(session.id)' in service and 'providerMessages,' in service and 'laneId' in service)
    require('VCR_NOT_MODIFIED_BY_UI_PATCH', 'resultCard' in explorer)

    build()
    print('VERTEX_SESSION_PORTAL_AI_LANES_EXPLORER_365_000028=PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'VERTEX_SESSION_PORTAL_AI_LANES_EXPLORER_365_000028=FAIL:{exc}')
        sys.exit(1)
