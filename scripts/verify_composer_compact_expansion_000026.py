from pathlib import Path
import subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
css=(ROOT/'src/renderer/src/components/VeraSession/VeraSession.css').read_text(encoding='utf-8')
ts=(ROOT/'src/renderer/src/components/VeraSession/VeraSession.ts').read_text(encoding='utf-8')

def need(label, cond):
    if not cond:
        raise SystemExit('MISSING_CONTRACT:'+label)
    print(label+'=PASS')

print('VERTEX SESSION PORTAL / COMPOSER COMPACT EXPANSION VERIFY 000026')
print('ROOT='+str(ROOT))
need('COMPACT_COMPOSER_52', '.composer {' in css and 'min-height: 52px;' in css)
need('EXPANDED_COMPOSER_270', '.composer[data-expanded="true"]' in css and 'min-height: 270px;' in css)
need('COMPACT_TEXTAREA_38', 'min-height: 38px;' in css)
need('EXPANDED_TEXTAREA_238', '.composer[data-expanded="true"] textarea' in css and 'min-height: 238px;' in css)
need('COMPOSER_MAX_900', 'max-height: 900px !important;' in css)
need('AUTOGROW_THRESHOLD', 'const expansionTrigger = 150' in ts)
need('AUTOGROW_COMPACT', 'const compactHeight = 38' in ts)
need('AUTOGROW_EXPANDED_MIN', 'const expandedMinimum = 238' in ts)
need('AUTOGROW_MAX', 'const maximum = 850' in ts)
need('RESET_COMPACT', "form.dataset.expanded = 'false'" in ts and "textarea.style.height = '38px'" in ts)

npm='npm.cmd' if sys.platform.startswith('win') else 'npm'
print('RUN='+npm+' run build')
r=subprocess.run([npm,'run','build'],cwd=ROOT,text=True,capture_output=True)
print(r.stdout)
if r.stderr: print(r.stderr,file=sys.stderr)
if r.returncode != 0:
    raise SystemExit(r.returncode)
print('BUILD=PASS')
print('VERTEX_SESSION_PORTAL_COMPOSER_COMPACT_EXPANSION_000026=PASS')
