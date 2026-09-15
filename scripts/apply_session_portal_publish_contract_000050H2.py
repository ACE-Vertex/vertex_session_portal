from pathlib import Path
import re
import shutil
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / 'scripts/publish_latest_to_vertex_workstation_000047.py'
VERIFY_LATEST = ROOT / 'scripts/verify_workstation_latest_session_portal_000047.py'
EVIDENCE = ROOT / 'EVIDENCE' / 'DISPATCH_BAY_PUBLISH_CONTRACT_000050H2' / datetime.now().strftime('%Y%m%d-%H%M%S')
TOUCH = [PUBLISH, VERIFY_LATEST]


def safe_emit(value='', stream=None):
    stream = stream or sys.stdout
    enc = getattr(stream, 'encoding', None) or 'utf-8'
    text = str(value)
    safe = text.encode(enc, errors='backslashreplace').decode(enc, errors='replace')
    stream.write(safe)
    if safe and not safe.endswith('\n'):
        stream.write('\n')
    stream.flush()


def read(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(f'MISSING_REQUIRED_FILE:{path}')
    return path.read_text(encoding='utf-8-sig')


def write(path: Path, text: str) -> None:
    path.write_bytes(text.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8'))


def backup() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for path in TOUCH:
        if path.exists():
            shutil.copy2(path, EVIDENCE / path.name)


def restore() -> None:
    for path in TOUCH:
        old = EVIDENCE / path.name
        if old.exists():
            shutil.copy2(old, path)


def patch_publisher(text: str) -> str:
    # Retire the obsolete requirement that the compatibility policy itself owns
    # DownloadItem.setSavePath(target). New invariant: VraDispatchService owns
    # browser capture, stages first, then Human EXPORT or SEND TO WORKS.
    old_tuple = re.compile(
        r'''\(\s*\n\s*SRC\s*/\s*["']src/main/vra/vra-download-destination-policy\.ts["']\s*,\s*\n'''
        r'''\s*["']item\.setSavePath\(target\)["']\s*,\s*\n'''
        r'''\s*["']DISPATCH_WILL_DOWNLOAD_POLICY["']\s*,\s*\n\s*\),''',
        re.S,
    )
    replacement = '''(
        SRC / "src/main/vra/vra-download-destination-policy.ts",
        "capture owner = VraDispatchService",
        "DISPATCH_POLICY_PASSIVE",
    ),
    (
        SRC / "src/main/vra/vra-dispatch-service.ts",
        "item.setSavePath(stagedPath)",
        "DISPATCH_STAGING_CAPTURE",
    ),
    (
        SRC / "src/main/vra/vra-dispatch-service.ts",
        "exportCard(cardId: string): string",
        "DISPATCH_HUMAN_EXPORT",
    ),'''

    if 'DISPATCH_WILL_DOWNLOAD_POLICY' in text:
        text, n = old_tuple.subn(replacement, text, count=1)
        if n != 1:
            raise RuntimeError('PUBLISHER_OLD_DISPATCH_MARKER_BLOCK_NOT_PATCHED')

    # Ensure new markers are present exactly once even on an H2 retry.
    for marker in ('DISPATCH_POLICY_PASSIVE', 'DISPATCH_STAGING_CAPTURE', 'DISPATCH_HUMAN_EXPORT'):
        if text.count(marker) != 1:
            raise RuntimeError(f'PUBLISHER_NEW_MARKER_COUNT_INVALID:{marker}:{text.count(marker)}')
    if 'DISPATCH_WILL_DOWNLOAD_POLICY' in text:
        raise RuntimeError('PUBLISHER_OBSOLETE_DISPATCH_MARKER_STILL_PRESENT')

    # Extend latest-build metadata with the new invariant while retaining the
    # old compatibility boolean for consumers that already read it.
    if '"dispatch_staging_first_verified": True' not in text:
        anchor = '        "dispatch_destination_setting_verified": True,\n'
        if anchor not in text:
            raise RuntimeError('PUBLISHER_METADATA_ANCHOR_MISSING')
        extra = (
            anchor
            + '        "dispatch_staging_first_verified": True,\n'
            + '        "dispatch_human_export_verified": True,\n'
            + '        "vra_capture_owner": "VRA_DISPATCH_SERVICE_ONLY",\n'
            + '        "dispatch_flow": "CHATGPT_TO_STAGING_TO_DISPATCH_BAY_TO_HUMAN_EXPORT_OR_WORKS",\n'
        )
        text = text.replace(anchor, extra, 1)

    return text


def patch_latest_verifier(text: str) -> str:
    # Add manifest assertions for the new flow. Keep existing checks intact.
    if 'MANIFEST_DISPATCH_STAGING_FIRST' not in text:
        anchor = '        check("MANIFEST_DISPATCH_SETTING", manifest.get("dispatch_destination_setting_verified") is True, failures)\n'
        if anchor not in text:
            raise RuntimeError('LATEST_VERIFIER_MANIFEST_ANCHOR_MISSING')
        extra = (
            anchor
            + '        check("MANIFEST_DISPATCH_STAGING_FIRST", manifest.get("dispatch_staging_first_verified") is True, failures)\n'
            + '        check("MANIFEST_DISPATCH_HUMAN_EXPORT", manifest.get("dispatch_human_export_verified") is True, failures)\n'
            + '        check("MANIFEST_VRA_CAPTURE_OWNER", manifest.get("vra_capture_owner") == "VRA_DISPATCH_SERVICE_ONLY", failures)\n'
            + '        check("MANIFEST_DISPATCH_FLOW", manifest.get("dispatch_flow") == "CHATGPT_TO_STAGING_TO_DISPATCH_BAY_TO_HUMAN_EXPORT_OR_WORKS", failures)\n'
        )
        text = text.replace(anchor, extra, 1)

    # Verify the live source still expresses staging-first semantics.
    if 'SOURCE_DISPATCH_STAGING_FIRST' not in text:
        anchor = '    dispatch = SRC / "src/renderer/src/components/VraDispatchLane/VraDispatchDestinationControl.ts"\n'
        if anchor not in text:
            raise RuntimeError('LATEST_VERIFIER_SOURCE_ANCHOR_MISSING')
        extra = (
            anchor
            + '    dispatch_service = SRC / "src/main/vra/vra-dispatch-service.ts"\n'
            + '    dispatch_policy = SRC / "src/main/vra/vra-download-destination-policy.ts"\n'
        )
        text = text.replace(anchor, extra, 1)

        insert_anchor = '''    check(
        "SOURCE_DISPATCH_SETTING_AFTER_RELOAD",
        dispatch.exists() and "reload.insertAdjacentElement('afterend', button)" in dispatch.read_text(encoding="utf-8"),
        failures,
    )
'''
        if insert_anchor not in text:
            raise RuntimeError('LATEST_VERIFIER_INSERT_ANCHOR_MISSING')
        checks = insert_anchor + '''    service_text = dispatch_service.read_text(encoding="utf-8") if dispatch_service.exists() else ""
    policy_text = dispatch_policy.read_text(encoding="utf-8") if dispatch_policy.exists() else ""
    check(
        "SOURCE_DISPATCH_STAGING_FIRST",
        "item.setSavePath(stagedPath)" in service_text,
        failures,
    )
    check(
        "SOURCE_DISPATCH_HUMAN_EXPORT",
        "exportCard(cardId: string): string" in service_text,
        failures,
    )
    check(
        "SOURCE_DISPATCH_POLICY_PASSIVE",
        "capture owner = VraDispatchService" in policy_text and "item.setSavePath(target)" not in policy_text,
        failures,
    )
'''
        text = text.replace(insert_anchor, checks, 1)

    return text


def main() -> None:
    safe_emit('=== VERTEX SESSION PORTAL / DISPATCH PUBLISH CONTRACT APPLY 000050H2 ===')
    safe_emit(f'ROOT={ROOT}')
    safe_emit(f'TRANSACTION_BACKUP={EVIDENCE}')
    backup()
    try:
        write(PUBLISH, patch_publisher(read(PUBLISH)))
        write(VERIFY_LATEST, patch_latest_verifier(read(VERIFY_LATEST)))
    except Exception:
        restore()
        safe_emit('TRANSACTION_ROLLBACK=PASS')
        raise

    safe_emit('TRANSACTION_ROLLBACK=NOT_REQUIRED')
    safe_emit('OBSOLETE_DISPATCH_WILL_DOWNLOAD_POLICY=RETIRED')
    safe_emit('PUBLISH_GATE=STAGING_FIRST_PLUS_HUMAN_EXPORT')
    safe_emit('CANONICAL_LAUNCHER=UNCHANGED')
    safe_emit('VERTEX_SESSION_PORTAL_DISPATCH_PUBLISH_CONTRACT_000050H2_APPLY=PASS')


if __name__ == '__main__':
    main()
