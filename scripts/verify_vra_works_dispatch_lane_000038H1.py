from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TS = ROOT / 'src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts'


def main() -> None:
    print('VERTEX SESSION PORTAL / VRA WORKS DISPATCH LANE REPAIR VERIFY 000038H1')
    print(f'ROOT={ROOT}')
    failures: list[str] = []

    if not TS.exists():
        print('VRA_DISPATCH_LANE_FILE=FAIL')
        failures.append('VRA_DISPATCH_LANE_FILE')
    else:
        text = TS.read_text(encoding='utf-8')
        checks = {
            'NATIVE_REMOVE_COLLISION_RETIRED': 'private async remove(cardId:' not in text,
            'REMOVE_CARD_METHOD_PRESENT': 'private async removeCard(cardId: string): Promise<void>' in text,
            'REMOVE_ACTION_CALL_UPDATED': 'void this.removeCard(cardId)' in text,
            'SEND_TO_WORKS_PRESERVED': 'SEND TO WORKS' in text,
            'WORKS_RECEIVING_BAY_PRESERVED': 'WORKS RECEIVING BAY' in text,
            'HUMAN_APPLY_BOUNDARY_PRESERVED': 'HUMAN_APPLY REMAINS IN WORKS' in text,
            'VRA_DRAG_MIME_PRESERVED': 'application/x-vertex-vra-card' in text,
        }
        for label, ok in checks.items():
            print(f'{label}={"PASS" if ok else "FAIL"}')
            if not ok:
                failures.append(label)

    verifier = ROOT / 'scripts/verify_vra_works_dispatch_lane_000038.py'
    if verifier.exists():
        print('BASE_000038_VERIFIER_PRESENT=PASS')
    else:
        print('BASE_000038_VERIFIER_PRESENT=FAIL')
        failures.append('BASE_000038_VERIFIER_PRESENT')

    if failures:
        raise SystemExit('STATIC_VERIFY_FAIL:' + ','.join(failures))

    command = ['npm.cmd', 'run', 'build'] if sys.platform.startswith('win') else ['npm', 'run', 'build']
    print('RUN=' + ' '.join(command))
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='backslashreplace',
    )
    if result.returncode != 0:
        print('BUILD=FAIL')
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise SystemExit(result.returncode)

    print('BUILD=PASS')
    print('VERTEX_SESSION_PORTAL_VRA_WORKS_DISPATCH_LANE_000038H1=PASS')


if __name__ == '__main__':
    main()
