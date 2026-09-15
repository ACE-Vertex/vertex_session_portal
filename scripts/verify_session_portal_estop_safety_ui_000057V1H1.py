from __future__ import annotations
from pathlib import Path
import os, subprocess, sys, hashlib

ROOT = Path(os.environ.get('VERTEX_SESSION_PORTAL_ROOT', r'G:\Vertex_Project\Development\vertex_session_portal'))
SERVICE = ROOT / 'src/main/vra/vra-dispatch-service.ts'
PARENT = ROOT / 'scripts/verify_session_portal_estop_safety_ui_000057V1.py'
failures=[]

def check(name, ok):
    print(f'{name}={"PASS" if ok else "FAIL"}')
    if not ok: failures.append(name)

def read(p): return p.read_text(encoding='utf-8')

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

print('=== VERTEX SESSION PORTAL / E-STOP SAFETY UI 000057V1H1 VERIFY COMPAT REPAIR ===')
print(f'ROOT={ROOT}')
print('PRODUCTION_MUTATION_FROM_VERIFY=NO')
check('FILE_SERVICE', SERVICE.is_file())
check('FILE_PARENT_000057V1_VERIFY', PARENT.is_file())
if SERVICE.is_file():
    s=read(SERVICE)
    check('SAFETY_REJECT_RETRYABLE_PENDING', "error.code === 'SAFETY_STATE_REJECTED'" in s and "card.workstationRegistration = 'PENDING'" in s)
    check('FINAL_B_OFFLINE_COMPAT_EXPRESSION_RESTORED', "workstationRegistration = error instanceof WorkstationHttpError" in s and "? 'BLOCKED'" in s and ": 'PENDING'" in s)
    check('PERMANENT_HTTP_ERRORS_STILL_BLOCKED', '[400, 403, 409].includes(error.status)' in s and "? 'BLOCKED'" in s)
    check('APPROVED_VRA_NOT_REVOKED', 'Approval is never silently revoked' in s)
    check('SAFETY_RUNNING_GATE_PRESERVED', "this.workstationSafety.state !== 'RUNNING'" in s)
    check('EVIDENCE_OBSERVATION_PRESERVED', 'retrieveEvidence(card)' in s)

before={}
for p in ROOT.rglob('*.ts') if ROOT.is_dir() else []:
    try: before[str(p)]=sha(p)
    except OSError: pass

parent_exit=99
if PARENT.is_file():
    env=os.environ.copy()
    proc=subprocess.run([sys.executable,str(PARENT)],cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(proc.stdout)
    parent_exit=proc.returncode
print(f'PARENT_000057V1_EXIT={parent_exit}')
check('PARENT_000057V1_FULL_VERIFY', parent_exit == 0)

after={}
for p in ROOT.rglob('*.ts') if ROOT.is_dir() else []:
    try: after[str(p)]=sha(p)
    except OSError: pass
check('VERIFY_PORTAL_SOURCE_UNCHANGED', before == after)

if failures:
    print('RED=VERIFY_FAILURE')
    print('YELLOW=REQUIRES_REPAIR')
    print('FAILURES=' + ','.join(failures))
    print('VERTEX_SESSION_PORTAL_ESTOP_SAFETY_UI_000057V1H1=FAIL')
    raise SystemExit(1)
print('ROOT_CAUSE=PARENT_FINAL_B_STATIC_COMPAT_SHAPE_ONLY')
print('SAFETY_FUNCTIONAL_IMPLEMENTATION=PRESERVED')
print('RED=NONE')
print('YELLOW=NONE')
print('VERTEX_SESSION_PORTAL_ESTOP_SAFETY_UI_000057V1H1=PASS')
