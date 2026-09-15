from pathlib import Path
import ast
import json

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
PKG = ROOT / "package.json"
LAUNCHER = ROOT / "VERTEX_SESSION_PORTAL_CURRENT.cmd"

failures = []

def ck(name, ok, detail=""):
    print(name + "=" + ("PASS" if ok else "FAIL") + ((" " + detail) if detail else ""))
    if not ok:
        failures.append(name)

ck("PACKAGE_PRESENT", PKG.is_file())
ck("LAUNCHER_PRESENT", LAUNCHER.is_file())

pkg = json.loads(PKG.read_text(encoding="utf-8")) if PKG.is_file() else {}
text = LAUNCHER.read_text(encoding="utf-8") if LAUNCHER.is_file() else ""

ck("MAIN_CONTRACT", pkg.get("main") == "./out/main/index.js", str(pkg.get("main")))
ck(
    "BUILD_CONTRACT",
    pkg.get("scripts", {}).get("build") == "npm run typecheck && electron-vite build",
    str(pkg.get("scripts", {}).get("build"))
)

for token in (
    "VXS_BUILD_BEFORE_LAUNCH_GUARD_000028",
    'cd /d "%~dp0"',
    "call npm.cmd run build",
    'if not exist "out\\main\\index.js"',
    'call "node_modules\\.bin\\electron.cmd" .',
    "Electron will NOT be started",
):
    ck("LAUNCHER_" + token.replace(" ", "_").replace('"', "").replace("\\", "_").replace(".", "_").upper(), token in text)

# Guard policy: launcher may build and launch only. It must not kill existing
# processes, mutate Git, manipulate ACK/Return Bus, or bypass Human Gate.
lower = text.lower()
ck("NO_TASKKILL", "taskkill" not in lower)
ck("NO_STOP_PROCESS", "stop-process" not in lower)
ck("NO_GIT_MUTATION", "git reset" not in lower and "git checkout" not in lower and "git clean" not in lower)
ck("NO_ACK_PATH", "ack" not in lower)
ck("NO_RETURN_QUEUE", "return_queue" not in lower and "return-queue" not in lower)
ck("NO_HUMAN_GATE_BYPASS", "human_apply" not in lower)
# Verify must not execute build/runtime commands. Use AST inspection instead of
# string-searching this verifier's own source (which would self-match).
verifier_source = Path(__file__).read_text(encoding="utf-8")
verifier_tree = ast.parse(verifier_source)

imported_modules = set()
for node in ast.walk(verifier_tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            imported_modules.add(alias.name.split(".")[0])
    elif isinstance(node, ast.ImportFrom) and node.module:
        imported_modules.add(node.module.split(".")[0])

ck("NO_VERIFY_SUBPROCESS_IMPORT", "subprocess" not in imported_modules)
ck("NO_VERIFY_OS_IMPORT", "os" not in imported_modules)

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

print("VXS_BUILD_BEFORE_LAUNCH_GUARD_000028=PASS")
raise SystemExit(0)
