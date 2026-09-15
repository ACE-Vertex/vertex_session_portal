
from pathlib import Path
import re, shutil, subprocess, sys, time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
POLICY = ROOT / "src/shared/system-policy-registry.ts"
MAIN_INDEX = ROOT / "src/main/index.ts"
PRELOAD = ROOT / "src/preload/index.ts"
IPC_FILE = ROOT / "src/main/ipc/register-system-policy-ipc.ts"
STAMP = time.strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / "EVIDENCE" / "SYSTEM_POLICY_RESOLVER_READONLY_000062V2" / STAMP
MARKER = "VERTEX_SYSTEM_POLICY_RESOLVER_000062V2"

RESOLVER_CODE = '\n// VERTEX_SYSTEM_POLICY_RESOLVER_000062V2\nexport function resolveActiveSystemPolicy(\n  policyId: string\n): KnownSystemPolicyRecord | null {\n  const records = POLICY_RECORDS.filter(record => record.policy_id === policyId)\n  if (records.length === 0) return null\n\n  const activeVersion = records[0]?.active_version\n  if (!activeVersion) return null\n\n  return records.find(record => record.policy_version === activeVersion) ?? null\n}\n\nexport function listActiveSystemPolicies(): readonly KnownSystemPolicyRecord[] {\n  const seen = new Set<string>()\n  const active: KnownSystemPolicyRecord[] = []\n\n  for (const record of POLICY_RECORDS) {\n    if (seen.has(record.policy_id)) continue\n    seen.add(record.policy_id)\n\n    const resolved = resolveActiveSystemPolicy(record.policy_id)\n    if (resolved) active.push(resolved)\n  }\n\n  return active\n}\n'
IPC_CODE = "import { ipcMain } from 'electron'\nimport {\n  listActiveSystemPolicies,\n  resolveActiveSystemPolicy\n} from '../../shared/system-policy-registry'\n\n// VERTEX_SYSTEM_POLICY_RESOLVER_000062V2\nexport function registerSystemPolicyIpc(): void {\n  ipcMain.handle('vertex:system-policy-resolve', (_event, policyId: unknown) => {\n    if (typeof policyId !== 'string' || policyId.trim().length === 0) return null\n    return resolveActiveSystemPolicy(policyId.trim())\n  })\n\n  ipcMain.handle('vertex:system-policy-list', () => listActiveSystemPolicies())\n}\n"
API_BLOCK = "\n// VERTEX_SYSTEM_POLICY_RESOLVER_000062V2\ncontextBridge.exposeInMainWorld('vertexSystemPolicy', {\n  resolve: (policyId: string) =>\n    ipcRenderer.invoke('vertex:system-policy-resolve', policyId),\n  list: () =>\n    ipcRenderer.invoke('vertex:system-policy-list')\n})\n"

def log(v=""):
    print(str(v).encode("ascii","backslashreplace").decode("ascii"))

def read(p):
    if not p.exists():
        raise RuntimeError(f"MISSING:{p}")
    return p.read_text(encoding="utf-8-sig", errors="replace")

def write(p, s):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")

def backup(p):
    if p.exists():
        dest = BACKUP / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)

def restore():
    for p in (POLICY, MAIN_INDEX, PRELOAD):
        b = BACKUP / p.relative_to(ROOT)
        if b.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(b, p)

    ipc_backup = BACKUP / IPC_FILE.relative_to(ROOT)
    if ipc_backup.exists():
        shutil.copy2(ipc_backup, IPC_FILE)
    elif IPC_FILE.exists():
        IPC_FILE.unlink()

def run_npm(args):
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    p = subprocess.run(
        [npm, *args], cwd=ROOT, text=True,
        encoding="utf-8", errors="replace", capture_output=True
    )
    log(f"RUN={npm} {' '.join(args)}")
    log(f"EXIT={p.returncode}")
    for line in (p.stdout + "\n" + p.stderr).splitlines()[-160:]:
        log(line)
    return p.returncode

policy0 = read(POLICY)
main0 = read(MAIN_INDEX)
preload0 = read(PRELOAD)

# Phase 1 must be present and untouched.
if "SYSTEM_POLICY_REGISTRY_SCHEMA" not in policy0:
    raise SystemExit("PHASE1_POLICY_REGISTRY_MISSING")
if "vertex.vra.issue" not in policy0 or "1.0.0" not in policy0:
    raise SystemExit("PHASE1_ACTIVE_POLICY_MISSING")
if "NO_POLICY_MUTATION_API_IN_PHASE1" not in policy0:
    raise SystemExit("PHASE1_READONLY_GUARD_MISSING")

# Fail closed against duplicate application.
if "resolveActiveSystemPolicy" in policy0:
    raise SystemExit("POLICY_RESOLVER_ALREADY_PRESENT")
if "registerSystemPolicyIpc" in main0:
    raise SystemExit("MAIN_POLICY_IPC_ALREADY_PRESENT")
