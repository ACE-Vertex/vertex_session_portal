from pathlib import Path
import datetime as dt
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'EVIDENCE' / 'DISPATCH_BAY_STAGING_EXPORT_000050'
STAMP = dt.datetime.now().strftime('%Y%m%d-%H%M%S')
BACKUP = EVIDENCE / STAMP

CONTRACTS = ROOT / 'src/shared/contracts.ts'
PRELOAD = ROOT / 'src/preload/index.ts'
MAINFRAME = ROOT / 'src/renderer/src/components/MainFrame/MainFrame.ts'
MAINFRAME_CSS = ROOT / 'src/renderer/src/components/MainFrame/MainFrame.css'
SCALER_CSS = ROOT / 'src/renderer/src/components/VeraWindowScaler/VeraWindowScaler.css'
LANE_CSS = ROOT / 'src/renderer/src/components/VraDispatchLane/VraDispatchLane.css'
TOUCH = [CONTRACTS, PRELOAD, MAINFRAME, MAINFRAME_CSS, SCALER_CSS, LANE_CSS]

M49B='/* VERTEX_SESSION_PORTAL_MOCK_FIDELITY_000049_BEGIN */'
M49E='/* VERTEX_SESSION_PORTAL_MOCK_FIDELITY_000049_END */'
M50B='/* VERTEX_SESSION_PORTAL_DISPATCH_BAY_000050_BEGIN */'
M50E='/* VERTEX_SESSION_PORTAL_DISPATCH_BAY_000050_END */'
S50B='/* VERTEX_SESSION_PORTAL_SCALER_000050_BEGIN */'
S50E='/* VERTEX_SESSION_PORTAL_SCALER_000050_END */'
L50B='/* VERTEX_SESSION_PORTAL_DISPATCH_ACTIONS_000050_BEGIN */'
L50E='/* VERTEX_SESSION_PORTAL_DISPATCH_ACTIONS_000050_END */'


def read(p):
    if not p.exists(): raise RuntimeError(f'MISSING_REQUIRED_FILE:{p}')
    return p.read_text(encoding='utf-8-sig')

def write(p,t): p.write_bytes(t.replace('\r\n','\n').replace('\r','\n').encode('utf-8'))

def backup():
    BACKUP.mkdir(parents=True, exist_ok=True)
    for p in TOUCH:
        if p.exists():
            d=BACKUP/p.relative_to(ROOT); d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,d)

def restore():
    if not BACKUP.exists(): return
    for s in BACKUP.rglob('*'):
        if s.is_file():
            d=ROOT/s.relative_to(BACKUP); d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(s,d)

def strip(t,b,e): return re.sub(re.escape(b)+r'.*?'+re.escape(e),'',t,flags=re.S).rstrip()+'\n'

def patch_contracts(t):
    if 'exportVraCard(cardId: string): Promise<string>' not in t:
        a='dispatchVraCard(cardId: string): Promise<VraDispatchCard>\n'
        if a not in t: raise RuntimeError('CONTRACT_EXPORT_API_ANCHOR_NOT_FOUND')
        t=t.replace(a,a+'exportVraCard(cardId: string): Promise<string>\n',1)
    if "captureOwner: 'VRA_DISPATCH_SERVICE_ONLY'" not in t:
        a="  browserDomScrape: 'NO'"
        if a not in t: raise RuntimeError('CONTRACT_CAPTURE_OWNER_ANCHOR_NOT_FOUND')
        t=t.replace(a,"  captureOwner: 'VRA_DISPATCH_SERVICE_ONLY',\n  exportAuthority: 'HUMAN',\n  exportMode: 'COPY_FROM_PORTAL_STAGING',\n"+a,1)
    return t

def patch_preload(t):
    if 'exportVraCard:' in t: return t
    pat=re.compile(r"dispatchVraCard:\s*\(cardId:\s*string\):\s*Promise<VraDispatchCard>\s*=>\s*ipcRenderer\.invoke\('workstation:vra-dispatch-card',\s*cardId\),",re.S)
    m=pat.search(t)
    if not m: raise RuntimeError('PRELOAD_EXPORT_API_ANCHOR_NOT_FOUND')
    ins=m.group(0)+"\n\nexportVraCard:\n  (cardId: string): Promise<string> =>\n    ipcRenderer.invoke('workstation:vra-export-card', cardId),"
    return t[:m.start()]+ins+t[m.end():]

def patch_mainframe(t):
    t=re.sub(r'\s*<div class="primaryEntry"[^>]*>\s*<span class="primaryEntryGlyph">.*?</span>\s*<span>PRIMARY ENTRY</span>\s*</div>\s*','\n          ',t,count=1,flags=re.S)
    if 'PRIMARY ENTRY' in t or 'class="primaryEntry"' in t: raise RuntimeError('PRIMARY_ENTRY_UI_NOT_FULLY_RETIRED')
    return t

