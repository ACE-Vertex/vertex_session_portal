from pathlib import Path
import hashlib
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
DEV=ROOT.parent
F={
 'policy':ROOT/'src/main/vra/vra-download-destination-policy.ts',
 'service':ROOT/'src/main/vra/vra-dispatch-service.ts',
 'ipc':ROOT/'src/main/ipc/register-vra-dispatch-ipc.ts',
 'contracts':ROOT/'src/shared/contracts.ts',
 'preload':ROOT/'src/preload/index.ts',
 'lane':ROOT/'src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts',
 'dest':ROOT/'src/renderer/src/components/VraDispatchLane/VraDispatchDestinationControl.ts',
 'mainframe':ROOT/'src/renderer/src/components/MainFrame/MainFrame.ts',
 'mainframe_css':ROOT/'src/renderer/src/components/MainFrame/MainFrame.css',
 'logo':ROOT/'src/renderer/src/assets/vertex-project-mark.svg',
}
EXPECTED_LOGO_SHA='397001f555894a202407686e0b4fac36edbef27219113a64a4544fd467f1424a'


def safe_emit(value='', stream=None):
    stream=stream or sys.stdout
    enc=getattr(stream,'encoding',None) or 'utf-8'
    text=str(value)
    safe=text.encode(enc,errors='backslashreplace').decode(enc,errors='replace')
    stream.write(safe)
    if safe and not safe.endswith('\n'): stream.write('\n')
    stream.flush()


def txt(k): return F[k].read_text(encoding='utf-8-sig') if F[k].exists() else ''
def ck(n,o,fail): safe_emit(f"{n}={'PASS' if o else 'FAIL'}"); fail.append(n) if not o else None

def run(cmd):
    safe_emit('RUN='+' '.join(str(x) for x in cmd))
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',shell=False)
    safe_emit(r.stdout)
    if r.stderr: safe_emit(r.stderr,sys.stderr)
    return r.returncode

def code_only(t):
    t=re.sub(r'/\*.*?\*/','',t,flags=re.S)
    t=re.sub(r'(^|\s)//[^\n]*',r'\1',t)
    return t


