from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]; DEV=ROOT.parent
F={
'policy':ROOT/'src/main/vra/vra-download-destination-policy.ts','service':ROOT/'src/main/vra/vra-dispatch-service.ts','ipc':ROOT/'src/main/ipc/register-vra-dispatch-ipc.ts','contracts':ROOT/'src/shared/contracts.ts','preload':ROOT/'src/preload/index.ts','lane':ROOT/'src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts','dest':ROOT/'src/renderer/src/components/VraDispatchLane/VraDispatchDestinationControl.ts','mainframe':ROOT/'src/renderer/src/components/MainFrame/MainFrame.ts','mainframe_css':ROOT/'src/renderer/src/components/MainFrame/MainFrame.css'}
def txt(k): return F[k].read_text(encoding='utf-8-sig') if F[k].exists() else ''
def ck(n,o,fail): print(f"{n}={'PASS' if o else 'FAIL'}"); fail.append(n) if not o else None
def run(cmd):
 print('RUN='+' '.join(str(x) for x in cmd)); r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',shell=False); print(r.stdout); print(r.stderr,file=sys.stderr) if r.stderr else None; return r.returncode
def main():
 print('=== VERTEX SESSION PORTAL / DISPATCH BAY STAGING + HUMAN EXPORT VERIFY 000050 ==='); fail=[]
 p,s,i,c,pr,l,d,mf,mfc=[txt(k) for k in ['policy','service','ipc','contracts','preload','lane','dest','mainframe','mainframe_css']]
 ck('POLICY_PASSIVE','passive destination policy active' in p,fail)
 ck('POLICY_NO_WILL_DOWNLOAD',".on('will-download'" not in p and 'setSavePath(' not in p,fail)
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
 ck('VERTEX_LOGO_MARK_PRESERVED','class="brandMark"' in mf,fail)
 ck('VERA_04_05_ASSIGNMENT_RETIRED',"session.id !== 'vera-04' && session.id !== 'vera-05'" in mf,fail)
 owners=[]; saves=[]
 for path in ROOT.rglob('*.ts'):
  try: t=path.read_text(encoding='utf-8-sig')
  except: continue
  rel=str(path.relative_to(ROOT)).replace('\\','/')
  if ".on('will-download'" in t or '.on("will-download"' in t: owners.append(rel)
  if 'item.setSavePath(' in t: saves.append(rel)
 print('WILL_DOWNLOAD_OWNERS='+';'.join(owners)); ck('SINGLE_WILL_DOWNLOAD_OWNER',owners==['src/main/vra/vra-dispatch-service.ts'],fail)
 print('SET_SAVE_PATH_OWNERS='+';'.join(saves)); ck('SINGLE_VRA_SAVE_PATH_OWNER',saves==['src/main/vra/vra-dispatch-service.ts'],fail)
 if fail: print('STATIC_FAILURES='+','.join(fail)); raise SystemExit(2)
 npm='npm.cmd' if sys.platform.startswith('win') else 'npm'; ck('SOURCE_BUILD',run([npm,'run','build'])==0,fail)
 if fail: raise SystemExit(3)
 ck('PUBLISH_CANONICAL_LATEST',run([sys.executable,'scripts/publish_latest_to_vertex_workstation_000047.py'])==0,fail)
 ck('VERIFY_CANONICAL_LATEST',run([sys.executable,'scripts/verify_workstation_latest_session_portal_000047.py'])==0,fail)
 launcher=DEV/'vertex_workstation'/'START_SESSION_PORTAL_LATEST.cmd'; latest=DEV/'vertex_workstation'/'SESSION_PORTAL_LATEST'/'Vertex Session Portal.exe'
 ck('CANONICAL_LAUNCHER_PRESENT',launcher.exists(),fail); ck('LATEST_EXE_PRESENT',latest.exists(),fail)
 if fail: print('FAILURES='+','.join(fail)); raise SystemExit(4)
 print('CANONICAL_LAUNCHER='+str(launcher)); print('LATEST_EXE='+str(latest)); print('MANUAL_ACCEPTANCE=DOWNLOAD_VRA_CARD_APPEARS_THEN_EXPORT_TO_SELECTED_FOLDER_THEN_OPTIONAL_SEND_TO_WORKS'); print('VERTEX_SESSION_PORTAL_DISPATCH_BAY_STAGING_EXPORT_000050=PASS')
if __name__=='__main__': main()
