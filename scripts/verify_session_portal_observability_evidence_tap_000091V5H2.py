from __future__ import annotations
from pathlib import Path
import subprocess
import traceback

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
NPM = Path(r"C:\Program Files\nodejs\npm.cmd")

def safe(value: object) -> str:
    return str(value).encode('ascii', errors='backslashreplace').decode('ascii')

def emit(value: object) -> None:
    print(safe(value), flush=True)

def check(name: str, ok: bool) -> bool:
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8', errors='replace')

def run_npm(*args: str) -> int:
    command = [str(NPM), *args]
    emit('RUN=' + ' '.join(command))
    try:
        p = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, errors='replace', timeout=180, shell=False)
    except subprocess.TimeoutExpired:
        emit('NPM_TIMEOUT=180')
        return 124
    except Exception as exc:
        emit(f'NPM_EXCEPTION={type(exc).__name__}:{exc}')
        emit(traceback.format_exc())
        return 125
    emit(f'EXIT={p.returncode}')
    if p.stdout: emit('STDOUT_TAIL=' + p.stdout[-16000:].replace('\r',''))
    if p.stderr: emit('STDERR_TAIL=' + p.stderr[-16000:].replace('\r',''))
    return p.returncode

def main() -> int:
    emit('=== SESSION PORTAL / OBSERVABILITY EVIDENCE RETURN TAP 000091V5H2 ===')
    emit('HUMAN_UI_CHANGE=NONE')
    emit('WORKSTATION_PRODUCTION_MUTATION=NONE')
    emit('EXACT_ORIGIN_ROUTING_AUTHORITY=UNCHANGED')
    emit('ACK_STATE_MACHINE_AUTHORITY=UNCHANGED')
    emit('OBSERVABILITY_TAP=NON_AUTHORITATIVE')
    emit('RAY_MODE=READ_ONLY')

    required = [
        'src/main/observability/contracts.ts',
        'src/main/observability/ray-core.ts',
        'src/main/observability/sensor-core.ts',
        'src/main/observability/judge-core.ts',
        'src/main/observability/black-box.ts',
        'src/main/observability/evidence-intelligence.ts',
        'src/main/observability/observability-coordinator.ts',
        'src/main/observability/redaction.ts',
        'src/main/observability/evidence-return-tap.ts',
        'src/main/vra/vra-dispatch-service.ts',
    ]
    ok = True
    for rel in required:
        ok &= check('FILE_' + rel.replace('/','_').replace('.','_').upper(), (ROOT / rel).is_file())
    if not ok: return 20

    service = read('src/main/vra/vra-dispatch-service.ts')
    tap = read('src/main/observability/evidence-return-tap.ts')
    coordinator = read('src/main/observability/observability-coordinator.ts')
    redaction = read('src/main/observability/redaction.ts')
    ray = read('src/main/observability/ray-core.ts')

    checks = {
      'SERVICE_TAP_IMPORT': "EvidenceReturnObservabilityTap" in service,
      'SERVICE_TAP_CONSTRUCTED_ONCE': service.count('new EvidenceReturnObservabilityTap(') == 1,
      'SERVICE_TAP_AFTER_IDENTITY_GATE': service.find('observeAndPersist({') > service.find('WORKSTATION_EVIDENCE_HUMAN_GATE_MISMATCH'),
      'SERVICE_TAP_BEFORE_CACHE_WRITE': service.find('observeAndPersist({') < service.find("const cacheName = `${createHash('sha256').update(card.jobId)"),
      'EXACT_ORIGIN_ASSERT_PRESERVED': 'this.assertOriginRoute(card, origin)' in service,
      'ACK_RETURN_QUEUED_GATE_PRESERVED': "['RETURN_QUEUED', 'RETURNED'].includes" in service,
      'ACK_WORKSTATION_CALL_PRESERVED': 'this.workstation.acknowledgeEvidence(card.jobId' in service,
      'RAY_OPTIC_BRIDGE_PRESERVED': '000082V5 — Ray Evidence optic-nerve bridge.' in service,
      'TAP_DEGRADED_NON_THROWING': "status: 'DEGRADED'" in tap and 'persistence error must never block exact-origin Evidence return' in tap,
      'TAP_IDEMPOTENT_BY_EVIDENCE': 'readExisting(input)' in tap and "update(evidenceId).digest('hex')" in tap,
      'TAP_HIDDEN_DURABLE_CACHE': "join(stagingRoot, 'observability', 'evidence')" in tap,
      'TAP_WORKSTATION_LANES_READ_SCOPE': "'vertex_workstation', 'runtime', 'lanes'" in tap,
      'COORDINATOR_REDACTS_BEFORE_BLACKBOX': 'const safeText = redactSensitiveText(read.text)' in coordinator,
      'REDACTION_OPENAI': 'REDACTED_OPENAI_KEY' in redaction,
      'REDACTION_GITHUB': 'REDACTED_GITHUB_TOKEN' in redaction,
      'NO_RENDERER_OBSERVABILITY_UI': not (ROOT / 'src/renderer/src/components/Observability').exists(),
      'RAY_NO_WRITE_API': all(x not in ray for x in ['writeFile(', 'appendFile(', 'rename(', 'unlink(', 'child_process']),
      'NO_DOM_SCRAPE': 'executeJavaScript' not in tap and 'webContents' not in tap,
    }
    for name, value in checks.items(): ok &= check(name, value)
    if not ok: return 21

    tc = run_npm('run', 'typecheck')
    if tc != 0: return 30 if tc < 124 else tc
    build = run_npm('run', 'build')
    if build != 0: return 31 if build < 124 else build

    emit('OBSERVABILITY_EVIDENCE_RETURN_TAP=PASS')
    emit('NEXT=H3_CONTROLLED_FAILURE_E2E_CANARY')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