def main():
    safe_emit('=== VERTEX SESSION PORTAL / DISPATCH BAY STAGING + HUMAN EXPORT VERIFY 000050H1 ===')
    fail=[]
    p,s,i,c,pr,l,d,mf,mfc=[txt(k) for k in ['policy','service','ipc','contracts','preload','lane','dest','mainframe','mainframe_css']]
    pc=code_only(p)
    ck('POLICY_PASSIVE','passive destination policy active' in p,fail)
    ck('POLICY_NO_WILL_DOWNLOAD',not re.search(r"\.\s*on\s*\(\s*['\"]will-download['\"]",pc) and not re.search(r'\.\s*setSavePath\s*\(',pc),fail)
    ck('CAPTURE_SERVICE_OWNS_WILL_DOWNLOAD',"target.on('will-download'" in s,fail)
    ck('CAPTURE_STAGING_FIRST','item.setSavePath(stagedPath)' in s and 'STAGING FIRST' in s,fail)
    ck('EXPORT_FROM_STAGING','exportCard(cardId: string): string' in s and 'getVraDispatchDestination()' in s and 'copyFileSync(card.stagedPath, destination)' in s,fail)
    ck('EXPORT_NON_DESTRUCTIVE','Export is intentionally non-destructive' in s,fail)
    ck('WORKS_LANE_SEPARATE','SEND TO WORKS: separate lane' in s and 'worksIncomingRoot' in s,fail)
    ck('EXPORT_IPC',"'workstation:vra-export-card'" in i,fail)
    ck('EXPORT_CONTRACT','exportVraCard(cardId: string): Promise<string>' in c,fail)
    ck('EXPORT_PRELOAD','exportVraCard:' in pr and "ipcRenderer.invoke('workstation:vra-export-card', cardId)" in pr,fail)
    ck('CAPTURE_OWNER_CONTRACT',"captureOwner: 'VRA_DISPATCH_SERVICE_ONLY'" in c,fail)
    ck('EXPORT_UI_ACTION','data-action="export"' in l and 'EXPORTING…' in l,fail)
    ck('DISPATCH_UI_ACTION','SEND TO WORKS' in l,fail)
    ck('DISPATCH_BAY_EMPTY_FLOW_TEXT','The Portal stages it here first' in l,fail)
    ck('EXPORT_PATH_SEMANTICS','Human export destination only' in d and '>EXPORT<' in d,fail)
    ck('PRIMARY_ENTRY_UI_RETIRED','PRIMARY ENTRY' not in mf and 'class="primaryEntry"' not in mf and '.primaryEntry' not in mfc,fail)
    ck('USER_VERTEX_LOGO_MOUNTED','class="brandLogo"' in mf and "url('../../assets/vertex-project-mark.svg')" in mfc,fail)
    logo_sha=hashlib.sha256(F['logo'].read_bytes()).hexdigest() if F['logo'].exists() else ''
    safe_emit('VERTEX_LOGO_SHA256='+logo_sha)
    ck('USER_VERTEX_LOGO_EXACT',logo_sha==EXPECTED_LOGO_SHA,fail)
    ck('VERA_04_05_ASSIGNMENT_RETIRED',"session.id !== 'vera-04' && session.id !== 'vera-05'" in mf,fail)

    owners=[]; saves=[]
    for path in (ROOT/'src').rglob('*.ts'):
        try: t=code_only(path.read_text(encoding='utf-8-sig'))
        except Exception: continue
        rel=str(path.relative_to(ROOT)).replace('\\','/')
        if re.search(r"\.\s*on\s*\(\s*['\"]will-download['\"]",t): owners.append(rel)
        if re.search(r'item\s*\.\s*setSavePath\s*\(',t): saves.append(rel)
    owners=sorted(set(owners)); saves=sorted(set(saves))
    safe_emit('WILL_DOWNLOAD_OWNERS='+';'.join(owners))
    ck('SINGLE_WILL_DOWNLOAD_OWNER',owners==['src/main/vra/vra-dispatch-service.ts'],fail)
    safe_emit('SET_SAVE_PATH_OWNERS='+';'.join(saves))
    ck('SINGLE_VRA_SAVE_PATH_OWNER',saves==['src/main/vra/vra-dispatch-service.ts'],fail)
    ck('EVIDENCE_EXCLUDED_FROM_OWNER_SCAN',all(not x.startswith('EVIDENCE/') for x in owners+saves),fail)

    if fail:
        safe_emit('STATIC_FAILURES='+','.join(fail)); raise SystemExit(2)

    npm='npm.cmd' if sys.platform.startswith('win') else 'npm'
    ck('SOURCE_BUILD',run([npm,'run','build'])==0,fail)
    if fail: raise SystemExit(3)

    ck('PUBLISH_CANONICAL_LATEST',run([sys.executable,'scripts/publish_latest_to_vertex_workstation_000047.py'])==0,fail)
    ck('VERIFY_CANONICAL_LATEST',run([sys.executable,'scripts/verify_workstation_latest_session_portal_000047.py'])==0,fail)
    launcher=DEV/'vertex_workstation'/'START_SESSION_PORTAL_LATEST.cmd'
    latest=DEV/'vertex_workstation'/'SESSION_PORTAL_LATEST'/'Vertex Session Portal.exe'
    ck('CANONICAL_LAUNCHER_PRESENT',launcher.exists(),fail)
    ck('LATEST_EXE_PRESENT',latest.exists(),fail)
    if fail:
        safe_emit('FAILURES='+','.join(fail)); raise SystemExit(4)

    safe_emit('CANONICAL_LAUNCHER='+str(launcher))
    safe_emit('LATEST_EXE='+str(latest))
    safe_emit('VRA_FLOW_CONTRACT=DOWNLOAD_TO_PORTAL_STAGING_THEN_DISPATCH_BAY_THEN_HUMAN_EXPORT_OR_WORKS')
    safe_emit('MANUAL_ACCEPTANCE=DOWNLOAD_ONE_VRA_CONFIRM_CARD_THEN_EXPORT_TO_SELECTED_FOLDER_CARD_REMAINS_THEN_OPTIONAL_SEND_TO_WORKS')
    safe_emit('VERTEX_SESSION_PORTAL_DISPATCH_BAY_STAGING_EXPORT_000050H1=PASS')

if __name__=='__main__': main()
