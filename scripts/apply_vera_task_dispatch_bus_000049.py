from pathlib import Path
import shutil,subprocess,sys
ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal"); MAIN=ROOT/"src/renderer/src/components/MainFrame/MainFrame.ts"; BRIDGE=ROOT/"src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts"; IMPORT="import '../VeraBrowserSession/VeraTaskDispatchBridge'\n"; BACKUP=ROOT/"runtime/patch-backups/000049/MainFrame.ts"
def emit(v,s=sys.stdout):
 e=getattr(s,"encoding",None) or "utf-8";t=str(v).encode(e,errors="backslashreplace").decode(e,errors="replace");s.write(t+("" if t.endswith("\n") else "\n"))
def build():
 npm=shutil.which("npm.cmd") or shutil.which("npm");
 if not npm: raise RuntimeError("NPM_NOT_FOUND")
 cp=subprocess.run([npm,"run","build"],cwd=ROOT,text=True,capture_output=True,encoding="utf-8",errors="replace");emit(cp.stdout);emit(cp.stderr,sys.stderr);return cp.returncode
def main():
 print("=== VERA TASK DISPATCH BUS APPLY 000049 ===");
 if not MAIN.exists() or not BRIDGE.exists(): raise RuntimeError("REQUIRED_SOURCE_MISSING")
 before=MAIN.read_text(encoding="utf-8")
 for m in ("vera-browser-session","vertex-vra-dispatch-lane"):
  if m not in before: raise RuntimeError("CURRENT_SOURCE_ANCHOR_MISSING:"+m)
 BACKUP.parent.mkdir(parents=True,exist_ok=True);BACKUP.write_text(before,encoding="utf-8")
 if IMPORT.strip() not in before: MAIN.write_text(IMPORT+before,encoding="utf-8")
 try:
  if build()!=0: raise RuntimeError("BUILD_FAILED")
 except Exception:
  MAIN.write_text(before,encoding="utf-8");print("TRANSACTION_ROLLBACK=PASS");raise
 print("SIDE_EFFECT_IMPORT_COMPLETE_STATEMENT=PASS");print("TASK_DISPATCH_BUS_APPLY=PASS")
if __name__=="__main__": main()
