from pathlib import Path
import re, sys, traceback

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
TARGETS = [
    "src/main/vra/vra-dispatch-service.ts",
    "src/main/ipc/register-vra-dispatch-ipc.ts",
    "src/preload/index.ts",
    "src/shared/contracts.ts",
    "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts",
    "src/renderer/src/components/VeraBrowserSession/VeraEvidenceReturnInjector.ts",
]

PATTERNS = [
    r"registry", r"vra/1", r"vra-routing/1", r"manifest", r"contract",
    r"evidence", r"RETURN_QUEUED", r"RETURNED", r"ack", r"inject",
    r"ipcMain", r"ipcRenderer", r"contextBridge", r"workstation:",
    r"originVera", r"originSession", r"returnChannel", r"correlationId",
]

def safe(v):
    return str(v).encode("ascii", "backslashreplace").decode("ascii")

def emit(v=""):
    print(safe(v))

def read(path):
    p = ROOT / path
    if not p.exists():
        emit(f"FILE={path} EXISTS=FALSE")
        return None
    lines = p.read_text(encoding="utf-8-sig").splitlines()
    emit(f"FILE={path} EXISTS=TRUE LINES={len(lines)}")
    return lines

def merge(ranges, total):
    out=[]
    for a,b in sorted(ranges):
        a=max(1,a); b=min(total,b)
        if not out or a > out[-1][1] + 1:
            out.append([a,b])
        else:
            out[-1][1]=max(out[-1][1], b)
    return out

try:
    rx=[re.compile(p,re.I) for p in PATTERNS]
    for path in TARGETS:
        lines=read(path)
        if lines is None:
            continue
        hits=[]
        for i,line in enumerate(lines,1):
            if any(r.search(line) for r in rx):
                hits.append(i)
        emit(f"HITS={hits[:80]}")
        ranges=merge([(i-8,i+14) for i in hits[:40]], len(lines))
        for n,(a,b) in enumerate(ranges,1):
            emit(f"--- WINDOW {n} {a}-{b} ---")
            for i in range(a,b+1):
                emit(f"{i:05d}|{lines[i-1]}")
        emit("--- END FILE ---")

    # Also discover nearby policy/registry-like files without reading everything.
    emit("=== DISCOVERY ===")
    roots = [ROOT/"src/main", ROOT/"src/shared", ROOT/"src/renderer/src"]
    names=[]
    for base in roots:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT).as_posix()
            low = rel.lower()
            if any(k in low for k in ("registry","policy","contract","evidence","vra")):
                names.append(rel)
    for rel in sorted(names)[:180]:
        emit(f"DISCOVERED={rel}")

    emit("READ_ONLY=PASS")
    emit("PRODUCTION_MUTATION=ZERO")
    emit("PURPOSE=LOCATE_MINIMAL_CONTRACT_CATALOG_AND_AUTO_INJECTION_ANCHORS")
except Exception as exc:
    emit("RAY_SCRIPT_FAILURE=YES")
    emit(f"TYPE={type(exc).__name__}")
    emit(f"MESSAGE={exc}")
    for line in traceback.format_exc().splitlines():
        emit(line)
    raise
