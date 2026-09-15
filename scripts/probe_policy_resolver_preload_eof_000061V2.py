
from pathlib import Path
import shutil, subprocess, sys, tempfile

ROOT = Path.cwd()
PRELOAD = ROOT / "src/preload/index.ts"
API_BLOCK = "\n// VERTEX_SYSTEM_POLICY_RESOLVER_PRELOAD_EOF_PROBE_000061V2\ncontextBridge.exposeInMainWorld('vertexSystemPolicy', {\n  resolve: (policyId: string) =>\n    ipcRenderer.invoke('vertex:system-policy-resolve', policyId),\n  list: () =>\n    ipcRenderer.invoke('vertex:system-policy-list')\n})\n"

# Exit code:
# 0  = appending the same API at EOF typechecks
# 61 = ipcRenderer missing
# 62 = contextBridge missing
# 63 = duplicate/redeclare
# 64 = property/access mismatch
# 65 = assign/argument/overload mismatch
# 66 = implicit any
# 67 = unused symbol/import
# 68 = syntax/parser
# 69 = other preload TS error
# 70 = typecheck failed but no preload diagnostic
# 71 = restore failure
#
# Transactional. Production preload is restored before exit.

def read(p):
    return p.read_text(encoding="utf-8-sig", errors="replace")

def write(p, s):
    p.write_text(s, encoding="utf-8")

def run_typecheck():
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    return subprocess.run(
        [npm, "run", "typecheck"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True
    )

tmp = Path(tempfile.mkdtemp(prefix="vertex-preload-eof-probe-"))
backup = tmp / "index.ts"
code = 71

try:
    shutil.copy2(PRELOAD, backup)
    preload = read(PRELOAD)

    if "vertexSystemPolicy" in preload:
        code = 69
    elif "contextBridge" not in preload:
        code = 62
    elif "ipcRenderer" not in preload:
        code = 61
    else:
        write(PRELOAD, preload.rstrip() + "\n\n" + API_BLOCK.strip() + "\n")
        tc = run_typecheck()

        if tc.returncode == 0:
            code = 0
        else:
            text = (tc.stdout + "\n" + tc.stderr).replace("\\", "/").lower()
            preload_lines = [
                line for line in text.splitlines()
                if "src/preload/index.ts" in line or "preload/index.ts" in line
            ]
            diag = "\n".join(preload_lines)

            if "cannot find name 'ipcrenderer'" in diag or 'cannot find name "ipcrenderer"' in diag:
                code = 61
            elif "cannot find name 'contextbridge'" in diag or 'cannot find name "contextbridge"' in diag:
                code = 62
            elif any(x in diag for x in ["ts2451", "ts2300", "cannot redeclare", "duplicate identifier"]):
                code = 63
            elif "ts2339" in diag or ("property '" in diag and "does not exist" in diag):
                code = 64
            elif any(x in diag for x in ["ts2322", "ts2345", "ts2769", "not assignable", "no overload matches"]):
                code = 65
            elif any(x in diag for x in ["ts7006", "implicitly has an 'any' type", 'implicitly has an "any" type']):
                code = 66
            elif any(x in diag for x in ["ts6133", "is declared but its value is never read"]):
                code = 67
            elif any(x in diag for x in ["ts1005", "ts1128", "ts1109", "ts1160", "unterminated", "expected"]):
                code = 68
            elif diag:
                code = 69
            else:
                code = 70

finally:
    try:
        if backup.exists():
            shutil.copy2(backup, PRELOAD)
        else:
            code = 71
    except Exception:
        code = 71

sys.exit(code)
