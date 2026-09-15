from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / 'src/renderer/src/components/VeraSession/VeraSession.css').read_text(encoding='utf-8')
ts = (ROOT / 'src/renderer/src/components/VeraSession/VeraSession.ts').read_text(encoding='utf-8')


def need(label, cond):
    if not cond:
        raise SystemExit('MISSING_CONTRACT:' + label)
    print(label + '=PASS')


def console_safe(text: str) -> str:
    """Render subprocess output using the active Windows console encoding without crashing.

    Node/Vite emits Unicode symbols (for example U+2713 CHECK MARK).  Vertex Works may
    run Python with a CP932 stdout.  Replace only characters that the active console
    cannot encode; verification semantics remain driven by the subprocess return code.
    """
    encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
    try:
        return text.encode(encoding, errors='replace').decode(encoding, errors='replace')
    except LookupError:
        return text.encode('ascii', errors='replace').decode('ascii')


print('VERTEX SESSION PORTAL / COMPOSER CLEARANCE + FOCUS VERIFY 000027')
print('ROOT=' + str(ROOT))
need('GRID_BODY_ROW_4', '.body {' in css and 'grid-row: 4;' in css)
need('GRID_COMPOSER_ROW_5', '.composer {' in css and 'grid-row: 5;' in css)
need('OPTIONAL_ROLE_ROW_3', '.roleBar {' in css and 'grid-row: 3;' in css)
need('COMPACT_CONTRACT_PRESERVED', 'min-height: 52px;' in css and 'min-height: 38px;' in css)
need('EXPANSION_CONTRACT_PRESERVED', '.composer[data-expanded="true"]' in css and 'min-height: 270px;' in css and 'max-height: 900px !important;' in css)
need('DRAFT_PRESERVATION', "private draft = ''" in ts and 'textarea.value = this.draft' in ts and 'this.draft = textarea.value' in ts)
need('SEND_RENDER_DEDUP', 'await this.loadHistory(false)' in ts and 'if (renderAfter) this.render()' in ts)
need('FOCUS_RESTORE', 'private focusComposer()' in ts and 'textarea.focus({ preventScroll: true })' in ts)
need('BUSY_DRAFT_SAFE', 'if (this.busy) {' in ts and 'this.focusComposer()' in ts)
need('TEXTAREA_NOT_DISABLED_DURING_THINKING', 'placeholder="Message Vera…"></textarea>' in ts)
need('SEND_BUTTON_BUSY_GUARD', "${this.busy ? 'disabled' : ''}>➤</button>" in ts)

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
print('VERTEX_SESSION_PORTAL_COMPOSER_CLEARANCE_FOCUS_000027=PASS')
print('VERTEX_SESSION_PORTAL_COMPOSER_CLEARANCE_FOCUS_000027H1=PASS')