MF_CSS='''
.topbar { min-height:50px; grid-template-columns:340px minmax(320px,1fr) auto; gap:12px; padding:0 14px; border-bottom-color:#1C2935; background:linear-gradient(180deg,rgba(10,25,47,.98),rgba(7,11,16,.99)); box-shadow:0 8px 28px rgba(0,0,0,.16),inset 0 -1px 0 rgba(58,184,255,.04); }
.brand { display:flex; align-items:center; justify-self:start; min-width:0; max-width:178px; gap:8px; white-space:nowrap; }
.brandMark { position:relative; display:inline-block; width:27px; height:27px; flex:0 0 27px; filter:drop-shadow(0 0 8px rgba(22,140,255,.22)); }
.brandMark i { position:absolute; top:2px; width:13px; height:23px; background:linear-gradient(180deg,#3AB8FF,#168CFF 62%,#0C5DB7); clip-path:polygon(0 0,100% 0,48% 100%); }
.brandMark i:first-child { left:0; transform:skewX(-8deg); }
.brandMark i:last-child { right:0; transform:skewX(8deg); opacity:.82; }
.vertex { color:#CBD5DF; font-size:14px; font-weight:900; letter-spacing:.14em; }
.product { margin-left:1px; padding-left:8px; border-left:1px solid #26394B; color:#AEBBC8; font-size:10px; font-weight:650; letter-spacing:.01em; text-transform:none; }
.commandSearch { justify-self:stretch; max-width:760px; min-width:260px; height:31px; border-color:#1C2935; border-radius:8px; background:#0C121A; }
.system { gap:10px; white-space:nowrap; }
.main { min-height:0; }
.sessionViewport { background:#070B10; }
.sessionTrack { gap:6px; padding:6px; }
.statusbar { border-top-color:#1C2935; background:#070B10; }
@media (max-width:1680px) { .topbar { grid-template-columns:300px minmax(250px,1fr) auto; } .system .telemetry:nth-of-type(-n+2) { display:none; } }
'''
SC_CSS='''
:host { top:9px; left:184px; z-index:5000; }
.scaler { height:31px; border-color:#26394B; border-radius:8px; background:linear-gradient(180deg,#111923,#0C121A); box-shadow:0 0 14px rgba(22,140,255,.10); }
button[data-active] { border-color:#3AB8FF; background:#102C44; color:#3AB8FF; }
@media (max-width:1680px) { :host { left:166px; } }
'''
LN_CSS='''
.notice { overflow:hidden; margin:8px 10px 0; padding:7px 8px; border:1px solid rgba(85,214,158,.22); border-radius:7px; background:rgba(9,47,37,.24); color:#55D69E; text-overflow:ellipsis; white-space:nowrap; font-size:8px; }
.cardActions .export { border-color:rgba(58,184,255,.42); background:#102C44; color:#3AB8FF; }
.cardActions .export:hover:not(:disabled) { border-color:#3AB8FF; box-shadow:0 0 12px rgba(22,140,255,.15); }
'''

def replace_css(p,oldb,olde,newb,newe,block):
    t=strip(read(p),oldb,olde); t=strip(t,newb,newe); write(p,t+'\n'+newb+'\n'+block.strip()+'\n'+newe+'\n')

def build():
    npm='npm.cmd' if sys.platform.startswith('win') else 'npm'
    r=subprocess.run([npm,'run','build'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',shell=False)
    print(r.stdout)
    if r.stderr: print(r.stderr,file=sys.stderr)
    print(f'BUILD_EXIT={r.returncode}')
    return r.returncode

def main():
    print('=== VERTEX SESSION PORTAL / DISPATCH BAY STAGING + HUMAN EXPORT APPLY 000050 ===')
    print(f'ROOT={ROOT}\nTRANSACTION_BACKUP={BACKUP}')
    backup()
    try:
        write(CONTRACTS,patch_contracts(read(CONTRACTS)))
        write(PRELOAD,patch_preload(read(PRELOAD)))
        write(MAINFRAME,patch_mainframe(read(MAINFRAME)))
        replace_css(MAINFRAME_CSS,M49B,M49E,M50B,M50E,MF_CSS)
        replace_css(SCALER_CSS,M49B,M49E,S50B,S50E,SC_CSS)
        replace_css(LANE_CSS,L50B,L50E,L50B,L50E,LN_CSS)
        if build()!=0: raise RuntimeError('SESSION_PORTAL_000050_BUILD_FAILED')
    except Exception:
        restore(); print('TRANSACTION_ROLLBACK=PASS'); raise
    print('TRANSACTION_ROLLBACK=NOT_REQUIRED')
    print('VRA_CAPTURE_OWNER=VRA_DISPATCH_SERVICE_ONLY')
    print('VRA_FLOW=CHATGPT_TO_STAGING_TO_DISPATCH_BAY_TO_HUMAN_EXPORT_OR_WORKS')
    print('PRIMARY_ENTRY_UI=RETIRED')
    print('CANONICAL_LAUNCHER=UNCHANGED')
    print('LOGO=EXISTING_SELECTED_VERTEX_MARK_PRESERVED')
    print('VERTEX_SESSION_PORTAL_DISPATCH_BAY_STAGING_EXPORT_000050_APPLY=PASS')

if __name__=='__main__': main()