if "vertexSystemPolicy" in preload0:
    raise SystemExit("PRELOAD_POLICY_API_ALREADY_PRESENT")
if IPC_FILE.exists():
    raise SystemExit("POLICY_IPC_FILE_ALREADY_PRESENT")

BACKUP.mkdir(parents=True, exist_ok=True)
for p in (POLICY, MAIN_INDEX, PRELOAD, IPC_FILE):
    backup(p)

try:
    # 1. Read-only resolver functions in the System Policy Registry.
    write(POLICY, policy0.rstrip() + "\n\n" + RESOLVER_CODE.strip() + "\n")

    # 2. Dedicated read-only IPC.
    write(IPC_FILE, IPC_CODE)

    # 3. Main registration.
    main = main0
    import_line = "import { registerSystemPolicyIpc } from './ipc/register-system-policy-ipc'"
    if import_line not in main:
        imports = list(re.finditer(r"^import .+$", main, flags=re.M))
        if not imports:
            raise RuntimeError("MAIN_IMPORT_REGION_NOT_FOUND")
        pos = imports[-1].end()
        main = main[:pos] + "\n" + import_line + main[pos:]

    if "registerSystemPolicyIpc()" not in main:
        anchor = re.search(r"^[ \t]*registerVraDispatchIpc\([^\n]*\)[ \t]*$", main, flags=re.M)
        if anchor is None:
            anchor = re.search(
                r"^(?P<indent>[ \t]*)register[A-Za-z0-9_]+Ipc\([^\n]*\)[ \t]*$",
                main,
                flags=re.M
            )
        if anchor is None:
            raise RuntimeError("MAIN_IPC_REGISTRATION_ANCHOR_NOT_FOUND")
        indent = re.match(r"[ \t]*", anchor.group(0)).group(0)
        main = main[:anchor.end()] + f"\n{indent}// {MARKER}\n{indent}registerSystemPolicyIpc()" + main[anchor.end():]

    write(MAIN_INDEX, main)

    # 4. SAFE preload exposure: verified EOF top-level placement.
    if "contextBridge" not in preload0 or "ipcRenderer" not in preload0:
        raise RuntimeError("PRELOAD_ELECTRON_BRIDGE_SYMBOLS_MISSING")
    preload = preload0.rstrip() + "\n\n" + API_BLOCK.strip() + "\n"
    write(PRELOAD, preload)

    # 5. Static invariants.
    policy_now = read(POLICY)
    ipc_now = read(IPC_FILE)
    main_now = read(MAIN_INDEX)
    preload_now = read(PRELOAD)

    checks = {
        "RESOLVER_EXPORT": "resolveActiveSystemPolicy" in policy_now,
        "LIST_ACTIVE_EXPORT": "listActiveSystemPolicies" in policy_now,
        "IPC_RESOLVE": "vertex:system-policy-resolve" in ipc_now,
        "IPC_LIST": "vertex:system-policy-list" in ipc_now,
        "IPC_READONLY": "ipcMain.handle" in ipc_now and "ipcMain.on" not in ipc_now,
        "MAIN_IMPORT": import_line in main_now,
        "MAIN_REGISTER": "registerSystemPolicyIpc()" in main_now,
        "PRELOAD_API": "vertexSystemPolicy" in preload_now,
        "PRELOAD_RESOLVE": "vertex:system-policy-resolve" in preload_now,
        "PRELOAD_LIST": "vertex:system-policy-list" in preload_now,
        "PRELOAD_EOF_MARKER": preload_now.rstrip().endswith("})"),
        "NO_WRITE_CHANNEL": "system-policy-set" not in (ipc_now + preload_now),
        "NO_REGISTRAR": "PolicyRegistrar" not in (policy_now + ipc_now + main_now + preload_now),
        "PHASE1_GUARD_PRESERVED": "NO_POLICY_MUTATION_API_IN_PHASE1" in policy_now,
    }
    for name, ok in checks.items():
        log(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"CHECK_FAILED:{name}")

    # 6. Compile and build.
    if run_npm(["run", "typecheck"]) != 0:
        raise RuntimeError("TYPECHECK_FAILED")

    if run_npm(["run", "build"]) != 0:
        raise RuntimeError("BUILD_FAILED")

    log("PHASE=SYSTEM_POLICY_RESOLVER")
    log("POLICY=vertex.vra.issue/1.0.0")
    log("WINDOW_API=vertexSystemPolicy")
    log("READ_API=resolve,list")
    log("WRITE_API=ZERO")
    log("POLICY_MUTATION=ZERO")
    log("REGISTRAR=ZERO")
    log("VRA_REGISTRY_CHANGE=ZERO")
    log("WORKSTATION_CHANGE=ZERO")
    log("PRELOAD_PLACEMENT=EOF_TOP_LEVEL_VERIFIED_PATTERN")
    log("SYSTEM_POLICY_RESOLVER_READONLY_000062V2=PASS")

except Exception:
    restore()
    log("TRANSACTION_ROLLBACK=RESTORED_ALL_PHASE2_FILES")
    raise
