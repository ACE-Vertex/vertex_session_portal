from pathlib import Path
import re, sys, traceback

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()

FILES = [
    ROOT / "src/renderer/src/components/VeraBrowserSession/VeraEvidenceReturnInjector.ts",
    ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts",
    ROOT / "src/renderer/src/components/VeraBrowserSession/VeraRelayInjector.ts",
    ROOT / "src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts",
    ROOT / "src/shared/vertex-contract-catalog.ts",
    ROOT / "src/preload/index.ts",
]

def safe(v=""):
    print(str(v).encode("ascii","backslashreplace").decode("ascii"))

def dump_full(path: Path):
    if not path.exists():
        safe(f"FILE={path.relative_to(ROOT)} EXISTS=FALSE")
        return
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    safe(f"=== FILE_BEGIN {path.relative_to(ROOT).as_posix()} LINES={len(lines)} ===")
    for i,line in enumerate(lines,1):
        safe(f"{i:05d}|{line}")
    safe(f"=== FILE_END {path.relative_to(ROOT).as_posix()} ===")

try:
    for path in FILES:
        if path.name in ("VeraEvidenceReturnInjector.ts","VeraRelayInjector.ts","VeraTaskDispatchBridge.ts","vertex-contract-catalog.ts"):
            dump_full(path)
        elif path.name == "VeraBrowserSession.ts":
            if not path.exists():
                safe("FILE=VeraBrowserSession.ts EXISTS=FALSE")
                continue
            lines = path.read_text(encoding="utf-8-sig").splitlines()
            pats = [
                re.compile(r"VERA_EVIDENCE_RETURN_EVENT", re.I),
                re.compile(r"injectWorkstationEvidence", re.I),
                re.compile(r"VERA_EVIDENCE_RETURN_RESULT_EVENT", re.I),
                re.compile(r"relay", re.I),
                re.compile(r"webview", re.I),
            ]
            hits=[i for i,l in enumerate(lines,1) if any(p.search(l) for p in pats)]
            safe(f"=== FILE_BEGIN VeraBrowserSession.ts LINES={len(lines)} HITS={hits[:100]} ===")
            ranges=[]
            for h in hits[:30]:
                a=max(1,h-20); b=min(len(lines),h+35)
                if not ranges or a > ranges[-1][1]+1:
                    ranges.append([a,b])
                else:
                    ranges[-1][1]=max(ranges[-1][1],b)
            for a,b in ranges:
                safe(f"--- WINDOW {a}-{b} ---")
                for i in range(a,b+1):
                    safe(f"{i:05d}|{lines[i-1]}")
            safe("=== FILE_END VeraBrowserSession.ts ===")
        else:
            # preload: only contract API and exposed bridge areas
            lines = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
            hits=[i for i,l in enumerate(lines,1) if "vertexContractCatalog" in l or "contextBridge" in l or "ipcRenderer" in l]
            safe(f"=== FILE_BEGIN preload/index.ts LINES={len(lines)} HITS={hits[:80]} ===")
            ranges=[]
            for h in hits[:25]:
                a=max(1,h-8); b=min(len(lines),h+18)
                if not ranges or a > ranges[-1][1]+1:
                    ranges.append([a,b])
                else:
                    ranges[-1][1]=max(ranges[-1][1],b)
            for a,b in ranges:
                safe(f"--- WINDOW {a}-{b} ---")
                for i in range(a,b+1):
                    safe(f"{i:05d}|{lines[i-1]}")
            safe("=== FILE_END preload/index.ts ===")

    safe("READ_ONLY=PASS")
    safe("PRODUCTION_MUTATION=ZERO")
    safe("PURPOSE=EXACT_DOM_AND_MESSAGE_CONTRACT_FOR_AUTOMATIC_SYSTEM_CONTRACT_INJECTION")
except Exception as exc:
    safe("RAY_SCRIPT_FAILURE=YES")
    safe(f"TYPE={type(exc).__name__}")
    safe(f"MESSAGE={exc}")
    for line in traceback.format_exc().splitlines():
        safe(line)
    raise
