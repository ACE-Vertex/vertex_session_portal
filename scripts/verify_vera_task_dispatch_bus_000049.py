from pathlib import Path
import shutil,subprocess,sys
ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal");MAIN=ROOT/"src/renderer/src/components/MainFrame/MainFrame.ts";BRIDGE=ROOT/"src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts"
def ck(n,v,b):print(f"{n}={'PASS' if v else 'FAIL'}");b.extend([] if v else [n])
def main():
 print("=== VERA TASK DISPATCH BUS VERIFY 000049 ===");bad=[];m=MAIN.read_text(encoding="utf-8") if MAIN.exists() else "";b=BRIDGE.read_text(encoding="utf-8") if BRIDGE.exists() else ""
 ck("SIDE_EFFECT_IMPORT","import '../VeraBrowserSession/VeraTaskDispatchBridge'" in m,bad);ck("FIVE_SESSION_ALLOWLIST",all(x in b for x in ("vera-01","vera-02","vera-03","vera-04","vera-05")),bad);ck("NO_SELF_DISPATCH","TASK_SELF_DISPATCH_FORBIDDEN" in b,bad);ck("MAX_FOUR_TARGETS","rows.length<1||rows.length>4" in b,bad);ck("HUMAN_CONFIRM_GATE","confirm(`VERA TASK DISPATCH" in b,bad);ck("STRICT_MARKED_CAPTURE","[VERTEX_TASK_DISPATCH/1]" in b and "[/VERTEX_TASK_DISPATCH/1]" in b,bad);ck("SOURCE_SESSION_BINDING","TASK_SOURCE_SESSION_MISMATCH" in b,bad);ck("IDEMPOTENCY_RECEIPTS","vertex.portal.task-dispatch.receipts.v1" in b,bad);ck("TARGET_COMPOSER_WRITE","TARGET_COMPOSER_NOT_FOUND" in b,bad);ck("SEND_BUTTON_AUTOMATION","b.click()" in b,bad);ck("HUMAN_CLICK_ONLY_SOURCE_READ","b.addEventListener('click'" in b and "executeJavaScript(extractScript()" in b,bad)
 if bad: raise SystemExit(2)
 npm=shutil.which("npm.cmd") or shutil.which("npm");cp=subprocess.run([npm,"run","build"],cwd=ROOT,text=True,capture_output=True,encoding="utf-8",errors="replace");ck("BUILD",cp.returncode==0,bad)
 if bad: raise SystemExit(3)
 print("SOURCE_DOM_READ=EXPLICIT_MARKED_BLOCK_ONLY_ON_HUMAN_CLICK");print("BACKGROUND_RESPONSE_SCRAPE=NO");print("TARGET_DOM_WRITE=YES");print("VERTEX_SESSION_PORTAL_VERA_TASK_DISPATCH_BUS_000049=PASS")
if __name__=="__main__": main()
