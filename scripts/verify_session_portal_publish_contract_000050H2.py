from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / 'scripts/publish_latest_to_vertex_workstation_000047.py'
VERIFY_LATEST = ROOT / 'scripts/verify_workstation_latest_session_portal_000047.py'
H1_VERIFY = ROOT / 'scripts/verify_session_portal_dispatch_bay_staging_export_000050H1.py'
SERVICE = ROOT / 'src/main/vra/vra-dispatch-service.ts'
POLICY = ROOT / 'src/main/vra/vra-download-destination-policy.ts'
MAINFRAME = ROOT / 'src/renderer/src/components/MainFrame/MainFrame.ts'


def safe_emit(value='', stream=None):
    stream = stream or sys.stdout
    enc = getattr(stream, 'encoding', None) or 'utf-8'
    text = str(value)
    safe = text.encode(enc, errors='backslashreplace').decode(enc, errors='replace')
    stream.write(safe)
    if safe and not safe.endswith('\n'):
        stream.write('\n')
    stream.flush()


def read(path):
    return path.read_text(encoding='utf-8-sig') if path.exists() else ''


def check(name, ok, failures):
    safe_emit(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)


def run(cmd):
    safe_emit('RUN=' + ' '.join(str(x) for x in cmd))
    result = subprocess.run(
        [str(x) for x in cmd],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        shell=False,
    )
    safe_emit(result.stdout)
    if result.stderr:
        safe_emit(result.stderr, sys.stderr)
    safe_emit(f'EXIT_CODE={result.returncode}')
    return result.returncode


def code_only(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'(^|\s)//[^\n]*', r'\1', text)
    return text


def main():
    safe_emit('=== VERTEX SESSION PORTAL / DISPATCH PUBLISH CONTRACT VERIFY 000050H2 ===')
    failures = []
    publisher = read(PUBLISH)
    latest_verifier = read(VERIFY_LATEST)
    service = code_only(read(SERVICE))
    policy = code_only(read(POLICY))
    mainframe = read(MAINFRAME)

    check('PUBLISHER_OLD_MARKER_RETIRED', 'DISPATCH_WILL_DOWNLOAD_POLICY' not in publisher, failures)
    check('PUBLISHER_PASSIVE_POLICY_MARKER', 'DISPATCH_POLICY_PASSIVE' in publisher and 'capture owner = VraDispatchService' in publisher, failures)
    check('PUBLISHER_STAGING_CAPTURE_MARKER', 'DISPATCH_STAGING_CAPTURE' in publisher and 'item.setSavePath(stagedPath)' in publisher, failures)
    check('PUBLISHER_HUMAN_EXPORT_MARKER', 'DISPATCH_HUMAN_EXPORT' in publisher and 'exportCard(cardId: string): string' in publisher, failures)
    check('PUBLISHER_MANIFEST_STAGING', '"dispatch_staging_first_verified": True' in publisher, failures)
    check('PUBLISHER_MANIFEST_EXPORT', '"dispatch_human_export_verified": True' in publisher, failures)
    check('PUBLISHER_MANIFEST_OWNER', '"vra_capture_owner": "VRA_DISPATCH_SERVICE_ONLY"' in publisher, failures)
    check('PUBLISHER_MANIFEST_FLOW', 'CHATGPT_TO_STAGING_TO_DISPATCH_BAY_TO_HUMAN_EXPORT_OR_WORKS' in publisher, failures)

    check('LATEST_VERIFY_NEW_MANIFEST_GATES', all(x in latest_verifier for x in [
        'MANIFEST_DISPATCH_STAGING_FIRST',
        'MANIFEST_DISPATCH_HUMAN_EXPORT',
        'MANIFEST_VRA_CAPTURE_OWNER',
        'MANIFEST_DISPATCH_FLOW',
    ]), failures)
    check('LATEST_VERIFY_SOURCE_STAGING', 'SOURCE_DISPATCH_STAGING_FIRST' in latest_verifier, failures)
    check('LATEST_VERIFY_SOURCE_EXPORT', 'SOURCE_DISPATCH_HUMAN_EXPORT' in latest_verifier, failures)
    check('LATEST_VERIFY_SOURCE_POLICY_PASSIVE', 'SOURCE_DISPATCH_POLICY_PASSIVE' in latest_verifier, failures)

    check('LIVE_CAPTURE_STAGING_FIRST', 'item.setSavePath(stagedPath)' in service, failures)
    check('LIVE_HUMAN_EXPORT', 'exportCard(cardId: string): string' in service, failures)
    check('LIVE_POLICY_NO_DIRECT_SAVE', 'item.setSavePath(target)' not in policy and 'will-download' not in policy, failures)
    check('PRIMARY_ENTRY_UI_REMAINS_RETIRED', 'PRIMARY ENTRY' not in mainframe and 'class="primaryEntry"' not in mainframe, failures)

    if failures:
        safe_emit('STATIC_FAILURES=' + ','.join(failures))
        raise SystemExit(2)

    # H1 verifier now becomes the end-to-end publication gate. It already checks
    # source build, staging/export ownership, canonical packaging and latest launcher.
    check('H1_FULL_VERIFY_PRESENT', H1_VERIFY.exists(), failures)
    if not failures:
        check('H1_FULL_VERIFY', run([sys.executable, str(H1_VERIFY.relative_to(ROOT))]) == 0, failures)

    if failures:
        safe_emit('FAILURES=' + ','.join(failures))
        raise SystemExit(3)

    safe_emit('PUBLISH_GATE_MIGRATION=OLD_DIRECT_DOWNLOAD_TO_STAGING_FIRST')
    safe_emit('VRA_FLOW=CHATGPT_DOWNLOAD_TO_PORTAL_STAGING_TO_DISPATCH_BAY_TO_HUMAN_EXPORT_OR_WORKS')
    safe_emit('MANUAL_ACCEPTANCE=DOWNLOAD_REAL_VRA_CONFIRM_DISPATCH_CARD_THEN_EXPORT_TO_SELECTED_FOLDER')
    safe_emit('VERTEX_SESSION_PORTAL_DISPATCH_PUBLISH_CONTRACT_000050H2=PASS')


if __name__ == '__main__':
    main()
